"""Stitch a subset of the rendered screenshots into a looping demo GIF.

The frames walk a user through the happy path:
    main menu → catalog → product → cart → checkout review → payment invoice
    → payment success → /stats (so clients see the admin side too)

Run after `_render.py`:

    python _make_gif.py

Output: `demo.gif` (~2 MB, looping forever, ~2.2 s per frame).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent

# Order matters: each frame is one beat in the user journey.
FRAMES = [
    "01_main_menu.png",
    "02_catalog.png",
    "03_product_detail.png",
    "04_cart.png",
    "05_checkout_promo.png",
    "06_checkout_review.png",
    "07_payment_invoice.png",
    "08_payment_success.png",
    "13_webapp_home.png",
    "11_stats_dashboard.png",
]

FRAME_DURATION_MS = 2200    # how long each screen lingers
TARGET_WIDTH = 360          # downscale for smaller GIF size


def _prep(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    # Fit on white bg so transparency reads cleanly when GIF doesn't support alpha well.
    bg = Image.new("RGBA", img.size, (243, 245, 248, 255))
    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
    img = bg.convert("RGB")
    # Resize keeping aspect.
    w, h = img.size
    new_h = int(h * TARGET_WIDTH / w)
    img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
    return img


def main() -> None:
    frames = []
    max_w = max_h = 0
    for fname in FRAMES:
        path = HERE / fname
        if not path.exists():
            print(f"  ✗ missing {fname} — skip")
            continue
        img = _prep(path)
        max_w = max(max_w, img.width)
        max_h = max(max_h, img.height)
        frames.append((fname, img))

    if not frames:
        raise SystemExit("no frames found — did you run _render.py?")

    # Pad every frame to the same canvas so the GIF has stable dimensions.
    canvas_size = (max_w, max_h)
    canvas_bg = (243, 245, 248)
    padded = []
    for fname, img in frames:
        canvas = Image.new("RGB", canvas_size, canvas_bg)
        x = (max_w - img.width) // 2
        y = (max_h - img.height) // 2
        canvas.paste(img, (x, y))
        padded.append(canvas)
        print(f"  ✓ frame: {fname}")

    out = HERE / "demo.gif"
    padded[0].save(
        out,
        save_all=True,
        append_images=padded[1:],
        duration=FRAME_DURATION_MS,
        loop=0,           # 0 = loop forever
        optimize=True,
    )
    size_kb = out.stat().st_size // 1024
    print(f"\n✓ {out.name}: {len(padded)} frames, {size_kb} KB")


if __name__ == "__main__":
    main()
