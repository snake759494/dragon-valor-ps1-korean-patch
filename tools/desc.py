"""item/magic description tables: u16 offsets[n] (in halfwords) then strings ending 0x8000, table ends 0xffff"""
import sys,os,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from containers import find_containers,isg
from dvlib import entries
from fixedmap import FIXED
def parse(blob):
    if len(blob)<8 or len(blob)%2: return None
    H=struct.unpack('<%dH'%(len(blob)//2),blob)
    n=H[0]
    if not (10<=n<=200) or n>=len(H): return None
    offs=list(H[:n])
    if any(offs[i]>=offs[i+1] for i in range(n-1)) or offs[0]!=n: return None
    if offs[-1]>=len(H): return None
    strs=[]
    for i in range(n):
        e=offs[i+1] if i+1<n else len(H)
        s=H[offs[i]:e]
        if not s or s[-1] not in (0x8000,0xffff,0): return None
        strs.append(s)
    return strs
def find(d):
    res=[]
    for s,n,offs in find_containers(d):
        for i,(a,b) in enumerate(entries(d,s,offs)):
            r=parse(d[a:b])
            if r and sum(1 for x in r for h in x if isg(h))>len(r)*3: res.append((s,i,a,b,r))
    return res
def dec(seq):
    o=''
    for h in seq:
        if h==0x8000: o+='⏎'; continue
        if h==0x8888: o+='¶'; continue
        if h==0xffff: o+='⏹'; continue
        if h==0x3000: o+='　'; continue
        if h==0x1800: o+=' '; continue
        if h&0x8000: o+='{%04x}'%h; continue
        o+=FIXED.get((h&31,(h>>5)&31),'?') if not h&0x4000 else '〓'
    return o
if __name__=='__main__':
    for disc in (1,2):
        d=open(f'work/DATA{disc}.CDR','rb').read()
        for s,i,a,b,r in find(d):
            print(disc,s,i,b-a,len(r),dec(r[0])[:40],'|',dec(r[24])[:40] if len(r)>24 else '')
