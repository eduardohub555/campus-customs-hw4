"""Lift the product photos off their backgrounds so the garments float.

The catalogue photos sit on flat black or flat white studio backgrounds. This
makes those backgrounds transparent, writing a PNG per product to
``data/products_cutout/``.

The background is found by flooding **inward from the border**, not by
thresholding on colour. That distinction matters: a naive "remove everything
white" pass would erase the white YALE lettering across a navy hoodie. Flooding
from the edge only removes background that is actually connected to the edge,
so lettering enclosed by the garment survives.

Run directly:  python cutouts.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

import db

SOURCE_DIR = db.PRODUCT_IMAGE_DIR
OUTPUT_DIR = db.DATA_DIR / "products_cutout"

# How far a pixel may drift from the corner colour and still count as
# background. Studio backdrops are not perfectly flat, so some tolerance is
# needed; too much and the garment's own shadows start to dissolve.
TOLERANCE = 42

# Tolerances to try, loosest first. A photo with a glow or a textured edge
# bleeding off the garment lets a loose flood run inward and eat part of the
# garment; tightening the tolerance stops the leak at the cost of leaving a
# little backdrop behind, which is the better trade.
TOLERANCE_LADDER = (42, 30, 20, 12)


def _is_flat_backdrop(image: Image.Image) -> tuple[bool, tuple[int, int, int]]:
    """Do the four corners agree on a colour? If so, that is the backdrop."""
    w, h = image.size
    corners = [
        image.getpixel((2, 2)),
        image.getpixel((w - 3, 2)),
        image.getpixel((2, h - 3)),
        image.getpixel((w - 3, h - 3)),
    ]
    corners = [c[:3] for c in corners]
    first = corners[0]
    agree = all(
        max(abs(a - b) for a, b in zip(first, other)) <= TOLERANCE for other in corners[1:]
    )
    return agree, first


def cut_out(path: Path) -> Image.Image | None:
    """Return the garment on a transparent background, or None to leave it be."""
    image = Image.open(path).convert("RGB")
    flat, backdrop = _is_flat_backdrop(image)
    if not flat:
        return None

    for tolerance in TOLERANCE_LADDER:
        cut = _attempt(image, tolerance)
        if cut is not None:
            return cut
    return None


def _attempt(image: Image.Image, tolerance: int) -> Image.Image | None:
    """One pass at the cutout with a given flood tolerance."""

    # Flood from every border pixel on a scratch copy, painting the background
    # a colour that cannot occur naturally, then read that back as the mask.
    MARKER = (255, 0, 255)
    scratch = image.copy()
    w, h = scratch.size
    from PIL import ImageDraw

    seeds = (
        [(x, 0) for x in range(0, w, 8)]
        + [(x, h - 1) for x in range(0, w, 8)]
        + [(0, y) for y in range(0, h, 8)]
        + [(w - 1, y) for y in range(0, h, 8)]
    )
    for seed in seeds:
        if scratch.getpixel(seed) == MARKER:
            continue
        ImageDraw.floodfill(scratch, seed, MARKER, thresh=tolerance)

    # Opaque everywhere except where the flood reached.
    mask = Image.new("L", image.size, 255)
    mask.putdata([0 if pixel == MARKER else 255 for pixel in scratch.convert("RGB").getdata()])

    # Pull the mask in by a pixel. A photo shot against black has a faint light
    # rim where the garment meets the backdrop; left in, it reads as a white
    # halo once the black behind it is gone. Eroding trims that fringe.
    mask = mask.filter(ImageFilter.MinFilter(3))

    # Then an opening — erode, dilate — to drop small islands of leftover
    # backdrop that the flood could not reach, without shrinking the garment.
    mask = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))

    # Then soften the alpha only, to take the staircase off the edge.
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))

    # Quality gate. Some photos have a glow or texture bleeding off the garment
    # into the backdrop; the flood follows it inward and eats part of the
    # garment itself. Backdrop belongs at the edges, so the test is simple:
    # look at the middle of the frame, where the garment is. If much of that
    # went transparent, the flood leaked and the original photo is better than
    # a damaged cutout.
    w, h = image.size
    centre = mask.crop((int(w * 0.32), int(h * 0.32), int(w * 0.68), int(h * 0.68)))
    centre_pixels = list(centre.getdata())
    removed = sum(1 for a in centre_pixels if a < 128) / max(len(centre_pixels), 1)
    if removed > 0.12:
        return None

    cut = image.convert("RGBA")
    cut.putalpha(mask)
    return cut


def build(force: bool = False) -> dict[str, int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    made = skipped = left_alone = 0

    for source in sorted(SOURCE_DIR.glob("*.jpg")):
        target = OUTPUT_DIR / f"{source.stem}.png"
        if target.exists() and not force:
            skipped += 1
            continue
        cut = cut_out(source)
        if cut is None:
            # No flat backdrop, or the cutout came out damaged. The site falls
            # back to the original photo for these.
            target.unlink(missing_ok=True)
            left_alone += 1
            continue
        cut.save(target, "PNG", optimize=True)
        made += 1

    return {"made": made, "skipped": skipped, "kept_original": left_alone}


if __name__ == "__main__":
    print(build(force=True))
