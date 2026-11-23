"""Overlay small Korean title under the DRAGON VALOR logo at the end of the opening STR (v3)."""
import sys,os,io,struct
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import strinfo as S, mdec3 as M3, mdec as M, mdecimg as MI
def frame_sectors(binp, lba, nsec):
    f = open(binp, 'rb'); f.seek(lba * 2352)
    cur = []; info = None; buf = bytearray()
    for i in range(nsec):
        s = f.read(2352)
        if len(s) < 2352: break
        if not S.is_video(s): continue
        h = S.vhdr(s)
        if h['cur'] == 0:
            if info is not None and cur: yield cur, info, bytes(buf)
            cur = []; info = h; buf = bytearray()
        if info is None: continue
        cur.append(i); buf += s[24 + 32:24 + 32 + 2016]
    f.close()
    if info is not None and cur: yield cur, info, bytes(buf)
from cdecc import fix_sector_mode2form1
from PIL import Image,ImageDraw,ImageFont
ROOT=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
FONT=open(os.path.join(ROOT,'SeoulHangangEB.ttf'),'rb').read()
SEC=2352; DATA=24; VHDR=32; PAY=2016
MOVIES={1:(24,37408768//2048,3482,3612),2:(261815,33716224//2048,3082,3212)}
TEXT='드래곤 밸러'
def text_layer(w,h):
    f=ImageFont.truetype(io.BytesIO(FONT),15)
    m=Image.new('L',(w,h),0); o=Image.new('L',(w,h),0)
    d=ImageDraw.Draw(m); bb=d.textbbox((0,0),TEXT,font=f); tw=bb[2]-bb[0]
    x=(w-tw)//2-bb[0]; y=186-bb[1]
    d.text((x,y),TEXT,font=f,fill=255)
    ImageDraw.Draw(o).text((x,y),TEXT,font=f,fill=255,stroke_width=2,stroke_fill=255)
    return np.array(m)/255.0,np.array(o)/255.0
def build_bs(blocks,qscale):
    bw=M3.encode_blocks(blocks,qscale); bw.write('1111111111'); body=bw.bytes()
    codes=sum(2+len(b['ac']) for b in blocks); nwords=((codes+1)//2+31)//32*32
    if (8+len(body))%4: body+=bytes(4-(8+len(body))%4)
    return struct.pack('<HHHH',nwords,0x3800,qscale,3)+body
def process(srcp,binp,disc,log=print):
    lba,nsec,f0,f1=MOVIES[disc]
    fill,outl=text_layer(304,224)
    ys,xs=np.where(outl>0); y0,y1,x0,x1=ys.min()//16,ys.max()//16,xs.min()//16,xs.max()//16
    frames=list(frame_sectors(srcp,lba,nsec)); fs=open(srcp,'rb')
    lum=[]
    ref=None; out=[]
    fh=open(binp,'r+b')
    for fi,(secs,info,buf) in enumerate(frames):
        if not (f0<=fi<f1): continue
        h,bl,br=M3.decode_frame(buf,266)
        img=MI.decode_image(bl,304,224,h['qscale']).astype(np.float64)
        L=img.mean()
        if ref is None or fi<f0+12: ref=max(ref or 0,L)
        a=min(1.0,(fi-f0+1)/8.0)*min(1.0,L/ref)
        if a<0.05: continue
        comp=img*(1-outl[...,None]*a)          # dark outline
        comp=comp*(1-fill[...,None]*a)+255*fill[...,None]*a
        comp=np.clip(comp,0,255).astype(np.uint8)
        budget=min(len(secs)*PAY,int(info['nbytes']))
        nb=None; tset=set()
        base=list(bl)
        for mx in range(x0,x1+1):
            for my in range(y0,y1+1):
                i=(mx*14+my)*6; tset.update(range(i,i+6))
                base[i:i+6]=MI.encode_macroblock(comp[my*16:my*16+16,mx*16:mx*16+16],h['qscale'],0,64)
        cut=99
        for kmax in (999,40,30,24,20,16,13,10,8,6,4,2):
            nbl=[b if (j in tset or len(b['ac'])<=kmax) else dict(dc=b['dc'],ac=b['ac'][:kmax]) for j,b in enumerate(base)]
            bs=build_bs(nbl,h['qscale'])
            if len(bs)<=budget: nb=bs; cut=kmax; break
        if nb is None: log('frame %d over budget'%fi); continue
        # write sectors
        for k,si in enumerate(secs):
            fs.seek((lba+si)*SEC); s=bytearray(fs.read(SEC))
            chunk=nb[k*PAY:(k+1)*PAY]; chunk=chunk+bytes(PAY-len(chunk))
            s[DATA+VHDR:DATA+VHDR+PAY]=chunk
            struct.pack_into('<I',s,DATA+12,len(nb))
            s[DATA+0x14:DATA+0x1C]=nb[:8]
            fix_sector_mode2form1(s)
            fh.seek((lba+si)*SEC); fh.write(s)
        out.append((fi,cut,len(nb),budget))
    fh.close()
    return out
if __name__=='__main__':
    for disc in (1,2):
        r=process(os.path.join(ROOT,f'Dragon Valor (Japan) (Disc {disc}).bin'),os.path.join(ROOT,f'Dragon Valor (Korean) (Disc {disc}).bin'),disc)
        print(disc,len(r),r[:3],r[-2:])
