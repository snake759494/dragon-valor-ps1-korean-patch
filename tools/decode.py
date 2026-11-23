import sys,os,pickle,struct,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from fixedmap import FIXED
from containers import find_containers
from dvlib import tim_info,entries
from glyphs import page_glyphs
W=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','work')
uniq,res=pickle.load(open(os.path.join(W,'ocr_res.pkl'),'rb'))
def page1_of(d,a,b):
    for m in re.finditer(b'TIM_CODE',d[a:b]):
        t=tim_info(d[a+m.start():b])
        if t and t['pix'][1:3]==(768,256):
            p=a+m.start()+t['pix'][0]+12
            return p
    return None
def chmap(d,p1):
    m={}
    if p1 is not None:
        for i,g in enumerate(page_glyphs(d[p1:p1+128*256])):
            if g in res: m[(i//21,i%21)]=res[g][0][0]
    return m
def dec(H,pm):
    out=[]
    for h in H:
        if h==0xffff: out.append('⏹'); continue
        if h==0x8888: out.append('\n'); continue
        if h==0x3000: out.append('　'); continue
        if h==0x1800: out.append(' '); continue
        if h==0xfccc: out.append('{C}'); continue
        if h&0x8000: out.append('{%04x}'%h); continue
        r=h&31;c=(h>>5)&31;w=(h>>10)&15;pg=(h>>14)&1
        if pg==0: ch=FIXED.get((r,c),'?')
        else: ch=pm.get((r,c),'〓')
        if w not in (12,) and pg==0 and ch not in '、。，．・': ch=ch+('{w%d}'%w if w!=6 else '')
        out.append(ch)
    return ''.join(out)
