"""Build the photo journal page.

Source images live in per-month folders:

    src/img/photo-journal/<YYYY-MM>/        # paste originals here

This script resizes/compresses each original into a web-friendly copy under

    src/img/photo-journal/web/<YYYY-MM>/    # generated, gitignored

and writes a generated markdown post to `src/photo-journal.md` containing one
scrapbook-style scattered collage section per month (newest month first).

It is called from build.py's main() so it runs on every build. Generated web
images are cached: an original is only re-encoded if its source is newer than
the existing web copy.
"""

from __future__ import annotations

import math
import os
import random
from datetime import datetime

from PIL import Image, ImageOps

# Where originals live and where generated web copies go.
SRC_ROOT = "src/img/photo-journal"
WEB_SUBDIR = "web"  # generated copies: src/img/photo-journal/web/<month>/
OUT_MD = "src/photos.md"  # must match the post `label` in meta.yaml

# Two sizes per photo: a small thumbnail shown in the collage, and a larger
# "full" version loaded only when a photo is clicked open (the lightbox zoom).
FULL_EDGE = 1600
FULL_QUALITY = 82
THUMB_EDGE = 600
THUMB_QUALITY = 78

# Scatter layout, computed in arbitrary units (W wide) then emitted as
# percentages so the whole collage scales responsively.
STAGE_W = 1000.0

# Max absolute tilt (degrees) and the most any photo may be obscured by others.
# MAX_OBSCURED = 0.0 means lay them out so they don't overlap at all.
MAX_ROTATION = 3.0
MAX_OBSCURED = 0.0

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".tif", ".tiff"}


def _is_month_dir(name: str) -> bool:
    """True for folder names like 2026-06."""
    if len(name) != 7 or name[4] != "-":
        return False
    year, _, month = name.partition("-")
    return year.isdigit() and month.isdigit() and 1 <= int(month) <= 12


def _month_label(month_dir: str) -> str:
    """2026-06 -> 'June 2026'."""
    return datetime.strptime(month_dir, "%Y-%m").strftime("%B %Y")


def _ensure_web_copy(
    src_path: str, dst_path: str, max_edge: int, quality: int
) -> tuple[int, int]:
    """Resize/compress an original into a web JPEG (cached); return its (w, h)."""
    if not (
        os.path.exists(dst_path)
        and os.path.getmtime(dst_path) >= os.path.getmtime(src_path)
    ):
        with Image.open(src_path) as im:
            im = ImageOps.exif_transpose(im)  # honour camera orientation
            im = im.convert("RGB")
            im.thumbnail((max_edge, max_edge), Image.LANCZOS)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            im.save(dst_path, "JPEG", quality=quality, optimize=True, progressive=True)
    with Image.open(dst_path) as im:
        return im.size


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rotated_aabb(x: float, y: float, w: float, h: float, rot_deg: float):
    """Axis-aligned bounding box of a tilted photo: (x0, y0, x1, y1)."""
    rad = math.radians(abs(rot_deg))
    bw = w * math.cos(rad) + h * math.sin(rad)
    bh = w * math.sin(rad) + h * math.cos(rad)
    cx, cy = x + w / 2, y + h / 2
    return cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2


def _max_obscured(boxes: list, areas: list[float]) -> float:
    """Worst-case fraction of any photo covered by photos painted on top of it.

    DOM order == original index order, so photo j paints over photo i when
    j > i. Summing intersection areas overestimates the union, so the result is
    a conservative upper bound on how obscured each photo is.
    """
    worst = 0.0
    for i in range(len(boxes)):
        ax0, ay0, ax1, ay1 = boxes[i]
        covered = 0.0
        for j in range(i + 1, len(boxes)):
            bx0, by0, bx1, by1 = boxes[j]
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > 0 and oy > 0:
                covered += ox * oy
        worst = max(worst, covered / areas[i])
    return worst


def _scatter_layout(aspects: list[float], seed: str) -> tuple[list[dict], float]:
    """Place photos in a deterministic tilted scatter (no row alignment).

    Photos are laid out on a jittered grid with gaps so they don't overlap;
    spacing is auto-loosened until no photo is more than MAX_OBSCURED covered.
    `aspects` are each image's height/width ratio. Returns per-photo dicts with
    left/top/width as percentages and a rotation, plus the stage aspect ratio.
    """
    n = len(aspects)
    if n <= 2:
        cols = max(1, n)
    elif n <= 6:
        cols = 3
    else:
        cols = 4

    cell_w = STAGE_W / cols
    rows = -(-n // cols)  # ceil

    # Assign grid slots so the tallest photos sit in upper rows and the
    # shortest land in the bottom row -> tidy bottom edge, no lone portrait
    # dangling. Columns within each row are shuffled to keep it scrapbooky.
    by_height = sorted(range(n), key=lambda i: aspects[i], reverse=True)

    best = None
    for attempt in range(8):
        rng = random.Random(f"{seed}-{attempt}")
        loosen = 0.06 * attempt  # widen gaps / shrink photos each retry
        w_hi = max(0.70, 0.86 - loosen)
        x_jit = max(0.0, 0.04 - 0.01 * attempt)
        y_jit = max(0.0, 0.03 - 0.008 * attempt)
        row_gap = cell_w * (0.12 + loosen)

        slot = {}
        row_members: list[list[int]] = []
        for r in range(rows):
            members = by_height[r * cols : (r + 1) * cols]
            col_order = list(range(len(members)))
            rng.shuffle(col_order)
            for member, c in zip(members, col_order):
                slot[member] = (r, c)
            row_members.append(members)

        w = [cell_w * rng.uniform(w_hi - 0.06, w_hi) for _ in range(n)]
        h = [w[i] * aspects[i] for i in range(n)]
        row_height = [
            max((h[i] for i in members), default=0.0) for members in row_members
        ]
        row_top = [0.0] * rows
        for r in range(1, rows):
            row_top[r] = row_top[r - 1] + row_height[r - 1] + row_gap

        cards, boxes, areas = [], [], []
        max_bottom = 0.0
        for i in range(n):
            row, col = slot[i]
            # Centre each photo in its cell, then jitter within the slack.
            x = col * cell_w + (cell_w - w[i]) / 2 + rng.uniform(-x_jit, x_jit) * cell_w
            y = row_top[row] + rng.uniform(-y_jit, y_jit) * row_height[row]
            x = _clamp(x, 0.0, STAGE_W - w[i])
            y = max(y, 0.0)
            rot = rng.uniform(1.0, MAX_ROTATION) * (1 if rng.random() < 0.5 else -1)
            cards.append({"x": x, "y": y, "w": w[i], "rot": round(rot, 2)})
            boxes.append(_rotated_aabb(x, y, w[i], h[i], rot))
            areas.append(w[i] * h[i])
            max_bottom = max(max_bottom, y + h[i])

        obscured = _max_obscured(boxes, areas)
        if best is None or obscured < best[2]:
            best = (cards, max_bottom, obscured)
        if obscured <= MAX_OBSCURED:
            break

    cards, max_bottom, _ = best
    for c in cards:
        c["left"] = round(c.pop("x") / STAGE_W * 100, 2)
        c["top"] = round(c.pop("y") / max_bottom * 100, 2)
        c["width"] = round(c.pop("w") / STAGE_W * 100, 2)

    return cards, round(STAGE_W / max_bottom, 4)


def _collect_months() -> list[tuple[str, list[str]]]:
    """Return [(month_dir, [original filenames sorted])] for existing month folders."""
    if not os.path.isdir(SRC_ROOT):
        return []
    months = []
    for name in sorted(os.listdir(SRC_ROOT)):
        month_path = os.path.join(SRC_ROOT, name)
        if not os.path.isdir(month_path) or not _is_month_dir(name):
            continue
        files = sorted(
            f
            for f in os.listdir(month_path)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        )
        if files:
            months.append((name, files))
    return months


def build() -> None:
    months = _collect_months()

    lines: list[str] = ["# Photo journal", ""]

    if not months:
        lines.append("*No photos yet.*")
        _write(OUT_MD, "\n".join(lines) + "\n")
        return

    expected: set[str] = set()  # web files we still want; everything else is pruned

    # Newest month first.
    for month_dir, files in sorted(months, reverse=True):
        thumbs, fulls = [], []
        aspects = []
        web_dir = os.path.join(SRC_ROOT, WEB_SUBDIR, month_dir)
        ref_base = f"img/photo-journal/{WEB_SUBDIR}/{month_dir}"
        for filename in files:
            stem = os.path.splitext(filename)[0]
            src_path = os.path.join(SRC_ROOT, month_dir, filename)
            full_path = os.path.join(web_dir, f"{stem}.jpg")
            thumb_path = os.path.join(web_dir, f"{stem}.thumb.jpg")
            w, h = _ensure_web_copy(src_path, full_path, FULL_EDGE, FULL_QUALITY)
            _ensure_web_copy(src_path, thumb_path, THUMB_EDGE, THUMB_QUALITY)
            expected.add(os.path.abspath(full_path))
            expected.add(os.path.abspath(thumb_path))
            fulls.append(f"{ref_base}/{stem}.jpg")
            thumbs.append(f"{ref_base}/{stem}.thumb.jpg")
            aspects.append(h / w)

        cards, stage_ratio = _scatter_layout(aspects, seed=month_dir)

        lines.append(f"## {_month_label(month_dir)}")
        lines.append("")
        lines.append(
            f'<div class="photo-collage" style="aspect-ratio: {stage_ratio};">'
        )
        for thumb, full, card in zip(thumbs, fulls, cards):
            lines.append(
                '  <figure class="photo-card" style="'
                f'left: {card["left"]}%; top: {card["top"]}%; '
                f'width: {card["width"]}%; --rot: {card["rot"]}deg;">'
                f'<img src="{thumb}" data-full="{full}" loading="lazy" alt="">'
                "</figure>"
            )
        lines.append("</div>")
        lines.append("")

    lines.append(LIGHTBOX_HTML)
    lines.append("")

    _prune_web(expected)

    _write(OUT_MD, "\n".join(lines) + "\n")


def _prune_web(expected: set[str]) -> None:
    """Delete generated web files (and empty month dirs) that are no longer used,
    so curated-out / renamed photos don't linger in the cache or the build."""
    web_root = os.path.join(SRC_ROOT, WEB_SUBDIR)
    if not os.path.isdir(web_root):
        return
    for month_name in os.listdir(web_root):
        month_path = os.path.join(web_root, month_name)
        if not os.path.isdir(month_path):
            continue
        for f in os.listdir(month_path):
            fp = os.path.join(month_path, f)
            if os.path.isfile(fp) and os.path.abspath(fp) not in expected:
                os.remove(fp)
        if not os.listdir(month_path):
            os.rmdir(month_path)


# Click-to-zoom overlay. Self-contained so no template change is needed.
LIGHTBOX_HTML = """<div class="photo-lightbox" id="photo-lightbox" aria-hidden="true">
  <img src="" alt="">
</div>
<script>
(function () {
  var box = document.getElementById('photo-lightbox');
  var full = box.querySelector('img');
  function close() {
    box.classList.remove('open');
    box.setAttribute('aria-hidden', 'true');
    full.removeAttribute('src');
  }
  document.querySelectorAll('.photo-collage .photo-card img').forEach(function (img) {
    img.addEventListener('click', function () {
      full.src = img.getAttribute('data-full') || img.currentSrc || img.src;
      box.classList.add('open');
      box.setAttribute('aria-hidden', 'false');
    });
  });
  box.addEventListener('click', close);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
})();
</script>"""


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    build()
