"""Extract all DATA.CDR dialogue / scroll texts to work/jp_*.json"""
import sys,os,struct,json,bisect
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from decode import *
from containers import find_containers,isg
from glyphs import font_pages
def tok(H,pm):
    out=[];px=0;maxpx=0
    for h in H:
        if h==0xffff: break
        if h==0x8888 or h==0x8000: out.append('\n' if h==0x8000 else '⏎'); maxpx=max(maxpx,px);px=0; continue
        if h==0x3000: out.append('　'); px+=12; continue
        if h==0x1800: out.append(' '); px+=6; continue
        if h&0x8000: out.append('{%04x}'%h); continue
        r=h&31;c=(h>>5)&31;w=(h>>10)&15;pg=(h>>14)&1
        ch=FIXED.get((r,c),'?') if pg==0 else pm.get((r,c),'〓')
        out.append(ch); px+=w
    maxpx=max(maxpx,px)
    return ''.join(out),maxpx
def run():
    allent=[]
    for disc in (1,2):
        d=open(os.path.join(W,f'DATA{disc}.CDR'),'rb').read()
        fps=[(t,p) for t,p,pix in font_pages(d)]; pos=[t for t,p in fps]; cache={}
        for s,n,offs in find_containers(d):
            ents=entries(d,s,offs)
            # own page1?
            own=None
            for a,b in ents:
                p=page1_of(d,a,b)
                if p: own=p
            for i,(a,b) in enumerate(ents):
                blob=d[a:b]
                if len(blob)<4 or len(blob)%2: continue
                H=struct.unpack('<%dH'%(len(blob)//2),blob)
                kind=None
                if H[0]==0x90b2: kind='dlg'
                elif blob[:8]!=b'TIM_CODE' and len(H)>8 and sum(isg(h) for h in H)>0.95*len(H) and 0x8888 in H: kind='scroll'
                if not kind: continue
                if own: p1=own
                else:
                    k=bisect.bisect(pos,a)-1; p1=fps[k][1] if k>=0 else None
                pm=cache.setdefault(p1,chmap(d,p1))
                t,mx=tok(H,pm)
                allent.append(dict(id=f'{disc}:{s}:{i}',kind=kind,size=len(blob),px=mx,p1=p1,jp=t))
    return allent
if __name__=='__main__':
    E=run()
    json.dump(E,open(os.path.join(W,'jp_all.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=0)
    from collections import Counter
    print(len(E),Counter(e['kind'] for e in E))
    u={}
    for e in E: u.setdefault(e['jp'],[]).append(e['id'])
    print('unique texts',len(u),'chars',sum(len(k) for k in u))
    print('max px dlg',sorted(Counter(e['px'] for e in E if e['kind']=='dlg').items())[-10:])
