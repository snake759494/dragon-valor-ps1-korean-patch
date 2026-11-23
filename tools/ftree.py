"""Family tree name boxes: find katakana names by template matching, redraw in Korean"""
import sys,os,re,io,pickle
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dvlib import tim_info
from timimg import clut_colors
from PIL import Image,ImageDraw,ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); W=os.path.join(HERE,'..','work')
KO={'クロヴィス':'클로비스','カロリナ':'카롤리나','セリア':'셀리아','アーレン':'아렌','シェラ':'셰라','コーデル':'코델','ファーナ':'파나',
'フェリペ':'펠리페','ジーネ':'지네','フィリップ':'필립','アンナ':'안나','ミハエル':'미하엘','ジェロム':'제롬','サーラ':'사라','アニタ':'아니타'}
def arr(d,a,t):
    cols=clut_colors(d[a:a+t['end']],t)
    p,_,_,w,h=t['pix']; base=a+p+12
    idx=np.frombuffer(d[base:base+w*2*h],np.uint8).reshape(h,w*2)
    lum=np.array([sum(c[:3]) for c in cols]+[0]*(256-len(cols)))
    return idx,lum[idx]>600,cols
def find(mask,refs):
    H,Wd=mask.shape; out=[]
    m=mask.astype(np.float32)
    from numpy.lib.stride_tricks import sliding_window_view
    for rm,name in refs:
        r=rm.astype(np.float32); h,w=r.shape
        win=sliding_window_view(m,(h,w))
        inter=(win*r).sum(axis=(2,3)); ws=win.sum(axis=(2,3))
        sc=2*inter/(ws+r.sum()+1e-6)
        ys,xs=np.where(sc>0.85)
        for y,x in zip(ys,xs): out.append((sc[y,x],x,y,name))
    out.sort(reverse=True); keep=[]
    for s,x,y,n in out:
        if all(abs(x-x2)>20 or abs(y-y2)>8 for _,x2,y2,_ in keep): keep.append((s,x,y,n))
    return keep
GAL=open(os.path.join(W,'fonts','z','Galmuri11.ttf'),'rb').read()
def patch(d,a,t,refs):
    idx,mask,cols=arr(d,a,t)
    p,_,_,w,h=t['pix']; base=a+p+12; st=w*2
    found=find(mask,refs); d=bytearray(d)
    f=ImageFont.truetype(io.BytesIO(GAL),12)
    bright=max(range(len(cols)),key=lambda i:sum(cols[i][:3]))
    for s,x,y,name in found:
        rh,rw=11,53
        sub=idx[y:y+rh,x:x+rw]; msub=mask[y:y+rh,x:x+rw]
        vals,cnt=np.unique(sub[~msub],return_counts=True); bg=int(vals[np.argmax(cnt)]) if len(vals) else 0
        for yy in range(-1,rh+1):
            for xx in range(-1,rw):
                d[base+(y+yy)*st+x+xx]=bg
        im=Image.new('L',(rw,12),0); dr=ImageDraw.Draw(im)
        txt=KO[name]; tw=dr.textlength(txt,font=f); dr.text(((rw-tw)//2,0),txt,font=f,fill=255)
        px=np.array(im)
        for yy in range(min(rh,12)):
            for xx in range(rw):
                if px[yy,xx]>=128: d[base+(y+yy)*st+x+xx]=bright
    return bytes(d),found
def build_refs(ds):
    items=pickle.load(open(os.path.join(W,'tims_items.pkl'),'rb'))
    POS=[(58,41),(138,41),(98,73),(178,73),(138,105),(218,105),(178,137),(258,137)]
    known={499:['クロヴィス','カロリナ','コーデル',None,'ジェロム'],581:['クロヴィス','セリア','アーレン','シェラ','フェリペ','ジーネ','アンナ','ミハエル'],
    673:['クロヴィス','カロリナ','コーデル','ファーナ','フィリップ','ジーネ','アンナ','ミハエル'],767:['クロヴィス','カロリナ','コーデル',None,'ジェロム','サーラ','アニタ']}
    refs=[]
    for n,names in known.items():
        k,(disc,a,f,dim)=items[n]; t=tim_info(ds[disc][a:a+0x80000]); idx,mask,cols=arr(ds[disc],a,t)
        for i,nm in enumerate(names):
            if nm:
                x,y=POS[i]; refs.append((mask[y+3:y+14,x+4:x+57].copy(),nm))
    return refs
def apply(disc,d,refs):
    d=bytearray(d); log=[]
    for m in re.finditer(b'TIM_CODE',bytes(d)):
        a=m.start(); t=tim_info(bytes(d[a:a+0x80000]))
        if t and t['pix'][1:]==(384,0,208,240):
            nb,found=patch(bytes(d[a:a+t['end']]),0,t,refs)
            d[a:a+t['end']]=nb; log.append((hex(a),[(n,x,y) for s,x,y,n in found]))
    return bytes(d),log
