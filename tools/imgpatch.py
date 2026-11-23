"""redraw Japanese text in stage-name TIMs and chapter title cards"""
import os,sys,re,json,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dvlib import tim_info
from timimg import clut_colors
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.path.join(ROOT,'work')
import io
SERIF_BYTES=open(os.path.join(ROOT,'SeoulHangangEB.ttf'),'rb').read()
CARDS={1:[('서장','멸룡사'),('제1장','복수자'),('제2장','기사단 잔당'),('제2장','광검사'),('제3장','마인 재상'),('제3장','흉룡신'),('제3장','배룡교단')],
       2:[('제4장','고대룡의 사도')]*3+[('제5장','사룡 부활')]*3}
def fit_font(text,size,maxw):
    while size>8:
        f=ImageFont.truetype(io.BytesIO(SERIF_BYTES),size)
        bb=f.getbbox(text)
        if bb[2]-bb[0]<=maxw: return f,bb
        size-=1
    return f,f.getbbox(text)
def text_mask(w,h,lines):
    """lines: [(text,size,cy)] -> L image"""
    im=Image.new('L',(w*4,h*4),0); dr=ImageDraw.Draw(im)
    for text,size,cy in lines:
        f,bb=fit_font(text,size*4,(w-4)*4)
        tw=bb[2]-bb[0]; th=bb[3]-bb[1]
        dr.text(((w*4-tw)//2-bb[0],cy*4-th//2-bb[1]),text,font=f,fill=255)
    return im.resize((w,h),Image.LANCZOS)
def nearest(cols,idxs,rgb):
    return min(idxs,key=lambda i:sum((cols[i][k]-rgb[k])**2 for k in range(3)))
def patch_name(blob,t,ko):
    blob=bytearray(blob); cols=clut_colors(blob,t)
    grays=[i for i,c in enumerate(cols) if c[3] and c[0]==c[1]==c[2]]
    p=t['pix'][0]+12; Wd=160
    def get(x,y): b=blob[p+y*80+x//2]; return (b>>4) if x&1 else b&15
    def put(x,y,v):
        o=p+y*80+x//2
        blob[o]=(blob[o]&0x0f)|(v<<4) if x&1 else (blob[o]&0xf0)|v
    from collections import Counter
    BG=Counter(get(x,y) for y in range(32) for x in range(Wd)).most_common(1)[0][0]
    grays=[g for g in grays if g!=BG]
    for y in range(0,18):
        for x in range(Wd):
            if get(x,y) in grays: put(x,y,BG)
    m=text_mask(Wd,19,[(ko,14,8)])
    fill=m.point(lambda a:255 if a>100 else 0)
    outline=fill.filter(ImageFilter.MaxFilter(3))
    dark=min(grays,key=lambda i:cols[i][0]); white=max(grays,key=lambda i:cols[i][0])
    mp=m.load(); op=outline.load()
    bb=outline.getbbox()
    if bb:
        for y in range(0,15):
            for x in range(Wd): put(x,y,BG)
    for y in range(0,18):
        for x in range(Wd):
            a=mp[x,y]
            if a>100: put(x,y,white)
            elif op[x,y]: put(x,y,dark)
    return bytes(blob)
def patch_card(blob,t,l1,l2):
    blob=bytearray(blob); cols=clut_colors(blob,t)
    p=t['pix'][0]+12; stride=t['pix'][3]*2
    from collections import Counter
    reg=[blob[p+y*stride+x] for y in range(80) for x in range(128)]
    bg=Counter(reg).most_common(1)[0][0]
    used=sorted(set(reg))
    ink=max(used,key=lambda i:sum((cols[i][k]-cols[bg][k])**2 for k in range(3)))
    m=text_mask(128,80,[(l1,17,15),(l2,27,57)]); mp=m.load()
    for y in range(80):
        for x in range(128):
            blob[p+y*stride+x]=ink if mp[x,y]>110 else bg
    return bytes(blob)
def apply(disc,d):
    d=bytearray(d)
    for sfx in ('','2'):
      locs=json.load(open(os.path.join(W,f'names{sfx}_locs.json')))
      keys=json.load(open(os.path.join(W,f'names{sfx}_keys.json')))
      names=json.load(open(os.path.join(W,f'names{sfx}_ko.json'),encoding='utf-8'))
      for i,k in enumerate(keys):
          if not names[i]: continue
          for dd,a in locs[k]:
              if dd!=disc: continue
              t=tim_info(bytes(d[a:a+0x10000])); e=a+t['end']
              d[a:e]=patch_name(bytes(d[a:e]),t,names[i])
    n=0
    for m in re.finditer(b'TIM_CODE',bytes(d)):
        a=m.start(); t=tim_info(bytes(d[a:a+0x40000]))
        if t and t['pix'][1:]==(576,0,352,240):
            l1,l2=CARDS[disc][n]; n+=1; e=a+t['end']
            d[a:e]=patch_card(bytes(d[a:e]),t,l1,l2)
    return bytes(d)

GALMURI=open(os.path.join(ROOT,'work','fonts','z','Galmuri11.ttf'),'rb').read()
def redraw_4bpp(blob, t, lines):
    """lines: [(text, y0, h, kind)] kind 'pix'=Galmuri 12px, 'big'=serif antialiased"""
    blob=bytearray(blob); cols=clut_colors(blob,t)
    p,x0,y0,w,h=t['pix']; p+=12; Wd=w*4; stride=w*2
    def get(x,y): b=blob[p+y*stride+x//2]; return (b>>4) if x&1 else b&15
    def put(x,y,v):
        o=p+y*stride+x//2
        blob[o]=(blob[o]&0x0f)|(v<<4) if x&1 else (blob[o]&0xf0)|v
    from collections import Counter
    BG=Counter(get(x,y) for y in range(h) for x in range(Wd)).most_common(1)[0][0]
    used=[i for i in set(get(x,y) for y in range(h) for x in range(Wd)) if i!=BG]
    bright=max(used,key=lambda i:sum(cols[i][:3]))
    for y in range(h):
        for x in range(Wd): put(x,y,BG)
    for text,ly,lh,kind in lines:
        if kind=='pix':
            f=ImageFont.truetype(io.BytesIO(GALMURI),12)
            im=Image.new('L',(Wd,lh),0); dr=ImageDraw.Draw(im)
            tw=dr.textlength(text,font=f); dr.text(((Wd-tw)//2,0),text,font=f,fill=255)
        else:
            im=text_mask(Wd,lh,[(text,lh-3,lh//2)])
        px=im.load()
        for yy in range(lh):
            for xx in range(Wd):
                a=px[xx,yy]
                if a>40:
                    rgb=tuple(cols[BG][k]*(1-a/255)+cols[bright][k]*(a/255) for k in range(3))
                    put(xx,ly+yy,nearest(cols,used,rgb) if a<230 else bright)
    return bytes(blob)
def apply_opn(opn):
    opn=bytearray(opn)
    for off,lines in [(0x16fd4,[('디스크가 다릅니다.',0,12,'pix'),('올바른 디스크를 넣어 주십시오.',12,12,'pix'),
                                 ('디스크가 다릅니다.',24,24,'big'),('올바른 디스크를 넣어 주세요.',48,24,'big')]),
                      (0x18cc8,[('드래곤 밸러 DISC 1을 넣어 주십시오',0,12,'pix'),('드래곤 밸러 DISC 2를 넣어 주십시오',12,12,'pix'),
                                 ('드래곤 밸러 DISC 1을 넣어 주세요',24,24,'big'),('드래곤 밸러 DISC 2를 넣어 주세요',48,24,'big')])]:
        blob=b'TIM_CODE'+bytes(opn[off:off+0x10000]); t=tim_info(blob)
        nb=redraw_4bpp(blob[:t['end']],t,lines)
        opn[off:off+t['end']-8]=nb[8:]
    return opn

def fixed_row20(opn):
    base=0xefd0
    f=ImageFont.truetype(io.BytesIO(GALMURI),12)
    im=Image.new('L',(256,12),0); dr=ImageDraw.Draw(im)
    dr.text((142-dr.textlength('드래곤 밸러 DISC',font=f),0),'드래곤 밸러 DISC',font=f,fill=255)
    dr.text((158,0),'넣어 주세요',font=f,fill=255)
    px=im.load()
    for y in range(12):
        for x in range(256):
            o=base+(240+y)*128+x//2; v=0 if px[x,y]>=128 else 15
            opn[o]=(opn[o]&0x0f)|(v<<4) if x&1 else (opn[o]&0xf0)|v
    return opn

def _rect_draw(blob,p,stride,rect,text,kind,align='c',inkv=None):
    x0,y0,w,h=rect
    def get(x,y): b=blob[p+y*stride+x//2]; return (b>>4) if x&1 else b&15
    def put(x,y,v):
        o=p+y*stride+x//2
        blob[o]=(blob[o]&0x0f)|(v<<4) if x&1 else (blob[o]&0xf0)|v
    from collections import Counter
    c=Counter(get(x,y) for y in range(y0,y0+h) for x in range(x0,x0+w))
    bg=c.most_common(1)[0][0]
    far=[v for v,_ in c.most_common() if abs(v-bg)>=4]
    ink=far[0] if far else max(c,key=lambda v:abs(v-bg))
    if inkv is not None: ink=inkv
    for y in range(y0,y0+h):
        for x in range(x0,x0+w): put(x,y,bg)
    im=Image.new('L',(w,h),0); dr=ImageDraw.Draw(im)
    if kind=='pix':
        f=ImageFont.truetype(io.BytesIO(GALMURI),12)
    else:
        sz=h
        while True:
            f=ImageFont.truetype(io.BytesIO(SERIF_BYTES),sz)
            bb=f.getbbox(text)
            if bb[2]-bb[0]<=w or sz<10: break
            sz-=1
    bb=dr.textbbox((0,0),text,font=f); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
    tx={'c':(w-tw)//2,'r':w-tw,'l':0}[align]-bb[0]
    ty=(h-th)//2-bb[1] if kind!='pix' else (h-12)//2
    dr.text((tx,ty),text,font=f,fill=255)
    px=im.load()
    for y in range(h):
        for x in range(w):
            if px[x,y]>=128: put(x0+x,y0+y,ink)
CFG=[((3,2,57,17),'미사용','pix','c'),((3,26,57,17),'대시','pix','c'),((3,50,57,17),'웅크리기','pix','c'),
     ((3,74,57,17),'마법','pix','c'),((3,98,57,17),'스테이터스','pix','c'),((3,122,57,17),'점프','pix','c'),
     ((3,146,57,17),'공격','pix','c'),((134,2,54,17),'진동 설정','pix','c'),
     ((196,122,55,17),'스테레오','pix','c'),((196,146,55,17),'모노럴','pix','c'),
     ((12,200,90,16),'방향키','pix','l'),((12,216,90,16),'START버튼','pix','l'),((12,232,90,16),'△버튼','pix','l'),
     ((114,200,70,16),'화면 이동','pix','l'),((114,216,70,16),'결정・종료','pix','l'),((114,232,70,16),'기본 설정','pix','l'),
     ((316,5,168,24),'컨트롤러 설정','big','r'),((316,37,168,24),'화면 위치 조정','big','r'),((316,69,168,24),'사운드 설정','big','r'),
     ((257,128,152,15),'슬롯1에 컨트롤러를','pix','l'),((257,143,152,17),'꽂아 주십시오','pix','l'),
     ((512,120,24,13),'이동','pix','l',1),((512,141,38,13),'포즈','pix','l',1),((512,193,124,13),'SELECT: 기본 설정','pix','l',4)]
def apply_tip(b):
    b=bytearray(b); o=0x35268+8
    ln=struct.unpack_from('<I',b,o)[0]; o+=ln
    ln,x,y,w,h=struct.unpack_from('<I4H',b,o); p=o+12; stride=w*2
    for e in CFG: _rect_draw(b,p,stride,*e)
    return logo_ko(b)

def logo_ko(b):
    """small Korean title in transparent bottom-right corner of the title logo TIM (8bpp)"""
    import numpy as np
    from PIL import ImageFilter
    o=0x28; blob=b'TIM_CODE'+bytes(b[o:o+0x30000]); t=tim_info(blob); cols=clut_colors(blob,t)
    p,x,y,w,h=t['pix']; base=o-8+p+12; Wd=w*2
    opaque=[i for i,c in enumerate(cols) if c[3]]
    white=max(opaque,key=lambda i:sum(cols[i][:3])); dark=min(opaque,key=lambda i:sum(cols[i][:3]))
    f=ImageFont.truetype(io.BytesIO(GALMURI),12)
    im=Image.new('L',(Wd,h),0); dr=ImageDraw.Draw(im)
    txt='드래곤 밸러'; tw=dr.textlength(txt,font=f)
    tx=346-int(tw); ty=116
    dr.text((tx,ty),txt,font=f,fill=255)
    m=np.array(im)>=128; ol=np.array(im.filter(ImageFilter.MaxFilter(3)))>=128
    for yy in range(h):
        for xx in range(Wd):
            if m[yy,xx]: b[base+yy*Wd+xx]=white
            elif ol[yy,xx]: b[base+yy*Wd+xx]=dark
    return b
