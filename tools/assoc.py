"""associate every text entry (dlg/scroll/desc) to a page1 font; verify referenced cells non-empty"""
import sys,os,struct,bisect,re,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from containers import find_containers,isg
from dvlib import entries,tim_info
from glyphs import font_pages,page_glyphs
W=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','work')
def nonempty(pix):
    return {(i//21,i%21) for i,g in enumerate(page_glyphs(pix)) if len(set(g))>1}
def text_kind(H,blob):
    if blob[:8]==b'TIM_CODE' or 0xffff not in H: return None
    e=H.index(0xffff)
    if e<2: return None
    body=H[:e]
    if not all(isg(h) or (h&0xf000) in (0x8000,0x9000,0xa000) for h in body): return None
    if not any(not(h&0x8000) for h in body): return None
    if not all(x in (0,0xffff) for x in H[e:]): return None
    if H[0]==0x90b2: return 'dlg'
    if (H[0]&0xff00)==0x9800: return 'name'
    if 0x8888 in body: return 'scroll'
    return 'misc'

def collect(disc):
    d=open(os.path.join(W,f'DATA{disc}.CDR'),'rb').read()
    fps=font_pages(d); pos=[t for t,p,pix in fps]
    ne=[nonempty(pix) for t,p,pix in fps]
    out=[]
    for s,n,offs in find_containers(d):
        ents=entries(d,s,offs)
        for i,(a,b) in enumerate(ents):
            blob=d[a:b]
            if len(blob)<4 or len(blob)%2: continue
            H=struct.unpack('<%dH'%(len(blob)//2),blob)
            k=text_kind(H,blob)
            if not k: continue
            refs={(h&31,(h>>5)&31) for h in H if not h&0x8000 and h&0x4000}
            # candidates: fonts in same container, else nearest preceding
            own=[j for j,(t,p,pix) in enumerate(fps) if s*2048<=t<s*2048+offs[-1]]
            j=own[-1] if own else bisect.bisect(pos,a)-1
            bad=len(refs-ne[j]) if j>=0 else len(refs)
            out.append(dict(disc=disc,sec=s,ent=i,a=a,b=b,kind=k,font=j,refs=len(refs),bad=bad))
    return out,fps,ne
if __name__=='__main__':
    for disc in (1,2):
        out,fps,ne=collect(disc)
        badl=[o for o in out if o['bad']]
        print(disc,len(out),'bad',len(badl))
        for o in badl[:20]: print(o)

def resolve(disc):
    out,fps,ne=collect(disc)
    d=open(os.path.join(W,f'DATA{disc}.CDR'),'rb').read()
    from collections import defaultdict
    bysec=defaultdict(list)
    for o in out: bysec[o['sec']].append(o)
    for s,lst in bysec.items():
        if not any(o['bad'] for o in lst): continue
        refs=set()
        for o in lst:
            H=struct.unpack('<%dH'%((o['b']-o['a'])//2),d[o['a']:o['b']])
            refs|={(h&31,(h>>5)&31) for h in H if not h&0x8000 and h&0x4000}
        cands=[j for j in range(len(fps)) if not (refs-ne[j])]
        a=lst[0]['a']
        cands.sort(key=lambda j:abs(fps[j][0]-a))
        best=cands[0] if cands else lst[0]['font']
        for o in lst: o['font']=best; o['bad']=0 if cands else o['bad']; o['fixed']=True
        print('disc',disc,'sec',s,'->font',best,'cands',cands[:5])
    return out,fps
