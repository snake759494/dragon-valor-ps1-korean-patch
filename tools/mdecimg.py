# -*- coding: utf-8 -*-
"""MDEC 계수 <-> 픽셀 변환 (numpy 일괄 처리).

매크로블록 = Cr, Cb, Y1, Y2, Y3, Y4 (4:2:0, 16x16), 매크로블록 순서는 열 우선.
"""
import numpy as np
import mdec as M

QT = np.array(M.QTBL, np.float64)
ZZ = np.array(M.ZIGZAG, np.int32)
ZR, ZC = ZZ // 8, ZZ % 8

_c = np.array([np.sqrt(0.5)] + [1.0] * 7)
_B = np.zeros((8, 8))
for _u in range(8):
    for _x in range(8):
        _B[_u, _x] = _c[_u] * np.cos((2 * _x + 1) * _u * np.pi / 16) / 2
_BT = _B.T


def idct_batch(F):
    """(N,8,8) 계수 -> (N,8,8) 픽셀"""
    return _BT @ F @ _B


def dct_batch(f):
    return _B @ f @ _BT


def coef_array(blocks, qscale):
    """블록 리스트 -> (N,8,8) 계수"""
    n = len(blocks)
    z = np.zeros((n, 64))
    for bi, b in enumerate(blocks):
        z[bi, 0] = b['dc'] * QT[0]
        i = 0
        for run, lv, _e in b['ac']:
            i += run + 1
            if i > 63: break
            z[bi, i] = lv * QT[ZZ[i]] * qscale / 4.0
    F = np.zeros((n, 8, 8))
    F[:, ZR, ZC] = z
    return F


def block_from_coefs(F, qscale, dead=0, cut=64):
    """프레임 qscale 그대로 양자화한다(디코더가 프레임 q로 역양자화하므로).
    비트를 줄여야 할 때는 q 를 올리지 말고 작은 계수를 버린다(dead)거나
    고주파를 잘라낸다(cut)."""
    z = F[ZR, ZC]
    dc = int(round(z[0] / QT[0]))
    dc = max(-512, min(511, dc))
    lv = np.rint(z * 4.0 / (QT[ZZ] * qscale)).astype(np.int32)
    lv[0] = 0
    if dead > 0: lv[np.abs(lv) <= dead] = 0
    if cut < 64: lv[cut:] = 0
    ac = []
    run = 0
    nz = np.nonzero(lv)[0]
    prev = 0
    for k in nz:
        v = int(max(-512, min(511, lv[k])))
        run = int(k - prev - 1)
        prev = int(k)
        esc = 0 if (run, abs(v)) in M.ENC else 1
        ac.append((run, v, esc))
    return dict(dc=dc, ac=ac)


def mb_grid(w, h):
    return (w + 15) // 16, (h + 15) // 16


def decode_image(blocks, w, h, qscale):
    mw, mh = mb_grid(w, h)
    need = mw * mh * 6
    if len(blocks) < need:
        blocks = list(blocks) + [dict(dc=0, ac=[]) for _ in range(need - len(blocks))]
    px = idct_batch(coef_array(blocks[:need], qscale))
    Y = np.zeros((mh * 16, mw * 16))
    Cb = np.zeros((mh * 8, mw * 8))
    Cr = np.zeros((mh * 8, mw * 8))
    i = 0
    for mx in range(mw):
        for my in range(mh):
            o = i * 6; i += 1
            Cr[my * 8:my * 8 + 8, mx * 8:mx * 8 + 8] = px[o]
            Cb[my * 8:my * 8 + 8, mx * 8:mx * 8 + 8] = px[o + 1]
            for k in range(4):
                oy = my * 16 + (k // 2) * 8; ox = mx * 16 + (k % 2) * 8
                Y[oy:oy + 8, ox:ox + 8] = px[o + 2 + k]
    Cbu = np.repeat(np.repeat(Cb, 2, 0), 2, 1)
    Cru = np.repeat(np.repeat(Cr, 2, 0), 2, 1)
    img = np.dstack([Y + 1.402 * Cru,
                     Y - 0.3437 * Cbu - 0.7143 * Cru,
                     Y + 1.772 * Cbu]) + 128.0
    return np.clip(img[:h, :w], 0, 255).astype(np.uint8)


def encode_macroblock(rgb, qscale, dead=0, cut=64):
    r = rgb[:, :, 0].astype(np.float64)
    g = rgb[:, :, 1].astype(np.float64)
    b = rgb[:, :, 2].astype(np.float64)
    Y = 0.299 * r + 0.587 * g + 0.114 * b - 128.0
    Cb = -0.1687 * r - 0.3313 * g + 0.5 * b
    Cr = 0.5 * r - 0.4187 * g - 0.0813 * b
    cb = (Cb[0::2, 0::2] + Cb[0::2, 1::2] + Cb[1::2, 0::2] + Cb[1::2, 1::2]) / 4
    cr = (Cr[0::2, 0::2] + Cr[0::2, 1::2] + Cr[1::2, 0::2] + Cr[1::2, 1::2]) / 4
    src = np.stack([cr, cb,
                    Y[0:8, 0:8], Y[0:8, 8:16], Y[8:16, 0:8], Y[8:16, 8:16]])
    F = dct_batch(src)
    return [block_from_coefs(F[k], qscale, dead, cut) for k in range(6)]
