"""Plain 'phone memo' style slide: white background, black left-aligned text,
no frame or decoration, no real app UI (PDCA test 2026-11-18).

Usage: python3 -I make_memo.py <out.jpg> <line> [<line> ...]   ("" = blank line)
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
W, H = 1080, 1350


def main():
    out, lines = sys.argv[1], sys.argv[2:]
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 54)
    lh = 92
    y = (H - lh * len(lines)) // 2
    for ln in lines:
        d.text((90, y), ln, font=f, fill=(20, 20, 20))
        y += lh
    img.save(os.path.join(ROOT, out) if not os.path.isabs(out) else out, quality=92)


if __name__ == "__main__":
    main()
