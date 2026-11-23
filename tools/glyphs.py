import re,sys,struct
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dvlib import tim_info
def page_glyphs(pix):  # pix: 128*256 bytes 4bpp
    out=[]
    for r in range(21):
        for c in range(21):
            g=[]
            for y in range(12):
                row=pix[(r*12+y)*128:(r*12+y)*128+128]
                for x in range(c*12,c*12+12):
                    b=row[x//2]; g.append((b>>4) if x&1 else b&15)
            out.append(bytes(g))
    return out
def font_pages(d):
    res=[]
    for m in re.finditer(b'TIM_CODE',d):
        t=tim_info(d[m.start():m.start()+0x40000])
        if t and t['pix'][1:3]==(768,256):
            p=m.start()+t['pix'][0]+12
            res.append((m.start(),p,d[p:p+128*256]))
    return res
