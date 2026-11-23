# -*- coding: utf-8 -*-
"""CD-XA ADPCM 오디오 디코더 (STR 무비 음성 추출용).

섹터 사용자데이터 2304바이트 = 사운드그룹 18개 x 128바이트.
그룹 = 파라미터 16바이트 + 데이터 112바이트.

4비트 XA 는 그룹당 **블록 8개**(각 28샘플)다. 파라미터는 중복 저장돼 있어
블록 0~3 은 params[4..7], 블록 4~7 은 params[12..15] 를 쓴다.
데이터 112바이트는 4바이트 워드 28개이고, 블록 b 는
  워드의 (b>>1)번째 바이트에서 (b&1 ? 상위 : 하위) 니블
을 읽는다. 스테레오면 블록이 좌·우 번갈아 간다.
(매핑은 좌우상관 +0.88 / 클리핑 0.000% 로 실측 확인. 다른 후보는 상관 +0.08, 클리핑 0.6%)

(예전 판은 블록을 4개만 읽어 샘플이 절반이었다. 그 결과 음성이 2배速으로
 재생돼 ASR 인식률이 크게 떨어졌다.)
"""
import struct, wave
import numpy as np

POS = [0, 60, 115, 98, 122]
NEG = [0, 0, -52, -55, -60]
SEC = 2352
DATA = 24


def decode_sector(d, st, stereo=True):
    """(좌, 우) 샘플 리스트. st = [l1,l2,r1,r2] 필터 상태"""
    L = []; R = []
    for g in range(18):
        base = g * 128
        params = d[base:base + 16]
        body = d[base + 16:base + 128]
        for b in range(8):
            p = params[4 + b] if b < 4 else params[8 + b]
            shift = p & 0x0F
            filt = (p >> 4) & 0x03
            if filt > 4: filt = 0
            ch = (b & 1) if stereo else 0
            prev = st[ch * 2:ch * 2 + 2]
            col = b >> 1
            hi = b & 1
            out = []
            for s in range(28):
                byte = body[s * 4 + col]
                nib = (byte >> 4) if hi else (byte & 0x0F)
                v = nib << 12
                if v & 0x8000: v -= 0x10000
                v >>= shift
                v += (prev[0] * POS[filt] + prev[1] * NEG[filt]) >> 6
                v = max(-32768, min(32767, v))
                prev[1] = prev[0]; prev[0] = v
                out.append(v)
            st[ch * 2:ch * 2 + 2] = prev
            (L if ch == 0 else R).extend(out)
    return L, R


def extract(binpath, lba, nsec, out_wav, max_sectors=None, rate=37800):
    f = open(binpath, 'rb'); f.seek(lba * SEC)
    st = [0, 0, 0, 0]
    L = []; R = []
    n = 0
    for i in range(nsec):
        s = f.read(SEC)
        if len(s) < SEC: break
        if not (s[18] & 0x20): continue          # Form2 = 오디오 섹터
        l, r = decode_sector(s[DATA:DATA + 2304], st)
        L.extend(l); R.extend(r); n += 1
        if max_sectors and n >= max_sectors: break
    f.close()
    m = min(len(L), len(R)) if R else len(L)
    a = np.empty(m * 2, np.int16)
    a[0::2] = np.array(L[:m], np.int16)
    a[1::2] = np.array((R or L)[:m], np.int16)
    w = wave.open(out_wav, 'wb')
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(a.tobytes()); w.close()
    return n, m / float(rate)
