"""Korean glyph rendering (Galmuri11, native 12px) into 4bpp 12x12 cells.
palette: 0 = ink (white in game), 15 = transparent background"""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', 'work', 'fonts', 'z', 'Galmuri11.ttf')
_font = None

def font():
    global _font
    if _font is None:
        _font = ImageFont.truetype(FONT, 12)   # 12px = native pixel size (UPM 1200, 100u/px)
    return _font

def render(ch):
    """return 144 nibbles (row-major) for a 12x12 cell"""
    im = Image.new('L', (12, 12), 0)
    d = ImageDraw.Draw(im)
    d.text((0, 0), ch, font=font(), fill=255)
    px = im.load()
    return [0 if px[x, y] >= 128 else 15 for y in range(12) for x in range(12)]

def put_cell(pix, r, c, nib, stride=128):
    """write 144 nibbles into 4bpp page bytearray (256px wide) at cell (r,c)"""
    for y in range(12):
        for x in range(12):
            X = c * 12 + x
            o = (r * 12 + y) * stride + X // 2
            v = nib[y * 12 + x]
            if X & 1:
                pix[o] = (pix[o] & 0x0F) | (v << 4)
            else:
                pix[o] = (pix[o] & 0xF0) | v

def clear_cell(pix, r, c):
    put_cell(pix, r, c, [15] * 144)
