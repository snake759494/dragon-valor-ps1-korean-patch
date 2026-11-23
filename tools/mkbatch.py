"""build unique-text translation batches from DATA texts (with resolved fonts)"""
import sys,os,json,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from assoc import resolve,W
from decode import chmap
from extract import tok
from glyphs import font_pages
def build():
    items=[]
    for disc in (1,2):
        d=open(os.path.join(W,f'DATA{disc}.CDR'),'rb').read()
        out,fps=resolve(disc)
        cache={}
        for o in out:
            if o['bad']: o['orphan']=True
            p1=fps[o['font']][1] if o['font']>=0 else None
            pm=cache.setdefault(p1,chmap(d,p1))
            H=struct.unpack('<%dH'%((o['b']-o['a'])//2),d[o['a']:o['b']])
            t,px=tok(H,pm)
            o['jp']=t; o['px']=px
            items.append(o)
    return items
if __name__=='__main__':
    items=build()
    json.dump(items,open(os.path.join(W,'texts.json'),'w',encoding='utf-8'),ensure_ascii=False)
    uniq=[];seen={}
    for o in items:
        if o.get('orphan'): continue
        if o['jp'] not in seen:
            seen[o['jp']]=len(uniq); uniq.append(o['jp'])
    json.dump(uniq,open(os.path.join(W,'uniq_jp.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=0)
    print(len(items),'unique',len(uniq),'chars',sum(len(u) for u in uniq))
    os.makedirs(os.path.join(W,'tr'),exist_ok=True)
    B=80
    for i in range(0,len(uniq),B):
        with open(os.path.join(W,'tr',f'jp_{i//B:03d}.txt'),'w',encoding='utf-8') as f:
            for k in range(i,min(i+B,len(uniq))):
                f.write(f'#{k}\n{uniq[k]}\n')
