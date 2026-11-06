#!/usr/bin/env python3
"""Analyze the story CSV schema: directive tokens, row shapes, per-file stats.

Usage: python story_schema.py <story_csv_dir> <outdir>
"""
import csv
import os
import sys
from collections import Counter, defaultdict


def sniff(path):
    raw = open(path, "rb").read()
    return {
        "bytes": len(raw),
        "bom": raw[:3] == b"\xef\xbb\xbf",
        "crlf": raw.count(b"\r\n"),
        "lf": raw.count(b"\n"),
    }


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.endswith(".csv"))
    token_counter = Counter()
    token_by_file = defaultdict(Counter)
    shapes = Counter()
    stats = []
    sample_by_token = {}

    for fn in files:
        path = os.path.join(src, fn)
        info = sniff(path)
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        # drop trailing empty rows
        while rows and not any(c.strip() for c in rows[-1]):
            rows.pop()
        cols = Counter(len(r) for r in rows)
        speakers = Counter(r[0].strip() for r in rows if r and r[0].strip())
        n_opt = n_branch = n_dict = 0
        for r in rows:
            if len(r) < 3:
                continue
            d = r[2].strip()
            if not d:
                continue
            parts = [p.strip() for p in d.split(",")]
            for i, p in enumerate(parts):
                if not p:
                    continue
                key = p
                if p.isdigit():
                    key = "NUM"
                token_counter[key] += 1
                token_by_file[fn][key] += 1
                sample_by_token.setdefault(key, (fn, rows.index(r), d))
            if any(p == "选项" for p in parts):
                n_opt += 1
            if any(p.startswith("分支") for p in parts):
                n_branch += 1
            if "词典" in parts:
                n_dict += 1
        stats.append((fn, len(rows), dict(cols), n_opt, n_branch, n_dict, info,
                      speakers.most_common(12)))

    with open(os.path.join(outdir, "story_schema.txt"), "w", encoding="utf-8") as f:
        f.write("== files ==\n")
        for s in stats:
            fn, nrows, cols, no, nb, nd, info, spk = s
            f.write("\n%s\n  rows=%d  cols=%s  bytes=%d bom=%s crlf=%d\n"
                    % (fn, nrows, cols, info["bytes"], info["bom"], info["crlf"]))
            f.write("  option_rows=%d branch_rows=%d dict_rows=%d\n" % (no, nb, nd))
            f.write("  speakers=%s\n" % spk)
        f.write("\n== directive tokens (global) ==\n")
        for k, v in token_counter.most_common():
            f.write("%6d  %s   e.g. %s\n" % (v, k, sample_by_token.get(k)))
        f.write("\n== tokens per file ==\n")
        for fn in files:
            f.write("\n%s: %s\n" % (fn, dict(token_by_file[fn].most_common())))
    print(open(os.path.join(outdir, "story_schema.txt"), encoding="utf-8").read()[:6000])


if __name__ == "__main__":
    main()
