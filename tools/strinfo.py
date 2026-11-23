# -*- coding: utf-8 -*-
"""PS1 STR(무비) 컨테이너 분석.

섹터 2352바이트, Mode2. 서브헤더(0x10~0x17)의 submode 로 비디오/오디오 구분.
비디오 섹터는 데이터 0x18 부터 32바이트 헤더:
  +0 u16 0x0160 매직
  +2 u16 0x8001 타입
  +4 u16 프레임 내 섹터 번호
  +6 u16 프레임의 섹터 수
  +8 u32 프레임 번호
  +C u32 비트스트림 바이트 수
  +10 u16 폭   +12 u16 높이
  +14.. 프레임 데이터 (섹터당 2016바이트)
"""
import struct

SEC = 2352
DATA = 24          # 동기12 + 헤더4 + 서브헤더8
VHDR = 32
PAY = 2048 - VHDR  # 2016


def read_list(lst):
    m = {}
    for line in open(lst, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 4 and p[0] == 'F': m[p[1]] = (int(p[2]), int(p[3]))
    return m


def sectors(binpath, lba, nsec):
    f = open(binpath, 'rb')
    f.seek(lba * SEC)
    for _ in range(nsec):
        s = f.read(SEC)
        if len(s) < SEC: break
        yield s
    f.close()


def is_video(sec):
    return sec[DATA:DATA + 2] == b'\x60\x01' and sec[DATA + 2:DATA + 4] == b'\x01\x80'


def vhdr(sec):
    (magic, typ, cur, cnt, fno, nbytes, w, h) = struct.unpack(
        '<HHHHIIHH', sec[DATA:DATA + 20])
    return dict(cur=cur, cnt=cnt, frame=fno, nbytes=nbytes, w=w, h=h)


def frames(binpath, lba, nsec):
    """비디오 프레임 단위로 (정보, 비트스트림) 산출"""
    buf = bytearray(); info = None
    for sec in sectors(binpath, lba, nsec):
        if not is_video(sec):
            continue
        h = vhdr(sec)
        if h['cur'] == 0:
            if info is not None and buf:
                yield info, bytes(buf[:info['nbytes']])
            info = h; buf = bytearray()
        if info is None: continue
        buf += sec[DATA + VHDR:DATA + VHDR + PAY]
        if h['cur'] == h['cnt'] - 1:
            yield info, bytes(buf[:info['nbytes']])
            info = None; buf = bytearray()
    if info is not None and buf:
        yield info, bytes(buf[:info['nbytes']])
