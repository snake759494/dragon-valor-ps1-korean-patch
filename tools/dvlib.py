"""Dragon Valor data helpers"""
import struct
from containers import find_containers, isg
def tim_info(blob):
    # TIM_CODE + id(0x10) + flags + [clut block] + pixel block
    if blob[:8]!=b'TIM_CODE': return None
    f=struct.unpack_from('<I',blob,12)[0]; p=16; clut=None
    if f&8:
        ln,x,y,w,h=struct.unpack_from('<I4H',blob,p); clut=(p,x,y,w,h); p+=ln
    ln,x,y,w,h=struct.unpack_from('<I4H',blob,p)
    return dict(flags=f,clut=clut,pix=(p,x,y,w,h),end=p+ln)
def entries(d,s,offs):
    o=s*2048
    return [(o+offs[i],o+offs[i+1]) for i in range(len(offs)-1)]
def text_entries(d):
    res=[]
    for s,n,offs in find_containers(d):
        ents=entries(d,s,offs)
        for i,(a,b) in enumerate(ents):
            blob=d[a:b]
            if len(blob)>=8 and len(blob)%2==0:
                H=struct.unpack('<%dH'%(len(blob)//2),blob)
                if sum(isg(h) for h in H)>0.9*len(H) and H.count(0xffff)<len(H) and blob[:8]!=b'TIM_CODE':
                    res.append((s,i,a,b))
    return res
