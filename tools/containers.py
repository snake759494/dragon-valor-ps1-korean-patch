import struct,sys
def find_containers(d):
    out=[]
    for s in range(len(d)//2048):
        o=s*2048
        n=struct.unpack_from('<I',d,o)[0]
        if not (1<=n<=200): continue
        offs=struct.unpack_from('<%dI'%(n+1),d,o+4)
        if offs[0]!=4+4*(n+1): continue
        if any(offs[i]>offs[i+1] for i in range(n)): continue
        if offs[-1]>8*1024*1024: continue
        out.append((s,n,offs))
    return out
def isg(h):
    if h in (0x8888,0x3000,0x1800,0xffff,0xfccc): return True
    w=(h>>10)&15
    return (h&0x8000)==0 and 1<=w<=13 and (h&31)<21 and ((h>>5)&31)<21
def classify(blob):
    if blob[:8]==b'TIM_CODE': 
        f=struct.unpack_from('<I',blob,12)[0]
        return 'TIM%d'%f
    if len(blob)>=8 and len(blob)%2==0:
        H=struct.unpack('<%dH'%(len(blob)//2),blob)
        g=sum(1 for h in H if isg(h)); 
        if g>0.9*len(H) and H.count(0xffff)<len(H): return 'TEXT'
    return blob[:8].hex()
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read()
    for s,n,offs in find_containers(d):
        o=s*2048
        kinds=[classify(d[o+offs[i]:o+offs[i+1]]) for i in range(n)]
        print(s,n,hex(offs[-1]),' '.join(kinds))
