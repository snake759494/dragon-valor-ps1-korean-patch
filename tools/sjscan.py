import sys,re
def scan(b,minlen=3):
    i=0;out=[]
    while i<len(b)-1:
        j=i;s=[]
        while j<len(b)-1:
            c=b[j]
            if (0x81<=c<=0x9f or 0xe0<=c<=0xef) and 0x40<=b[j+1]<=0xfc and b[j+1]!=0x7f:
                try: s.append(b[j:j+2].decode('cp932')); j+=2; continue
                except: break
            if 0x20<=c<0x7f and s: s.append(chr(c)); j+=1; continue
            break
        if sum(1 for x in s if len(x.encode('cp932'))==2)>=minlen: out.append((i,''.join(s))); i=j
        else: i+=1 if j==i else (j-i if j>i else 1)
    return out
if __name__=='__main__':
    b=open(sys.argv[1],'rb').read()
    r=scan(b)
    for o,s in r[:int(sys.argv[2]) if len(sys.argv)>2 else 99999]: print(hex(o),s)
    print('total',len(r),file=sys.stderr)
