import struct,sys
d=open(sys.argv[1],'rb').read()
n=len(d)//2
H=struct.unpack('<%dH'%n,d[:n*2])
def isg(h):
    if h in (0x8888,0x3000,0x1800): return True
    f=h>>12
    if f in (3,7) and (h&0x800)==0:
        r=h&31; c=(h>>5)&31
        return r<21 and c<21
    return False
runs=[];i=0
while i<n:
    if isg(H[i]):
        j=i;g=0
        while j<n and (isg(H[j]) or H[j]==0xffff):
            if H[j]!=0xffff: g+=1
            j+=1
        if g>=40: runs.append((i*2,j*2,g))
        i=j
    else: i+=1
tot=0
for a,b,g in runs: tot+=g
print(len(runs),tot)
for a,b,g in runs[:400]: print(hex(a),hex(b),a//2048,g)
