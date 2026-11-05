#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 02_工作区 重新打包成 APK（未签名）。

用法:
    python repack.py <原始APK> <工作区目录> <输出APK>

规则:
  * 条目顺序沿用原始 APK 的中央目录顺序，工作区新增的文件追加在最后；
  * 每个条目沿用原始 APK 的压缩方式（STORED/DEFLATED）；
  * resources.arsc 强制 STORED，且其数据区按 4 字节对齐（Android 11+ targetSdk30+ 要求）；
  * 其它 STORED 条目同样做 4 字节对齐（用 0xD935 扩展字段填充）；
  * 剔除旧签名文件（META-INF/*.SF、*.RSA、*.DSA、MANIFEST.MF），其余 META-INF 保留；
  * 工作区缺失的原始条目会报错（除非显式 --allow-delete）。
"""
import hashlib
import json
import os
import struct
import sys
import zipfile

ALIGN = 4
ALIGN_ID = 0xD935
SIG_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def is_signature_entry(name: str) -> bool:
    up = name.upper()
    if up == "META-INF/MANIFEST.MF":
        return True
    if up.startswith("META-INF/") and up.endswith(SIG_SUFFIXES):
        return True
    return False


def align_extra(name_len: int, pos: int, pad_needed: int) -> bytes:
    """返回使 (pos+30+name_len+len(extra)) % ALIGN == 0 的扩展字段。"""
    base = pos + 30 + name_len
    pad = (-base) % ALIGN
    if pad == 0:
        return b""
    if pad < 4:
        pad += ALIGN
    payload = pad - 4
    return struct.pack("<HH", ALIGN_ID, payload) + b"\x00" * payload


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_delete = "--allow-delete" in sys.argv
    if len(args) != 3:
        print(__doc__)
        return 2
    src_apk, tree, out_apk = args

    if not os.path.isfile(src_apk):
        print(f"[错误] 原始 APK 不存在: {src_apk}")
        return 2
    if not os.path.isdir(tree):
        print(f"[错误] 工作区不存在: {tree}")
        return 2

    with zipfile.ZipFile(src_apk) as src:
        infos = src.infolist()

    # 工作区文件索引（zip 内部路径使用 /）
    have = {}
    for root, _dirs, files in os.walk(tree):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, tree).replace(os.sep, "/")
            have[rel] = full

    ordered = [i.filename for i in infos if not is_signature_entry(i.filename)]
    missing = [n for n in ordered if n not in have]
    if missing and not allow_delete:
        print("[错误] 工作区缺少以下原始条目（如确需删除请加 --allow-delete）:")
        for n in missing[:20]:
            print("   -", n)
        return 3
    ordered = [n for n in ordered if n in have]

    extra_files = sorted(n for n in have if n not in set(i.filename for i in infos))

    info_by_name = {i.filename: i for i in infos}
    changed, added, deleted = [], [], []
    entry_hashes = {}

    os.makedirs(os.path.dirname(os.path.abspath(out_apk)) or ".", exist_ok=True)
    tmp = out_apk + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)

    with zipfile.ZipFile(tmp, "w", allowZip64=True) as zout:
        f = zout.fp
        for name in ordered + extra_files:
            data = open(have[name], "rb").read()
            entry_hashes[name] = hashlib.sha256(data).hexdigest()

            if name in info_by_name:
                src_info = info_by_name[name]
                method = src_info.compress_type
                if name == "resources.arsc":
                    method = zipfile.ZIP_STORED
            else:
                src_info = None
                method = zipfile.ZIP_DEFLATED

            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = method
            zi.external_attr = (src_info.external_attr if src_info else 0) or 0o600 << 16
            zi.create_system = 0

            if method == zipfile.ZIP_STORED:
                pos = f.tell()
                zi.extra = align_extra(len(name.encode("utf-8")), pos, 0)
            zout.writestr(zi, data)

            if src_info is None:
                added.append(name)
            else:
                old = src_info
                if old.file_size != len(data):
                    changed.append(name)
                entry_hashes.setdefault(name, hashlib.sha256(data).hexdigest())

    os.replace(tmp, out_apk)

    # 原始条目里被工作区删掉的
    deleted = [n for n in info_by_name if n not in have and not is_signature_entry(n)]

    report = {
        "source_apk": os.path.abspath(src_apk),
        "tree": os.path.abspath(tree),
        "output": os.path.abspath(out_apk),
        "entries": len(ordered) + len(extra_files),
        "added": added,
        "deleted": deleted,
        "changed_by_size": changed,
        "output_sha256": sha256_file(out_apk),
        "output_size": os.path.getsize(out_apk),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    with open(out_apk + ".repack.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
