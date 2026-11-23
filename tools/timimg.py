import struct,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dvlib import tim_info
from PIL import Image
def clut_colors(blob,t,row=0):
    p,x,y,w,h=t['clut']; base=p+12+row*w*2
    cols=[]
    for i in range(w):
        c=struct.unpack_from('<H',blob,base+i*2)[0]
        cols.append(((c&31)<<3,((c>>5)&31)<<3,((c>>10)&31)<<3, 0 if c==0 else 255))
    return cols
def to_image(blob,t,crop=None):
    p,x,y,w,h=t['pix']; pix=blob[p+12:p+12+w*h*2]
    bpp8 = t['flags']&3==1
    W=w*2 if bpp8 else w*4
    cols=clut_colors(blob,t)
    im=Image.new('RGBA',(W,h))
    px=im.load()
    for yy in range(h):
        for xx in range(W):
            if bpp8: i=pix[yy*w*2+xx]
            else:
                b=pix[yy*w*2+xx//2]; i=(b>>4) if xx&1 else b&15
            px[xx,yy]=cols[i] if i<len(cols) else (255,0,255,255)
    return im
