"""Dragon Valor Korean patch builder.

usage: python tools/build.py [--test]
inputs : work/texts.json, work/uniq_jp.json, work/tr/ko_*.txt, work/sys_ko.json (BIN strings)
outputs: Dragon Valor (Korean) (Disc 1/2).bin/.cue next to the originals
"""
import sys, os, re, json, struct, glob
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fixedmap import FIXED
from containers import find_containers
from dvlib import entries
from glyphs import font_pages
from kofont import render, put_cell, clear_cell
import iso
from cdecc import fix_sector_mode2form1

ROOT = os.path.abspath(os.path.join(HERE, '..'))
W = os.path.join(ROOT, 'work')
SRC = {1: 'Dragon Valor (Japan) (Disc 1).bin', 2: 'Dragon Valor (Japan) (Disc 2).bin'}
DST = {1: 'Dragon Valor (Korean) (Disc 1).bin', 2: 'Dragon Valor (Korean) (Disc 2).bin'}

# ---------------------------------------------------------------- symbols
REV = {}
for (r, c), ch in FIXED.items():
    REV.setdefault(ch, (r, c))
ALIAS = {'!': '！', '?': '？', ':': '：', '<': '＜', '>': '＞', ',': '，', '.': '．',
         '-': '－', '~': '～', '#': '＃', '%': '％', '&': '＆', '+': '＋', '=': '＝',
         '*': '＊', '/': '／', '$': '＄', '「': '「', '」': '」', '[': '[', ']': ']',
         '｢': '「', '｣': '」', '“': '”', '"': '”', '’': '’', '\'': '’'}
WIDTH = {'…': 12, '。': 6, '、': 6, '－': 12, '！': 6, '？': 9, '：': 6, '(': 6, ')': 6,
         '＜': 12, '＞': 12, '・': 12, '□': 12, '×': 12, '○': 12, '△': 12, '「': 6, '」': 6,
         '～': 12, '．': 6, '，': 6, '’': 6, '”': 8, 'ー': 12, '＃': 12, 'Ⓥ': 12}
for ch in '0123456789':
    WIDTH[ch] = 9
WIDTH['1'] = 8
for ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    WIDTH[ch] = 10
for ch in 'HMRGOW':
    WIDTH[ch] = 12
for ch in 'abcdefghijklmnopqrstuvwxyz':
    WIDTH[ch] = 8
for ch in 'mw':
    WIDTH[ch] = 10
for ch in 'ijl':
    WIDTH[ch] = 5
WIDTH['P'] = 10
WIDTH['L'] = 10
HANGUL_W = 12
SCROLL_CENTER = 123

# fixed-page cells that may be replaced by Hangul
FREE_FIXED = [(r, c) for r in range(5, 12) for c in range(21)] + \
             [(12, c) for c in range(14)] + \
             [(r, c) for r in range(13, 20) for c in range(21)]

def is_hangul(ch):
    return '가' <= ch <= '힣'

def norm_char(ch):
    return ALIAS.get(ch, ch)

# ---------------------------------------------------------------- translations
def load_ko():
    ko = {}
    for fn in sorted(glob.glob(os.path.join(W, 'tr', 'ko_*.txt'))):
        txt = open(fn, encoding='utf-8').read()
        parts = re.split(r'(?m)^#(\d+)\n', txt)
        for i in range(1, len(parts), 2):
            k = int(parts[i]); body = parts[i + 1]
            if body.endswith('\n'):
                body = body[:-1]
            ko[k] = body
    return ko

TOKEN = re.compile(r'\{([0-9a-f]{4})\}|(\n)|(⏎)|(.)', re.S)

def tokenize(s):
    """-> list of ('code',int) | ('nl',) | ('snl',) | ('ch',str)"""
    out = []
    s = s.replace('……', '……')
    q = 0
    for m in TOKEN.finditer(s):
        if m.group(1):
            out.append(('code', int(m.group(1), 16)))
        elif m.group(2):
            out.append(('nl',))
        elif m.group(3):
            out.append(('snl',))
        else:
            ch = m.group(4)
            if ch == "'":
                ch = '「' if q % 2 == 0 else '」'; q += 1
            out.append(('ch', ch))
    return out

def chars_of(s):
    return [t[1] for t in tokenize(s) if t[0] == 'ch' and t[1] not in ' 　']

# ---------------------------------------------------------------- encoder
class Enc:
    def __init__(self, fixed_map, page_map):
        self.fixed = fixed_map      # ch -> (r,c)   (Hangul placed in fixed page)
        self.page = page_map        # ch -> (r,c)   (page1)

    def glyph(self, ch):
        ch = norm_char(ch)
        if is_hangul(ch):
            if ch in self.fixed:
                r, c = self.fixed[ch]; pg = 0
            elif ch in self.page:
                r, c = self.page[ch]; pg = 1
            else:
                raise KeyError(ch)
            return r | (c << 5) | (HANGUL_W << 10) | (pg << 14), HANGUL_W
        if ch in REV:
            r, c = REV[ch]
            w = WIDTH.get(ch, 12)
            return r | (c << 5) | (w << 10), w
        raise KeyError(ch)

    def line_width(self, toks):
        w = 0
        for t in toks:
            if t[0] == 'ch':
                ch = t[1]
                if ch == '　': w += 12
                elif ch == ' ': w += 6
                else: w += self.glyph(ch)[1]
        return w

    def encode(self, s, kind):
        toks = tokenize(s)
        codes = []
        if kind == 'scroll':
            # re-center every line
            lines = [[]]
            for t in toks:
                if t[0] == 'snl': lines.append([])
                else: lines[-1].append(t)
            for li, ln in enumerate(lines):
                while ln and ln[0][0] == 'ch' and ln[0][1] in ' 　': ln.pop(0)
                while ln and ln[-1][0] == 'ch' and ln[-1][1] in ' 　': ln.pop()
                if ln:
                    w = self.line_width(ln)
                    lead = max(0, SCROLL_CENTER - w // 2)
                    codes += [0x3000] * (lead // 12)
                    if lead % 12 >= 6: codes.append(0x1800)
                    codes += self._enc(ln)
                if li < len(lines) - 1: codes.append(0x8888)
        else:
            codes = self._enc(toks)
        codes.append(0xffff)
        if len(codes) % 2: codes.append(0)
        return codes

    def _enc(self, toks):
        codes = []; at_line_start = True
        for t in toks:
            if t[0] == 'code':
                codes.append(t[1]); continue
            if t[0] == 'nl':
                codes.append(0x8000); at_line_start = True; continue
            if t[0] == 'snl':
                codes.append(0x8888); at_line_start = True; continue
            ch = t[1]
            if ch == '　':
                codes.append(0x3000); continue
            if ch == ' ':
                codes.append(0x3000 if at_line_start else 0x1800); continue
            at_line_start = False
            codes.append(self.glyph(ch)[0])
        return codes

def max_line_px(enc, s):
    toks = tokenize(s); best = 0; cur = []
    for t in toks + [('nl',)]:
        if t[0] in ('nl', 'snl'):
            best = max(best, enc.line_width(cur)); cur = []
        elif t[0] == 'ch':
            cur.append(t)
    return best

# ---------------------------------------------------------------- desc tables
def load_desc_ko():
    p = os.path.join(W, 'desc_ko.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}

def desc_to_text(v):
    return v.replace('⏎', '\n').replace('¶', '⏎').replace('⏹', '{ffff}')

def desc_key(seq):
    o = ''; i = 0
    while i < len(seq):
        h = seq[i]
        if h == 0xfccc and i + 1 < len(seq):
            o += '{fccc}{%04x}' % seq[i + 1]; i += 2; continue
        if h == 0x8000: o += '⏎'
        elif h == 0x8888: o += '¶'
        elif h == 0xffff: o += '⏹'
        elif h == 0x3000: o += '　'
        elif h == 0x1800: o += ' '
        elif h & 0x8000: o += '{%04x}' % h
        else: o += FIXED.get((h & 31, (h >> 5) & 31), '?') if not h & 0x4000 else '〓'
        i += 1
    return o

def rebuild_desc(blob, dko, enc):
    import desc
    strs = desc.parse(blob)
    n = len(strs); out = []
    for sq in strs:
        k = desc_key(sq)
        if k in dko:
            out.append(enc._enc(tokenize(desc_to_text(dko[k]))))
        else:
            out.append(list(sq))
    offs = []; pos = n
    for c in out:
        offs.append(pos); pos += len(c)
    codes = offs + [x for c in out for x in c]
    if len(codes) % 2: codes.append(0)
    return struct.pack('<%dH' % len(codes), *codes)

# ---------------------------------------------------------------- plan
def load_items():
    T = json.load(open(os.path.join(W, 'texts.json'), encoding='utf-8'))
    U = json.load(open(os.path.join(W, 'uniq_jp.json'), encoding='utf-8'))
    idx = {u: i for i, u in enumerate(U)}
    ko = load_ko()
    for t in T:
        t['ko'] = None
        if not t.get('orphan') and t['jp'] in idx and idx[t['jp']] in ko:
            t['ko'] = ko[idx[t['jp']]]
            t['uid'] = idx[t['jp']]
    op = os.path.join(W, 'orphan_ko.json')
    if os.path.exists(op):
        O = json.load(open(op, encoding='utf-8'))
        for t in T:
            k = '%d:%d:%d' % (t['disc'], t['sec'], t['ent'])
            if k in O: t['ko'] = O[k]; t['fixed_only'] = True; t['uid'] = -1
    return T

def load_sys():
    p = os.path.join(W, 'sys_ko.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []

def plan(T, sysk):
    freq = Counter()
    for t in T:
        if t['ko']:
            for ch in chars_of(t['ko']):
                if is_hangul(ch): freq[ch] += 1
    must = set()
    for t in T:
        if t.get('fixed_only'):
            for ch in chars_of(t['ko']):
                if is_hangul(ch): must.add(ch)
    for v in load_desc_ko().values():
        for ch in chars_of(desc_to_text(v)):
            if is_hangul(ch): must.add(ch)
    for s in sysk:
        for ch in chars_of(s['ko']):
            if is_hangul(ch): must.add(ch)
    order = sorted(must, key=lambda c: -freq[c]) + [c for c, _ in freq.most_common() if c not in must]
    if len(must) > len(FREE_FIXED):
        raise SystemExit('too many fixed-only syllables: %d' % len(must))
    fixed_chars = order[:len(FREE_FIXED)]
    fixed_map = {ch: FREE_FIXED[i] for i, ch in enumerate(fixed_chars)}
    pages = {}
    for disc in (1, 2):
        need = defaultdict(set)
        for t in T:
            if t['disc'] == disc and t['ko']:
                for ch in chars_of(t['ko']):
                    if is_hangul(ch) and ch not in fixed_map and not t.get('fixed_only'): need[t['font']].add(ch)
        for j, chs in need.items():
            chs = sorted(chs, key=lambda c: -freq[c])
            if len(chs) > 441:
                raise SystemExit('disc %d font %d needs %d glyphs' % (disc, j, len(chs)))
            pages[(disc, j)] = {ch: (i // 21, i % 21) for i, ch in enumerate(chs)}
    return fixed_map, pages, freq

# ---------------------------------------------------------------- apply
def patch_fixed_page(opn, fixed_map):
    base = 0xefd0
    pix = bytearray(opn[base:base + 128 * 256])
    for rc in FREE_FIXED: clear_cell(pix, *rc)
    for ch, (r, c) in fixed_map.items(): put_cell(pix, r, c, render(ch))
    opn[base:base + 128 * 256] = pix

def rebuild_data(disc, T, fixed_map, pages, report):
    d = bytearray(open(os.path.join(W, f'DATA{disc}.CDR'), 'rb').read())
    fps = font_pages(bytes(d))
    # font pages
    for (dd, j), pm in pages.items():
        if dd != disc: continue
        p = fps[j][1]
        pix = bytearray(128 * 256)
        for i in range(len(pix)): pix[i] = 0xff
        for ch, (r, c) in pm.items(): put_cell(pix, r, c, render(ch))
        d[p:p + 128 * 256] = pix
    # containers
    bysec = defaultdict(list)
    for t in T:
        if t['disc'] == disc and t['ko']: bysec[t['sec']].append(t)
    dko = load_desc_ko()
    import desc as _desc
    for s_, i_, a_, b_, r_ in _desc.find(bytes(d)):
        bysec[s_].append({'desc': True, 'ent': i_})
    cs = {s: (n, offs) for s, n, offs in find_containers(bytes(d))}
    over = []
    for s, lst in bysec.items():
        n, offs = cs[s]
        o = s * 2048
        ents = [bytes(d[o + offs[i]:o + offs[i + 1]]) for i in range(n)]
        for t in lst:
            if t.get('desc'):
                ents[t['ent']] = rebuild_desc(ents[t['ent']], dko, Enc(fixed_map, {}))
                continue
            enc = Enc(fixed_map, {} if t.get('fixed_only') else pages.get((disc, t['font']), {}))
            codes = enc.encode(t['ko'], t['kind'])
            t['newpx'] = max_line_px(enc, t['ko'])
            ents[t['ent']] = struct.pack('<%dH' % len(codes), *codes)
        hdr = 4 + 4 * (n + 1)
        newoffs = [hdr]
        for e in ents:
            assert len(e) % 4 == 0, (s, len(e))
            newoffs.append(newoffs[-1] + len(e))
        total = newoffs[-1]
        cap = (offs[-1] + 2047) // 2048 * 2048
        if total > cap:
            over.append((s, total - cap)); continue
        blob = struct.pack('<I', n) + struct.pack('<%dI' % (n + 1), *newoffs) + b''.join(ents)
        blob += b'\0' * (cap - len(blob))
        d[o:o + cap] = blob
    report['over_%d' % disc] = over
    return bytes(d)

# ---------------------------------------------------------------- iso write
def write_disc(disc, files):
    """files: {iso_path: new_bytes} (same size as original)"""
    src = os.path.join(ROOT, SRC[disc]); dst = os.path.join(ROOT, DST[disc])
    dd = iso.Disc(src)
    table = {n: (l, sz) for n, l, sz, _, _ in dd.walk()}
    dd.f.close()
    import shutil
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        shutil.copyfile(src, dst)
    with open(src, 'rb') as fs, open(dst, 'r+b') as fd:
        for name, data in files.items():
            lba, sz = table[name]
            assert len(data) == sz, (name, len(data), sz)
            nsec = (sz + 2047) // 2048
            for i in range(nsec):
                fs.seek((lba + i) * 2352)
                sec = bytearray(fs.read(2352))
                chunk = data[i * 2048:(i + 1) * 2048]
                if len(chunk) < 2048: chunk = chunk + bytes(sec[24 + len(chunk):24 + 2048])
                fd.seek((lba + i) * 2352)
                cur = fd.read(2352)
                if bytes(sec[24:24 + 2048]) == chunk and cur == bytes(sec):
                    continue
                if sec[18] & 0x20:      # form 2: should never be touched
                    raise SystemExit('form2 sector touched %s %d' % (name, i))
                sec[24:24 + 2048] = chunk
                fix_sector_mode2form1(sec)
                fd.seek((lba + i) * 2352); fd.write(sec)
    cue = os.path.splitext(dst)[0] + '.cue'
    open(cue, 'w', newline='\r\n').write(f'FILE "{os.path.basename(dst)}" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')

def main():
    T = load_items(); sysk = load_sys()
    fixed_map, pages, freq = plan(T, sysk)
    rep = {}
    opn = bytearray(open(os.path.join(W, 'd1', 'BIN_OPENNING.BIN'), 'rb').read())
    patch_fixed_page(opn, fixed_map)
    import imgpatch
    opn = imgpatch.apply_opn(opn)
    opn = imgpatch.fixed_row20(opn)
    import sysstr
    bins = sysstr.apply(sysk, Enc(fixed_map, {}), {'BIN/OPENNING.BIN': opn})
    for disc in (1, 2):
        data = rebuild_data(disc, T, fixed_map, pages, rep)
        import imgpatch
        data = imgpatch.apply(disc, data)
        import ftree, pickle as _pk
        import mapsheet
        data = mapsheet.apply(disc, data)[0]
        data = ftree.apply(disc, data, _pk.load(open(os.path.join(W, 'ftree_refs.pkl'), 'rb')))[0]
        files = {'/DATA.CDR': data}
        for k, v in bins.items(): files['/' + k] = bytes(v)
        dd = iso.Disc(os.path.join(ROOT, SRC[disc]))
        for n_, l_, sz_, _, _ in dd.walk():
            if n_ == '/TITLE/DB_TITLE.TIP':
                tip = dd.readfile(l_, sz_)
                files[n_] = bytes(imgpatch.apply_tip(tip))
        dd.f.close()
        write_disc(disc, files)
        import movsub
        r = movsub.process(os.path.join(ROOT, SRC[disc]), os.path.join(ROOT, DST[disc]), disc)
        print('movie frames', disc, len(r), 'max cut', min((x[1] for x in r), default=None))
    done = sum(1 for t in T if t['ko'])
    print('translated items', done, '/', sum(1 for t in T if not t.get('orphan')))
    print('fixed hangul', len(fixed_map), 'pages', len(pages), 'max page', max((len(p) for p in pages.values()), default=0))
    print('overflow', rep)
    wide = [(t['disc'], t['sec'], t['ent'], t['newpx'], t['uid']) for t in T if t.get('newpx', 0) > 276 and t['kind'] != 'scroll']
    print('too wide lines', len(wide), wide[:20])
    json.dump({'fixed': {k: v for k, v in fixed_map.items()}}, open(os.path.join(W, 'fixed_map.json'), 'w', encoding='utf-8'), ensure_ascii=False)

if __name__ == '__main__':
    main()
