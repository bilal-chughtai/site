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
) -> None:
    """Generate reading.md with Books and Online tabs."""
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
    sorted_months = sorted(by_month.keys(), reverse=True)

    online_lines = []
    for year, month in sorted_months:
        month_name = datetime(year, month, 1).strftime("%B %Y")
        online_lines.append(f'<p class="link-heading">{month_name}</p>')
        online_lines.append('<ul class="reading-list">')
        for rd in by_month[(year, month)]:
            title = rd.get("title") or rd.get("link", "(no title)")
            link = rd.get("link", "#")
            domain = rd.get("domain", "")
            title_escaped = html.escape(title)
            link_escaped = link.replace("&", "&amp;").replace('"', "&quot;")
            if domain:
                online_lines.append(
                    f'<li><a href="{link_escaped}">{title_escaped}</a> '
                    f"<small>({domain})</small></li>"
                )
            else:
                online_lines.append(
                    f'<li><a href="{link_escaped}">{title_escaped}</a></li>'
                )
        online_lines.append("</ul>")

    books_html = "\n".join(books_lines)
    online_html = "\n".join(online_lines)

    content = f"""*Last updated: {now.strftime("%B")} {day}{ordinal_suffix(day)} {now.year}.*

<div class="tab-container reading-tabs">
<input type="radio" id="reading-tab1" name="reading-tabs" checked>
<input type="radio" id="reading-tab2" name="reading-tabs">
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
    load_env()
    base = Path(__file__).parent
    src = base / "src"

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
    generate_reading_markdown(books, raindrops, output_path)
    # Write timestamp for autoreload to check
    (base / ".reading_last_updated").write_text(
        datetime.now().isoformat(), encoding="utf-8"
    )
    print(f"Generated {output_path}")
