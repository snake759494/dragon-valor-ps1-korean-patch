"""world-map sheets (TIM 768,0,192,176): chapter title, stage list, buttons — region used as 4bpp"""
import sys,os,io,json
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from dvlib import tim_info
from PIL import Image,ImageDraw,ImageFont
W=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','work')
GAL=open(os.path.join(W,'fonts','z','Galmuri11.ttf'),'rb').read()
L1=['락시스 국경 지대','국경 경비대 요새','포로수용소 터','락시스 시가','락시스 성 가는 길','지하 수로','락시스 성','연금술 연구탑','지하 분묘','교역소']
L2a=['동락시스 성','파레이드 동굴','데트 산악 지대','산촌','알케미아 주둔지','처형장','거대 성채','영구 동토','교역소']
L4=['살드 거대 유적','거대 유적 지하','거대 유적 최심부','벨레아 산','벨레아 성채 도시','만마전 연결로','결계','만마전','만마전 깊은 곳','교역소']
L5=['옛 락시스 시가','락시스 성터','이계로 가는 동굴','마계 변경','마계 도시','이형의 숲','영원의 미궁','용왕의 감옥','교역소']
TEXT=[['제2장','기사단 잔당','동락시스 성','파레이드 동굴','데트 산악 지대','산촌','침공군 주둔지','처형장','알케미아 대성채','영구 동토'],
 ['제1장','락시스 왕국','락시스 국경 지대','국경 경비대 병사','민간인 포로수용소','락시스 시가','락시스 성 가는 길','지하 수로','락시스 성 돌입','락시스 성 잠입','연금술 연구탑','지하 분묘'],
 ['제1장','복수자']+L1, ['제1장','락시스 왕국']+L1, ['제2장','기사단 잔당']+L2a,
 ['제2장','광검사','해적선','카데리 운하','카데리 시가','채굴장 터','린턴 숲','클로비스의 요새','린턴 고지','화산 지하부','교역소'],
 ['제3장','마인 재상','왕성 지하 투기장','조마스 저택','유적 가는 산길','지라트 고대 유적','갈리아 사막','지라트 성','조마스 저택','교역소'],
 ['제3장','흉룡신','교역선 갑판','파레 섬 해안','열대 우림','주술사 마을','밀림 깊은 곳','파레 고대 유적','지라트 함정 내부','교역소'],
 ['제3장','배룡교단','카데리 서부','살드 국경 지대','살드 마을','사교도 예배당','예배당 지하','거대 유적 지하','거대 유적 최심부','교역소'],
 ['제4장','고대룡의 사도']+L4, ['제4장','고대룡의 사도','마술사의 요새','갈리아 사막','지라트 고대 유적']+L4[3:],
 ['제5장','사룡 부활']+L5, ['제5장','사룡 부활']+L5]
BTN=[((101,99,54,13),'이동'),((101,116,54,13),'스테이터스'),((101,133,54,13),'세이브')]
def nib(d,base,x,y): b=d[base+y*384+x//2]; return (b>>4) if x&1 else b&15
def setn(d,base,x,y,v):
    o=base+y*384+x//2; d[o]=(d[o]&0x0f)|(v<<4) if x&1 else (d[o]&0xf0)|v
def draw(d,base,x0,y0,w,h,text,bg,ink):
    f=ImageFont.truetype(io.BytesIO(GAL),12)
    im=Image.new('L',(w,h),0); dr=ImageDraw.Draw(im); tw=dr.textlength(text,font=f)
    dr.text(((w-tw)//2,(h-12)//2),text,font=f,fill=255); px=np.array(im)
    for y in range(h):
        for x in range(w):
            setn(d,base,x0+x,y0+y,ink if px[y,x]>=128 else bg)
def patch(d,a,lines):
    t=tim_info(bytes(d[a:a+0x80000])); base=a+t['pix'][0]+12
    from collections import Counter
    c=Counter(nib(d,base,x,y) for y in range(176) for x in range(96))
    bg=c.most_common(1)[0][0]; ink=max((v for v in c if v!=bg),key=lambda v:(abs(v-bg),c[v]))
    for y in range(168):
        for x in range(96): setn(d,base,x,y,bg)
    draw(d,base,0,6,96,14,lines[0],bg,ink); draw(d,base,0,21,96,14,lines[1],bg,ink)
    for i,txt in enumerate(lines[2:]):
        y=47+i*12
        if y+12>168: break
        draw(d,base,0,y,96,12,txt,bg,ink)
    # buttons
    for (x,y,w,h),txt in BTN:
        c2=Counter(nib(d,base,xx,yy) for yy in range(y,y+h) for xx in range(x,x+w))
        b2=c2.most_common(1)[0][0]; i2=max((v for v in c2 if v!=b2),key=lambda v:abs(v-b2),default=ink)
        draw(d,base,x,y,w,h,txt,b2,i2)
    return 'ok'
def apply(disc,d):
    d=bytearray(d); info=json.load(open(os.path.join(W,'maps.json'))); log=[]
    for i,k in enumerate(info['keys']):
        for dd,a in info['locs'][k]:
            if dd==disc: log.append((i,patch(d,a,TEXT[i])))
    return bytes(d),log
