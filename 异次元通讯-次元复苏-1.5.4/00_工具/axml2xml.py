#!/usr/bin/env python3
"""Android binary XML (AXML) -> readable XML. Pure stdlib.

Usage: python axml2xml.py <AndroidManifest.xml> <out.xml>
"""
import struct
import sys
from xml.sax.saxutils import escape, quoteattr

RES_STRING_POOL_TYPE = 0x0001
RES_XML_TYPE = 0x0003
RES_XML_START_NAMESPACE_TYPE = 0x0100
RES_XML_END_NAMESPACE_TYPE = 0x0101
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
RES_XML_CDATA_TYPE = 0x0104
RES_XML_RESOURCE_MAP_TYPE = 0x0180

TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12
TYPE_FLOAT = 0x04

# Common android attribute resource ids -> names (subset, enough for manifests)
ATTR_IDS = {
    0x01010000: "theme", 0x01010001: "label", 0x01010002: "icon",
    0x01010003: "name", 0x01010004: "manageSpaceActivity", 0x01010005: "allowClearUserData",
    0x01010006: "permission", 0x01010007: "readPermission", 0x01010008: "writePermission",
    0x01010009: "protectionLevel", 0x0101000A: "permissionGroup",
    0x0101000B: "sharedUserId", 0x0101000C: "hasCode", 0x0101000D: "persistent",
    0x0101000E: "enabled", 0x0101000F: "debuggable", 0x01010010: "exported",
    0x01010011: "process", 0x01010012: "taskAffinity", 0x01010013: "multiprocess",
    0x01010014: "finishOnTaskLaunch", 0x01010015: "clearTaskOnLaunch",
    0x01010016: "stateNotNeeded", 0x01010017: "excludeFromRecents",
    0x01010018: "authorities", 0x01010019: "syncable", 0x0101001A: "initOrder",
    0x0101001B: "grantUriPermissions", 0x0101001C: "priority", 0x0101001D: "launchMode",
    0x0101001E: "screenOrientation", 0x0101001F: "configChanges",
    0x01010020: "description", 0x01010021: "targetPackage", 0x01010022: "handleProfiling",
    0x01010023: "functionalTest", 0x01010024: "value", 0x01010025: "resource",
    0x0101020C: "minSdkVersion", 0x0101021B: "versionCode", 0x0101021C: "versionName",
    0x01010270: "targetSdkVersion", 0x01010271: "maxSdkVersion",
    0x01010572: "compileSdkVersion", 0x01010573: "compileSdkVersionCodename",
    0x0101048F: "extractNativeLibs", 0x0101056F: "appComponentFactory",
    0x01010329: "installLocation", 0x0101021D: "roundIcon",
    0x01010570: "requestLegacyExternalStorage", 0x010104EA: "usesCleartextTraffic",
    0x01010527: "networkSecurityConfig", 0x0101026C: "allowBackup",
    0x0101021E: "supportsRtl", 0x01010225: "hardwareAccelerated",
    0x0101035F: "largeHeap", 0x01010285: "required",
    0x01010026: "language", 0x01010027: "country", 0x01010028: "screenSize",
    0x01010029: "characterEncoding", 0x01010030: "flags",
    0x01010079: "grantUriPermission", 0x0101007A: "maxRecursion",
    0x01010212: "minSdk",
    0x0101055C: "resizeableActivity",
    0x01010286: "usesSdk",
}


def read_len8(b, off):
    n = b[off]
    if n & 0x80:
        return ((n & 0x7F) << 8) | b[off + 1], off + 2
    return n, off + 1


def read_len16(b, off):
    n = struct.unpack_from("<H", b, off)[0]
    if n & 0x8000:
        return ((n & 0x7FFF) << 16) | struct.unpack_from("<H", b, off + 2)[0], off + 4
    return n, off + 2


def parse_string_pool(b, off):
    _, hsize, _ = struct.unpack_from("<HHI", b, off)
    count, _, flags, strings_start, _ = struct.unpack_from("<IIIII", b, off + 8)
    utf8 = bool(flags & 0x100)
    offs = struct.unpack_from("<%dI" % count, b, off + hsize)
    base = off + strings_start
    out = []
    for o in offs:
        p = base + o
        if utf8:
            _, p = read_len8(b, p)          # utf16 length
            ln, p = read_len8(b, p)         # utf8 byte length
            out.append(b[p:p + ln].decode("utf-8", "replace"))
        else:
            ln, p = read_len16(b, p)
            out.append(b[p:p + ln * 2].decode("utf-16-le", "replace"))
    return out


def fmt_value(t, data, strings):
    if t == TYPE_STRING:
        return quoteattr(strings[data]) if data < len(strings) else '""'
    if t == TYPE_REFERENCE:
        return '"@%08x"' % data
    if t == TYPE_INT_BOOLEAN:
        return '"%s"' % ("true" if data else "false")
    if t == TYPE_INT_HEX:
        return '"0x%x"' % data
    if t == TYPE_FLOAT:
        return '"%s"' % struct.unpack("<f", struct.pack("<I", data))[0]
    return '"%d"' % data


def parse(b):
    typ, hsize, size = struct.unpack_from("<HHI", b, 0)
    if typ != RES_XML_TYPE:
        raise SystemExit("not an AXML file (type=0x%04x)" % typ)
    strings, resmap = [], {}
    lines, stack, depth = [], [], 0
    pos = hsize
    while pos + 8 <= size:
        ctype, chsize, csize = struct.unpack_from("<HHI", b, pos)
        if csize == 0:
            break
        if ctype == RES_STRING_POOL_TYPE:
            strings = parse_string_pool(b, pos)
        elif ctype == RES_XML_RESOURCE_MAP_TYPE:
            n = (csize - chsize) // 4
            for i in range(n):
                resmap[i] = struct.unpack_from("<I", b, pos + chsize + i * 4)[0]
        elif ctype == RES_XML_START_ELEMENT_TYPE:
            ns_i, name_i, attr_start, attr_size, attr_count = struct.unpack_from("<iIHHH", b, pos + 16)
            name = strings[name_i]
            attrs = []
            ap = pos + 16 + attr_start
            for _ in range(attr_count):
                if ap + 20 > len(b):
                    break
                ans, an, raw, tsize, res0, ttype = struct.unpack_from("<iIIHBB", b, ap)
                vdata = struct.unpack_from("<I", b, ap + 16)[0]
                vtype = ttype
                aname = strings[an] if an < len(strings) else ""
                if aname == "" or aname is None:
                    aname = ATTR_IDS.get(resmap.get(an, 0), "attr_%04x" % resmap.get(an, 0))
                attrs.append((aname, fmt_value(vtype, vdata, strings)))
                ap += attr_size
            pad = "  " * depth
            lines.append("%s<%s%s>" % (
                pad, name,
                "".join(" %s=%s" % (k, v) for k, v in attrs)))
            stack.append((name, pad))
            depth += 1
        elif ctype == RES_XML_END_ELEMENT_TYPE:
            if stack:
                name, pad = stack.pop()
                depth = max(0, depth - 1)
                lines.append("%s</%s>" % (pad, name))
        elif ctype == RES_XML_CDATA_TYPE:
            data = struct.unpack_from("<i", b, pos + 16)[0]
            if data < len(strings):
                lines.append("  " * depth + escape(strings[data]))
        pos += csize
    return lines


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data = open(src, "rb").read()
    text = "\n".join(parse(data))
    open(dst, "w", encoding="utf-8").write(text)
    print("wrote %s (%d lines)" % (dst, text.count("\n") + 1))
