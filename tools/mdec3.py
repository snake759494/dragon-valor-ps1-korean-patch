"""STR v3 decoder/encoder (DC differential VLC, like MPEG-1). AC identical to v2."""
import struct
import mdec as M
LUMA={'100':0,'00':1,'01':2,'101':3,'110':4,'1110':5,'11110':6,'111110':7,'1111110':8}
CHROMA={'00':0,'01':1,'10':2,'110':3,'1110':4,'11110':5,'111110':6,'1111110':7,'11111110':8}
LUMA_E={v:k for k,v in LUMA.items()}; CHROMA_E={v:k for k,v in CHROMA.items()}
def _readcode(br,tab):
    s=''
    for _ in range(9):
        s+='1' if br.read(1) else '0'
        if s in tab: return tab[s]
    raise ValueError('bad dc size '+s)
def decode_frame(bs,nmb):
    nwords,magic,qscale,ver=struct.unpack('<HHHH',bs[:8])
    br=M.BitReader(bs,8); blocks=[]; pred=[0,0,0]  # Cr,Cb,Y
    for mb in range(nmb):
        for k in range(6):
            comp=0 if k==0 else 1 if k==1 else 2
            size=_readcode(br,CHROMA if comp<2 else LUMA)
            diff=0
            if size:
                v=br.read(size)
                diff=v if v>>(size-1) else v-((1<<size)-1)
            pred[comp]+=diff*4
            dc=pred[comp]
            ac=[]
            while True:
                s='';code=None
                for _ in range(16):
                    s+='1' if br.read(1) else '0'
                    if s==M.ESCAPE:
                        run=br.read(6); lv=br.read(10)
                        if lv>=512: lv-=1024
                        code=('esc',run,lv); break
                    if s in M.DEC: code=M.DEC[s]; break
                if code is None: raise ValueError('vlc '+s)
                if code=='EOB': break
                if code[0]=='esc': ac.append((code[1],code[2],1))
                else:
                    run,lv=code
                    if br.read(1): lv=-lv
                    ac.append((run,lv,0))
            blocks.append(dict(dc=dc,ac=ac))
    return dict(nwords=nwords,qscale=qscale,ver=ver),blocks,br
def encode_blocks(blocks,qscale,ver=3):
    bw=M.BitWriter(); pred=[0,0,0]
    for i,b in enumerate(blocks):
        k=i%6; comp=0 if k==0 else 1 if k==1 else 2
        dc=int(round(b['dc']/4))*4
        diff=(dc-pred[comp])//4
        size=0 if diff==0 else abs(diff).bit_length()
        size=min(size,8)
        if diff>255: diff=255
        if diff<-255: diff=-255
        size=0 if diff==0 else abs(diff).bit_length()
        bw.write((CHROMA_E if comp<2 else LUMA_E)[size])
        if size: bw.write_num(diff if diff>0 else diff+(1<<size)-1,size)
        pred[comp]+=diff*4
        for run,lv,esc in b['ac']:
            key=(run,abs(lv))
            if not esc and key in M.ENC:
                bw.write(M.ENC[key]); bw.write('1' if lv<0 else '0')
            else:
                bw.write(M.ESCAPE); bw.write_num(run,6); bw.write_num(lv&0x3FF,10)
        bw.write(M.EOB)
    return bw
