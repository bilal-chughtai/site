"""Generate reading.md: books from CSV + online links from Raindrop."""

import csv
import html
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import requests

API_BASE = "https://api.raindrop.io/rest/v1"

JAN2026_ONLINE_CACHE_FILE = "reading-jan2026-online.cache.html"
READING_ONLINE_SENTINEL = "<!-- READING_JAN2026_ONLINE_CACHE -->"

_READING_ONLINE_SECTION_RE = re.compile(
    r'<p class="link-heading">([^<]+)</p>\s*<ul class="reading-list">\s*(.*?)\s*</ul>',
    re.DOTALL,
)
_UL_TOKEN_RE = re.compile(r"<!--.*?-->|<li>.*?</li>", re.DOTALL)


def _href_key_for_raindrop_link(link: str) -> str:
    """Match href string as emitted inside raindrop_to_li <a href="...">."""
    return link.replace("&", "&amp;").replace('"', "&quot;")


def _parse_link_heading_to_ym(heading: str) -> tuple[int, int]:
    dt = datetime.strptime(heading.strip(), "%B %Y")
    return (dt.year, dt.month)


def _extract_ul_tokens(ul_inner: str) -> list[tuple[str, str]]:
    """Order-preserving (comment | li) pieces inside a reading-list ul."""
    out: list[tuple[str, str]] = []
    for m in _UL_TOKEN_RE.finditer(ul_inner):
        text = m.group(0).strip()
        kind = "comment" if text.startswith("<!--") else "li"
        out.append((kind, text))
    return out


def _href_from_li_line(line: str) -> Optional[str]:
    m = re.search(r'<a\s+href="([^"]*)"', line)
    return m.group(1) if m else None


def _build_earliest_month_per_href(raindrops: list[dict], src_dir: Path) -> dict[str, tuple[int, int]]:
    """Same URL may appear in Raindrop in several months; keep earliest calendar month (Jan before Apr)."""
    href_months: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for rd in raindrops:
        last_update = rd.get("lastUpdate", "")
        if not last_update:
            continue
        dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
        ym = (dt.year, dt.month)
        key = _href_key_for_raindrop_link(rd.get("link", "#"))
        href_months[key].append(ym)
    cache_path = src_dir / JAN2026_ONLINE_CACHE_FILE
    if cache_path.exists():
        for raw_line in cache_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line.startswith("<li>"):
                continue
            href = _href_from_li_line(line)
            if href:
                href_months[href].append((2026, 1))
    return {h: min(months) for h, months in href_months.items() if months}


def dedupe_reading_online_inner_html(inner: str) -> str:
    """Drop duplicate <li> by <a href>: keep the item under the earliest month heading only. Preserves <!-- --> in uls."""
    matches = list(_READING_ONLINE_SECTION_RE.finditer(inner))
    if not matches:
        return inner

    parsed: list[tuple[str, tuple[int, int], list[tuple[str, str]]]] = []
    for m in matches:
        heading = m.group(1).strip()
        ym = _parse_link_heading_to_ym(heading)
        tokens = _extract_ul_tokens(m.group(2))
        parsed.append((heading, ym, tokens))

    href_to_min: dict[str, tuple[int, int]] = {}
    for _heading, ym, tokens in parsed:
        for kind, text in tokens:
            if kind != "li":
                continue
            href = _href_from_li_line(text)
            if not href:
                continue
            prev = href_to_min.get(href)
            if prev is None or ym < prev:
                href_to_min[href] = ym

    out_blocks: list[str] = []
    for heading, ym, tokens in parsed:
        kept: list[str] = []
        for kind, text in tokens:
            if kind == "comment":
                kept.append(text)
                continue
            href = _href_from_li_line(text)
            if href:
                if href_to_min.get(href) != ym:
                    continue
            kept.append(text)
        body = "\n".join(kept)
        inner_ul = body + "\n" if body else ""
        out_blocks.append(
            f'<p class="link-heading">{heading}</p>\n<ul class="reading-list">\n{inner_ul}</ul>'
        )
    # Leading/trailing newlines so inner replaces cleanly inside the reading-online div.
    return "\n" + "\n".join(out_blocks) + "\n"


def _append_jan2026_cache(
    online_lines: list[str],
    earliest: dict[str, tuple[int, int]],
    src_dir: Path,
    ym: tuple[int, int],
    month_hrefs: set[str],
) -> None:
    path = src_dir / JAN2026_ONLINE_CACHE_FILE
    if not path.exists():
        print(f"Warning: {path} not found; Jan 2026 online cache skipped.")
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("<!--"):
            online_lines.append(line)
            continue
        if line.startswith("<li>"):
            href = _href_from_li_line(line)
            if href:
                if earliest.get(href) != ym:
                    continue
                if href in month_hrefs:
                    continue
                month_hrefs.add(href)
            online_lines.append(line)


def raindrop_to_li(rd: dict) -> str:
    title = rd.get("title") or rd.get("link", "(no title)")
    link = rd.get("link", "#")
    domain = rd.get("domain", "")
    title_escaped = html.escape(title)
    link_escaped = link.replace("&", "&amp;").replace('"', "&quot;")
    if domain:
        return (
            f'<li><a href="{link_escaped}">{title_escaped}</a> '
            f"<small>({domain})</small></li>"
        )
    return f'<li><a href="{link_escaped}">{title_escaped}</a></li>'


def _rebuild_january_online_ul(old_jan_inner: str, cache_path: Path) -> str:
    """January list = cache lines then existing Jan <li>; dedupe within merge only (cross-month in dedupe_reading_online_inner_html)."""
    new_lines: list[str] = []
    merge_seen: set[str] = set()
    if cache_path.exists():
        for raw_line in cache_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("<!--"):
                new_lines.append(line)
                continue
            if line.startswith("<li>"):
                href = _href_from_li_line(line)
                if href:
                    if href in merge_seen:
                        continue
                    merge_seen.add(href)
                new_lines.append(line)
    li_pattern = re.compile(r"<li>.*?</li>", re.DOTALL)
    for m in li_pattern.finditer(old_jan_inner):
        line = m.group(0).strip()
        if not line.startswith("<li>"):
            continue
        href = _href_from_li_line(line)
        if href:
            if href in merge_seen:
                continue
            merge_seen.add(href)
        new_lines.append(line)
    return "\n".join(new_lines)


def repair_reading_online_in_file(md_path: Path, src_dir: Path) -> None:
    """Rebuild January online list from cache + existing Jan <li>, then dedupe Online tab (no Raindrop)."""
    text = md_path.read_text(encoding="utf-8")
    if READING_ONLINE_SENTINEL in text:
        text = text.replace(READING_ONLINE_SENTINEL, "", 1)

    div_open = '<div class="tab-content" id="reading-online">'
    start = text.find(div_open)
    if start < 0:
        md_path.write_text(text, encoding="utf-8")
        return
    inner_start = start + len(div_open)
    close_i = text.find("</div>", inner_start)
    if close_i < 0:
        md_path.write_text(text, encoding="utf-8")
        return

    inner = text[inner_start:close_i]
    cache_path = src_dir / JAN2026_ONLINE_CACHE_FILE
    jan_pattern = re.compile(
        r"^(.*?)(<p class=\"link-heading\">January 2026</p>\s*"
        r'<ul class="reading-list">\s*)(.*?)(\s*</ul>\s*)$',
        re.DOTALL,
    )
    m = jan_pattern.match(inner)
    if m:
        prefix, jan_open, old_jan, jan_close = m.groups()
        new_jan_body = _rebuild_january_online_ul(old_jan, cache_path)
        inner = prefix + jan_open + new_jan_body + jan_close

    inner = dedupe_reading_online_inner_html(inner)
    text = text[:inner_start] + inner + text[close_i:]
    md_path.write_text(text, encoding="utf-8")
    print(f"Repaired Online tab in {md_path}")


@dataclass
class Book:
    """A book from the bookshelf."""

    title: str
    subtitle: str
    author: str
    start_date: datetime
    end_date: Optional[datetime] = None
    partial: bool = False
    link: str = ""
    publish_year: int = 0
    additional_text: Optional[str] = None
    notes: bool = False
    row_order: int = 0

    @property
    def full_title(self) -> str:
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title

    @property
    def is_currently_reading(self) -> bool:
        return self.end_date is None

    def to_html(self) -> str:
        """Return HTML for list item."""
        title = html.escape(self.full_title)
        if self.partial:
            title = f"<em>{title}</em>"
        link = self.link.replace("&", "&amp;").replace('"', "&quot;")
        entry = f'<a href="{link}">{title}</a> <small>({self.author}, {self.publish_year})</small>'
        if self.additional_text:
            # Convert [text](url) to <a href="url">text</a>
            def link_repl(m):
                url = m.group(2).replace("&", "&amp;").replace('"', "&quot;")
                return f'<a href="{url}">{html.escape(m.group(1))}</a>'

            extra = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, self.additional_text)
            entry += f" [{extra}]"
        return f"<li>{entry}</li>"


def load_env() -> None:
    """Load .env file into os.environ."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def load_books(path: Union[str, Path]) -> list[Book]:
    """Load books from CSV."""
    books = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            additional_text = row["Additional Text"] or None
            partial = row["Partial"].lower() == "true"
            notes = row["Notes"].lower() == "true"
            start_date = datetime.strptime(row["Start Date"], "%Y-%m-%d")
            end_date = None
            if row["End Date"].strip():
                end_date = datetime.strptime(row["End Date"], "%Y-%m-%d")
            publish_year = int(row["Publish Year"]) if row["Publish Year"] else 0
            book = Book(
                title=row["Title"],
                subtitle=row["Subtitle"],
                author=row["Author"],
                start_date=start_date,
                end_date=end_date,
                partial=partial,
                link=row["Link"],
                publish_year=publish_year,
                additional_text=additional_text,
                notes=notes,
                row_order=i,
            )
            books.append(book)
    return books


def get_read_collection_id(token: str) -> int:
    """Find the 'Read' collection ID."""
    headers = {"Authorization": f"Bearer {token}"}
    for endpoint in ["collections", "collections/childrens"]:
        r = requests.get(f"{API_BASE}/{endpoint}", headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data.get("result"):
            continue
        for coll in data.get("items", []):
            if coll.get("title", "").strip().lower() == "read":
                return coll["_id"]
    raise ValueError("Could not find 'Read' collection in Raindrop.")


def is_google_doc(rd: dict) -> bool:
    link = rd.get("link", "")
    domain = rd.get("domain", "")
    return "docs.google.com" in link or "docs.google.com" in domain


def fetch_all_raindrops(token: str, collection_id: int) -> list[dict]:
    """Fetch all raindrops from a collection."""
    headers = {"Authorization": f"Bearer {token}"}
    all_items = []
    page = 0
    perpage = 50
    while True:
        r = requests.get(
            f"{API_BASE}/raindrops/{collection_id}",
            headers=headers,
            params={"sort": "-lastUpdate", "perpage": perpage, "page": page},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        all_items.extend(items)
        if len(items) < perpage:
            break
        page += 1
    return all_items


def ordinal_suffix(day: int) -> str:
    if 10 <= day % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def generate_reading_markdown(
    books: list[Book],
    raindrops: list[dict],
    output_path: Path,
    src_dir: Optional[Path] = None,
) -> None:
    """Generate reading.md with Books and Online tabs."""
    src_dir = src_dir or output_path.parent
    now = datetime.now()
    day = now.day

    # --- Books section ---
    currently_reading = [b for b in books if b.is_currently_reading]
    completed = [b for b in books if not b.is_currently_reading]
    sorted_completed = sorted(
        completed, key=lambda b: (b.end_date, b.row_order), reverse=True
    )
    sorted_reading = sorted(
        currently_reading, key=lambda b: (b.start_date, b.row_order), reverse=True
    )

    books_lines = []
    if sorted_reading:
        books_lines.append('<p class="link-heading">Currently Reading</p>')
        books_lines.append('<ul class="reading-list">')
        for book in sorted_reading:
            books_lines.append(book.to_html())
        books_lines.append("</ul>")
    current_year = None
    for book in sorted_completed:
        if book.end_date.year != current_year:
            if current_year is not None:
                books_lines.append("</ul>")
            current_year = book.end_date.year
            books_lines.append(f'<p class="link-heading">{current_year}</p>')
            books_lines.append('<ul class="reading-list">')
        books_lines.append(book.to_html())
    if sorted_completed:
        books_lines.append("</ul>")

    # --- Online section ---
    raindrops = [rd for rd in raindrops if not is_google_doc(rd)]
    by_month: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for rd in raindrops:
        last_update = rd.get("lastUpdate", "")
        if last_update:
            dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            by_month[(dt.year, dt.month)].append(rd)
    for key in by_month:
        by_month[key].sort(key=lambda rd: rd.get("lastUpdate", ""), reverse=True)
    # Stub January 2026 so the cache always has a month bucket even with no Raindrop saves.
    if (2026, 1) not in by_month:
        by_month[(2026, 1)] = []
    sorted_months = sorted(by_month.keys(), reverse=True)

    earliest_href_month = _build_earliest_month_per_href(raindrops, src_dir)
    online_lines: list[str] = []
    for year, month in sorted_months:
        ym = (year, month)
        month_hrefs: set[str] = set()
        month_name = datetime(year, month, 1).strftime("%B %Y")
        online_lines.append(f'<p class="link-heading">{month_name}</p>')
        online_lines.append('<ul class="reading-list">')
        if year == 2026 and month == 1:
            _append_jan2026_cache(
                online_lines, earliest_href_month, src_dir, ym, month_hrefs
            )
        for rd in by_month[(year, month)]:
            li_html = raindrop_to_li(rd)
            href = _href_from_li_line(li_html)
            if href:
                if earliest_href_month.get(href) != ym:
                    continue
                if href in month_hrefs:
                    continue
                month_hrefs.add(href)
            online_lines.append(li_html)
        online_lines.append("</ul>")

    books_html = "\n".join(books_lines)
    online_html = "\n".join(online_lines)

    content = f"""*Last updated: {now.strftime("%B")} {day}{ordinal_suffix(day)} {now.year}.*

<div class="tab-container reading-tabs">
<input type="radio" id="reading-tab1" name="reading-tabs">
<input type="radio" id="reading-tab2" name="reading-tabs" checked>
<div class="tab-buttons">
<label for="reading-tab1" class="tab-button">Books</label>
<label for="reading-tab2" class="tab-button">Online</label>
</div>
<div class="tab-content" id="reading-books">
{books_html}
</div>
<div class="tab-content" id="reading-online">
{online_html}
</div>
</div>

<script>
(function() {{
  var tabs = document.querySelectorAll('.reading-tabs input[name="reading-tabs"]');
  if (tabs.length >= 2) {{
    var idx = Math.random() < 0.5 ? 0 : 1;
    tabs[idx].checked = true;
  }}
}})();
</script>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    import sys

    load_env()
    base = Path(__file__).parent
    src = base / "src"

    if len(sys.argv) > 1 and sys.argv[1] == "--repair-online":
        repair_reading_online_in_file(src / "reading.md", src)
        raise SystemExit(0)

    # Load books
    books = load_books(src / "bookshelf.csv")
    print(f"Loaded {len(books)} books")

    # Fetch raindrops
    token = os.getenv("RAINDROP_ACCESS_TOKEN")
    if not token:
        raise SystemExit("RAINDROP_ACCESS_TOKEN not set in .env")
    collection_id = get_read_collection_id(token)
    raindrops = fetch_all_raindrops(token, collection_id)
    print(f"Fetched {len(raindrops)} raindrops")

    output_path = src / "reading.md"
    generate_reading_markdown(books, raindrops, output_path, src_dir=src)
    print(f"Generated {output_path}")
    repair_reading_online_in_file(output_path, src)
    # Write timestamp for autoreload to check
    (base / ".reading_last_updated").write_text(
        datetime.now().isoformat(), encoding="utf-8"
    )
