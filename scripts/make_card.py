"""Draw a 1080x1350 text card in the same style as images 01-19.

Usage: python3 -I make_card.py <out.jpg> <tag> <title lines separated by |> <sub lines separated by |>
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOLD = os.path.join(ROOT, "fonts", "ZenMaruGothic-Bold.ttf")
MED = os.path.join(ROOT, "fonts", "ZenMaruGothic-Medium.ttf")

BG = (251, 229, 234)
CIRCLE1 = (242, 176, 192)
CIRCLE2 = (246, 200, 211)
PINK = (231, 118, 151)
TITLE = (92, 45, 58)
SUB = (128, 108, 114)
HANDLE = "@hikarihikari.ai.jp"


def center(draw, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text(((1080 - w) / 2, y), text, font=font, fill=fill)


def fit(draw, lines, path, size, max_w):
    while size > 30:
        f = ImageFont.truetype(path, size)
        if all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f
        size -= 4
    return ImageFont.truetype(path, size)


def make(out, tag, title_lines, sub_lines):
    im = Image.new("RGB", (1080, 1350), BG)
    d = ImageDraw.Draw(im)
    d.ellipse((-230, -230, 300, 300), fill=CIRCLE1)
    d.ellipse((860, 1090, 1340, 1570), fill=CIRCLE2)
    d.rounded_rectangle((80, 200, 1000, 1150), radius=48, fill=(255, 255, 255))

    tf = ImageFont.truetype(BOLD, 40)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle(((1080 - tw) / 2 - 36, 160, (1080 + tw) / 2 + 36, 240), radius=40, fill=PINK)
    center(d, 175, tag, tf, (255, 255, 255))

    f = fit(d, title_lines, BOLD, 96, 820)
    lh = int(f.size * 1.2)
    sf = fit(d, sub_lines, MED, 40, 800) if sub_lines else None
    sub_h = (len(sub_lines) * int(sf.size * 1.6) + 90) if sub_lines else 0
    block = len(title_lines) * lh + sub_h
    y = 675 - block / 2
    for l in title_lines:
        center(d, y, l, f, TITLE)
        y += lh
    if sub_lines:
        y += 30
        d.rounded_rectangle((490, y, 590, y + 8), radius=4, fill=PINK)
        y += 60
        for l in sub_lines:
            center(d, y, l, sf, SUB)
            y += int(sf.size * 1.6)

    center(d, 1205, HANDLE, ImageFont.truetype(MED, 34), TITLE)
    im.save(out, "JPEG", quality=92)


if __name__ == "__main__":
    out, tag, title, sub = sys.argv[1:5]
    make(out, tag, title.split("|"), [s for s in sub.split("|") if s])


def _base():
    im = Image.new("RGB", (1080, 1350), BG)
    d = ImageDraw.Draw(im)
    d.ellipse((-230, -230, 300, 300), fill=CIRCLE1)
    d.ellipse((860, 1090, 1340, 1570), fill=CIRCLE2)
    d.rounded_rectangle((80, 200, 1000, 1150), radius=48, fill=(255, 255, 255))
    return im, d


def make_point(out, num, page, head_lines, body_lines):
    """Content slide: number badge, heading, body text."""
    im, d = _base()
    nf = ImageFont.truetype(BOLD, 56 if len(num) <= 2 else 48)
    nw = max(120, d.textlength(num, font=nf) + 70)
    d.rounded_rectangle(((1080 - nw) / 2, 140, (1080 + nw) / 2, 260), radius=60, fill=PINK)
    center(d, 162 if len(num) <= 2 else 168, num, nf, (255, 255, 255))
    hf = fit(d, head_lines, BOLD, 76, 800)
    bf = fit(d, body_lines, MED, 42, 780)
    hl, bl = int(hf.size * 1.25), int(bf.size * 1.7)
    block = len(head_lines) * hl + 90 + len(body_lines) * bl
    y = 690 - block / 2
    for l in head_lines:
        center(d, y, l, hf, TITLE)
        y += hl
    y += 30
    d.rounded_rectangle((490, y, 590, y + 8), radius=4, fill=PINK)
    y += 60
    for l in body_lines:
        center(d, y, l, bf, SUB)
        y += bl
    center(d, 1205, f"{HANDLE}  {page}", ImageFont.truetype(MED, 34), TITLE)
    im.save(out, "JPEG", quality=92)
