import sys,os,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from fixedmap import FIXED
def ok(h):
    if h in (0x3000,0x1800): return True
    if h&0xc000: return False
    w=(h>>10)&15; r=h&31; c=(h>>5)&31
    return 4<=w<=13 and r<20 and c<21 and FIXED.get((r,c),' ') not in ' '
def scan(b,minrun=3):
    out=[]
    for st in (0,):
        n=len(b)//2; H=struct.unpack('<%dH'%n,b[:n*2]); i=0
        while i<n:
            if ok(H[i]):
                j=i
                while j<n and ok(H[j]): j+=1
                if j-i>=minrun:
                    s=''.join('　' if H[k]==0x3000 else ' ' if H[k]==0x1800 else FIXED[(H[k]&31,(H[k]>>5)&31)] for k in range(i,j))
                    term=H[j] if j<n else None
                    out.append((i*2,j*2,s,term))
                i=j
            else: i+=1
    return out
if __name__=='__main__':
    b=open(sys.argv[1],'rb').read()
    r=scan(b)
    for a,e,s,t in r: print(hex(a),hex(t) if t is not None else '-',s)
    print(len(r),file=sys.stderr)
