"""in-place system strings inside BIN overlays (fixed font only)"""
import os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, '..', 'work')
def apply(sysk, enc, bins):
    out = dict(bins)
    for s in sysk:
        f = s['file']
        if f not in out:
            out[f] = bytearray(open(os.path.join(W, 'd1', f.replace('/', '_')), 'rb').read())
        b = out[f]
        if s.get('fmt') == 'rc':
            B = __import__('build'); codes = []
            for ch in s['ko']:
                if ch == ' ': codes.append(0); continue
                g = enc.glyph(ch)[0]; codes.append(((g & 31) << 5) | ((g >> 5) & 31))
            room = s['len'] // 2
            if len(codes) > room: raise SystemExit('rc too long ' + s['ko'])
            codes += [0] * (room - len(codes))
            b[s['off']:s['off'] + s['len']] = struct.pack('<%dH' % room, *codes)
            continue
        codes = enc._enc(__import__('build').tokenize(s['ko']))
        room = s['len'] // 2
        if len(codes) > room:
            raise SystemExit('sys string too long %s %x: %d > %d' % (f, s['off'], len(codes), room))
        codes += [s.get('pad', 0x3000)] * (room - len(codes))
        b[s['off']:s['off'] + s['len']] = struct.pack('<%dH' % room, *codes)
    return out
