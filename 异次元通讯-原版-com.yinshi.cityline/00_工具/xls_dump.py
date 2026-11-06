# -*- coding: utf-8 -*-
"""最小实现：解析 OLE2(CFB) 容器里的 BIFF8 .xls（多工作表），每表导出一个 CSV。
不依赖 xlrd / olefile，只用标准库。
用法: python xls_dump.py <in.xls> <out_dir>
"""
import sys, struct, io, csv, os, re

def read_cfb(data):
    hdr = data[:512]
    if hdr[:8] != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        raise SystemExit('not a CFB file')
    ssz = 1 << struct.unpack_from('<H', hdr, 30)[0]
    mssz = 1 << struct.unpack_from('<H', hdr, 32)[0]
    n_fat = struct.unpack_from('<I', hdr, 44)[0]
    dir_start = struct.unpack_from('<I', hdr, 48)[0]
    cutoff = struct.unpack_from('<I', hdr, 56)[0]
    mini_start = struct.unpack_from('<I', hdr, 60)[0]
    n_difat = struct.unpack_from('<I', hdr, 72)[0]
    difat = list(struct.unpack_from('<109I', hdr, 76))

    def sector(i):
        off = 512 + i * ssz
        return data[off:off + ssz]

    per = ssz // 4
    nxt = struct.unpack_from('<I', hdr, 68)[0]
    for _ in range(n_difat):
        if nxt in (0xFFFFFFFE, 0xFFFFFFFF):
            break
        vals = list(struct.unpack_from('<%dI' % per, sector(nxt), 0))
        difat.extend(vals[:-1])
        nxt = vals[-1]

    fat = []
    for sec in difat:
        if sec >= 0xFFFFFFFA:
            continue
        fat.extend(struct.unpack_from('<%dI' % per, sector(sec), 0))

    def chain(start):
        out, cur, guard = [], start, 0
        while cur < 0xFFFFFFFA and guard < 1000000:
            out.append(cur)
            cur = fat[cur] if cur < len(fat) else 0xFFFFFFFE
            guard += 1
        return out

    def stream(start, size):
        return b''.join(sector(s) for s in chain(start))[:size]

    dirdata = b''.join(sector(s) for s in chain(dir_start))
    entries = []
    for i in range(0, len(dirdata), 128):
        e = dirdata[i:i + 128]
        if len(e) < 128:
            break
        nlen = struct.unpack_from('<H', e, 64)[0]
        name = e[:max(0, nlen - 2)].decode('utf-16-le', 'replace')
        entries.append((name, e[66], struct.unpack_from('<I', e, 116)[0],
                        struct.unpack_from('<Q', e, 120)[0]))

    root = next((e for e in entries if e[1] == 5), None)
    mini_data = b''.join(sector(s) for s in chain(root[2])) if root else b''
    mfat = []
    for s in chain(mini_start):
        mfat.extend(struct.unpack_from('<%dI' % per, sector(s), 0))

    def mini_stream(start, size):
        out, cur, guard = b'', start, 0
        while cur < 0xFFFFFFFA and guard < 1000000:
            off = cur * mssz
            out += mini_data[off:off + mssz]
            cur = mfat[cur] if cur < len(mfat) else 0xFFFFFFFE
            guard += 1
        return out[:size]

    streams = {}
    for name, typ, start, size in entries:
        if typ == 2:
            streams[name] = stream(start, size) if size >= cutoff else mini_stream(start, size)
    return streams

def _rk(rk):
    cents = rk & 1
    if rk & 2:
        v = rk >> 2
        if v & 0x20000000:
            v -= 0x40000000
        v = float(v)
    else:
        v = struct.unpack('<d', struct.pack('<Q', (rk & 0xFFFFFFFC) << 32))[0]
    return v / 100.0 if cents else v

def parse_wb(wb):
    """返回 [(sheet_name, {(row,col): value})]"""
    names = []
    sst = []
    sheets = []
    cur = None
    started = False
    pos, n = 0, len(wb)
    while pos + 4 <= n:
        rtype, rlen = struct.unpack_from('<HH', wb, pos)
        body = wb[pos + 4:pos + 4 + rlen]
        pos += 4 + rlen
        if rtype == 0x0085:  # BOUNDSHEET
            cch = body[6]
            flags = body[7]
            nm = (body[8:8 + cch * 2].decode('utf-16-le', 'replace') if flags & 1
                  else body[8:8 + cch].decode('latin-1'))
            names.append(nm)
        elif rtype == 0x0809:  # BOF
            if cur is not None:
                sheets.append(cur)
            cur = {}
            continue
        elif rtype == 0x000A:  # EOF
            if cur is not None:
                sheets.append(cur)
                cur = None
            continue
        elif rtype == 0x00FC:  # SST
            chunks = [body[8:]]
            while pos + 4 <= n:
                t2, l2 = struct.unpack_from('<HH', wb, pos)
                if t2 != 0x003C:
                    break
                chunks.append(wb[pos + 4:pos + 4 + l2])
                pos += 4 + l2
            unique = struct.unpack_from('<I', body, 4)[0]
            ci, off = 0, 0

            def avail():
                return len(chunks[ci]) - off

            def take(k):
                nonlocal ci, off
                out = b''
                while k > 0:
                    while ci < len(chunks) and avail() == 0:
                        ci += 1
                        off = 0
                    if ci >= len(chunks):
                        raise EOFError
                    m = min(k, avail())
                    out += chunks[ci][off:off + m]
                    off += m
                    k -= m
                return out

            for _ in range(unique):
                cch = struct.unpack('<H', take(2))[0]
                flags = take(1)[0]
                rich, ext, wide = flags & 8, flags & 4, flags & 1
                nruns = struct.unpack('<H', take(2))[0] if rich else 0
                extsz = struct.unpack('<I', take(4))[0] if ext else 0
                segs, remaining, curwide = [], cch, wide
                while remaining > 0:
                    if avail() == 0:
                        ci += 1
                        off = 0
                        if ci >= len(chunks):
                            break
                        curwide = chunks[ci][off] & 1
                        off += 1
                        continue
                    if curwide:
                        k = min(remaining, avail() // 2)
                        if k == 0:
                            off = len(chunks[ci])
                            continue
                        segs.append((True, chunks[ci][off:off + 2 * k]))
                        off += 2 * k
                    else:
                        k = min(remaining, avail())
                        segs.append((False, chunks[ci][off:off + k]))
                        off += k
                    remaining -= k
                s = ''.join(seg.decode('utf-16-le', 'replace') if w else seg.decode('latin-1')
                            for w, seg in segs)
                if rich:
                    take(nruns * 4)
                if ext:
                    take(extsz)
                sst.append(s)
        elif cur is not None:
            if rtype == 0x00FD:
                r, c, xf, isst = struct.unpack_from('<HHHI', body, 0)
                cur[(r, c)] = sst[isst] if isst < len(sst) else ''
            elif rtype == 0x0204:
                r, c, xf, cch = struct.unpack_from('<HHHH', body, 0)
                fl = body[8]
                cur[(r, c)] = (body[9:9 + cch * 2].decode('utf-16-le', 'replace') if fl & 1
                               else body[9:9 + cch].decode('latin-1'))
            elif rtype == 0x0203:
                r, c, xf, v = struct.unpack_from('<HHHd', body, 0)
                cur[(r, c)] = v
            elif rtype == 0x027E:
                r, c, xf, rk = struct.unpack_from('<HHHI', body, 0)
                cur[(r, c)] = _rk(rk)
            elif rtype == 0x00BD:
                r, c0 = struct.unpack_from('<HH', body, 0)
                for i in range((len(body) - 6) // 6):
                    cur[(r, c0 + i)] = _rk(struct.unpack_from('<I', body, 8 + i * 6)[0])
    if cur is not None:
        sheets.append(cur)
    out = []
    for i, cells in enumerate(sheets):
        if not cells:
            continue
        out.append((names[i] if i < len(names) else 'sheet%d' % (i + 1), cells))
    return out

def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    streams = read_cfb(open(src, 'rb').read())
    key = 'Workbook' if 'Workbook' in streams else 'Book'
    sheets = parse_wb(streams[key])
    for name, cells in sheets:
        maxr = max(r for r, c in cells)
        maxc = max(c for r, c in cells)
        rows = []
        for r in range(maxr + 1):
            row = [cells.get((r, c), '') for c in range(maxc + 1)]
            if any(str(x).strip() for x in row):
                rows.append(row)
        safe = re.sub(r'[\\/:*?"<>|]', '_', name).strip() or 'sheet'
        dst = os.path.join(outdir, '%s.csv' % safe)
        with io.open(dst, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerows(rows)
        print('%-24s %4d rows x %2d cols -> %s' % (name, len(rows), maxc + 1, os.path.basename(dst)))

if __name__ == '__main__':
    main()
