import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
FONTS=[r'C:\Windows\Fonts\msgothic.ttc',r'C:\Windows\Fonts\YuGothB.ttc',r'C:\Windows\Fonts\simsun.ttc']
def candidates():
    cs=[]
    for hi in range(0x88,0xa0):
        for lo in range(0x40,0xfd):
            try: cs.append(bytes([hi,lo]).decode('cp932'))
            except: pass
    for hi in range(0xe0,0xeb):
        for lo in range(0x40,0xfd):
            try: cs.append(bytes([hi,lo]).decode('cp932'))
            except: pass
    # kana & symbols
    for hi in (0x81,0x82,0x83,0x84):
        for lo in range(0x40,0xfd):
            try: cs.append(bytes([hi,lo]).decode('cp932'))
            except: pass
    return sorted(set(cs))
def norm(a):
    a=a.astype(np.float32); a-=a.mean(); n=np.linalg.norm(a); return a/(n+1e-6)
def render(ch,font,S=48):
    im=Image.new('L',(S,S),0); dr=ImageDraw.Draw(im)
    f=ImageFont.truetype(font,S)
    bb=dr.textbbox((0,0),ch,font=f)
    dr.text(((S-(bb[2]-bb[0]))/2-bb[0],(S-(bb[3]-bb[1]))/2-bb[1]),ch,font=f,fill=255)
    return im
def feat_img(im):
    a=np.asarray(im,dtype=np.float32)
    ys,xs=np.nonzero(a>40)
    if len(xs)==0: return None
    im=im.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1)).resize((16,16),Image.BILINEAR)
    return norm(np.asarray(im))
def feat_glyph(g):  # 144 nibbles, 15=bg
    a=np.array([(15-p)*17 for p in g],dtype=np.uint8).reshape(12,12)
    im=Image.fromarray(a).resize((48,48),Image.BILINEAR)
    return feat_img(im)
class OCR:
    def __init__(s):
        s.chars=candidates(); s.F=[]
        for font in FONTS:
            fs=[]
            for ch in s.chars:
                f=feat_img(render(ch,font)); fs.append(f if f is not None else np.zeros((16,16),np.float32))
            s.F.append(np.stack(fs).reshape(len(s.chars),-1))
    def top(s,g,k=5):
        f=feat_glyph(g)
        if f is None: return []
        f=f.reshape(-1)
        sc=np.max(np.stack([F@f for F in s.F]),axis=0)
        idx=np.argsort(-sc)[:k]
        return [(s.chars[i],float(sc[i])) for i in idx]
