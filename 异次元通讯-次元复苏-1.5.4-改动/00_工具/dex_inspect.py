#!/usr/bin/env python3
"""Minimal DEX inspector: header, string pool, type/class names, method refs.

Usage: python dex_inspect.py <classes.dex> <outdir>
Writes: strings.txt, classes.txt, methods.txt, summary.txt
"""
import struct
import sys
import os
from collections import Counter


def uleb128(b, p):
    r = 0
    s = 0
    while True:
        v = b[p]
        p += 1
        r |= (v & 0x7F) << s
        if not v & 0x80:
            return r, p
        s += 7


def read_mutf8(b, p):
    _, p = uleb128(b, p)
    end = b.index(b"\x00", p)
    raw = b[p:end]
    return raw.decode("utf-8", "replace"), end + 1


class Dex:
    def __init__(self, path):
        self.b = open(path, "rb").read()
        b = self.b
        (self.string_ids_size, self.string_ids_off,
         self.type_ids_size, self.type_ids_off,
         self.proto_ids_size, self.proto_ids_off,
         self.field_ids_size, self.field_ids_off,
         self.method_ids_size, self.method_ids_off,
         self.class_defs_size, self.class_defs_off) = struct.unpack_from("<12I", b, 56)
        self.strings = []
        for i in range(self.string_ids_size):
            off = struct.unpack_from("<I", b, self.string_ids_off + i * 4)[0]
            s, _ = read_mutf8(b, off)
            self.strings.append(s)

    def type_name(self, idx):
        sidx = struct.unpack_from("<I", self.b, self.type_ids_off + idx * 4)[0]
        return self.strings[sidx]

    def class_defs(self):
        out = []
        for i in range(self.class_defs_size):
            o = self.class_defs_off + i * 32
            class_idx, access, super_idx, ifaces, src_idx, annos, cdata, svalues = struct.unpack_from(
                "<8I", self.b, o)
            out.append({
                "name": self.type_name(class_idx),
                "super": self.type_name(super_idx) if super_idx != 0xFFFFFFFF else None,
                "src": self.strings[src_idx] if src_idx != 0xFFFFFFFF else None,
                "access": access,
            })
        return out

    def method_refs(self):
        out = []
        b = self.b
        for i in range(self.method_ids_size):
            cls_idx, proto_idx, name_idx = struct.unpack_from("<HHI", b, self.method_ids_off + i * 8)
            out.append((self.type_name(cls_idx), self.strings[name_idx]))
        return out

    def field_refs(self):
        out = []
        b = self.b
        for i in range(self.field_ids_size):
            cls_idx, type_idx, name_idx = struct.unpack_from("<HHI", b, self.field_ids_off + i * 8)
            out.append((self.type_name(cls_idx), self.strings[name_idx], self.type_name(type_idx)))
        return out


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    d = Dex(src)
    classes = d.class_defs()
    methods = d.method_refs()
    fields = d.field_refs()

    with open(os.path.join(outdir, "strings.txt"), "w", encoding="utf-8") as f:
        for s in d.strings:
            f.write(s + "\n")

    with open(os.path.join(outdir, "classes.txt"), "w", encoding="utf-8") as f:
        for c in sorted(classes, key=lambda x: x["name"]):
            f.write("%s\tsuper=%s\tsrc=%s\n" % (c["name"], c["super"], c["src"]))

    with open(os.path.join(outdir, "methods.txt"), "w", encoding="utf-8") as f:
        for cls, name in sorted(methods):
            f.write("%s->%s\n" % (cls, name))

    with open(os.path.join(outdir, "fields.txt"), "w", encoding="utf-8") as f:
        for cls, name, t in sorted(fields):
            f.write("%s->%s:%s\n" % (cls, name, t))

    pkgs = Counter()
    for c in classes:
        n = c["name"]
        if n.startswith("L"):
            n = n[1:]
        parts = n.split("/")
        pkgs["/".join(parts[:3])] += 1

    with open(os.path.join(outdir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("file=%s bytes=%d\n" % (src, len(d.b)))
        f.write("strings=%d types=%d protos=%d fields=%d methods=%d classes=%d\n" % (
            d.string_ids_size, d.type_ids_size, d.proto_ids_size,
            d.field_ids_size, d.method_ids_size, d.class_defs_size))
        f.write("\n== top package prefixes ==\n")
        for k, v in pkgs.most_common(60):
            f.write("%5d  %s\n" % (v, k))
    print(open(os.path.join(outdir, "summary.txt"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
