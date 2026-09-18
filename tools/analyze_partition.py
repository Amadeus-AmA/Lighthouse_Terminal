"""离线分析 EEPROM 分区 dump: 识别 CRC 算法 + 定位参数值"""
import re
import sys
import zlib
import struct


def parse_dump(text):
    data = {}
    for line in text.splitlines():
        m = re.match(r'^([0-9A-Fa-f]{4,8}):\s+((?:[0-9A-Fa-f]{2}[ \t]+)+)', line)
        if m:
            addr = int(m.group(1), 16)
            for h in m.group(2).split():
                data[addr] = int(h, 16)
                addr += 1
    if not data:
        return b""
    base, size = min(data), max(data) - min(data) + 1
    return bytes(data.get(base + i, 0) for i in range(size))


# ---------- 32 位 CRC 家族 (参数化实现) ----------
def crc32_generic(data, poly, init, refin, refout, xorout):
    def reflect(v, w):
        r = 0
        for i in range(w):
            if v & (1 << i):
                r |= 1 << (w - 1 - i)
        return r

    if refin:
        poly = reflect(poly, 32)
    crc = init
    for b in data:
        if refin:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ (poly if crc & 1 else 0)
        else:
            crc ^= b << 24
            for _ in range(8):
                crc = ((crc << 1) ^ (poly if crc & 0x80000000 else 0)) & 0xFFFFFFFF
    if refout != refin:
        crc = reflect(crc, 32)
    return crc ^ xorout


CRC_ALGOS = {
    "CRC-32/ISO-HDLC(zlib)": lambda d, s: zlib.crc32(d, s) ^ 0xFFFFFFFF if False else zlib.crc32(d, s),
    "CRC-32/JAMCRC": lambda d, s: zlib.crc32(d, s) ^ 0xFFFFFFFF,
    "CRC-32/MPEG-2": lambda d, s: crc32_generic(d, 0x04C11DB7, 0xFFFFFFFF, False, False, 0),
    "CRC-32/BZIP2": lambda d, s: crc32_generic(d, 0x04C11DB7, 0xFFFFFFFF, False, False, 0xFFFFFFFF),
    "CRC-32/CKSUM": lambda d, s: crc32_generic(d, 0x04C11DB7, 0, False, False, 0xFFFFFFFF) ^ 0xFFFFFFFF,
    "CRC-32C": lambda d, s: crc32_generic(d, 0x1EDC6F41, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
    "CRC-32C/JAM": lambda d, s: crc32_generic(d, 0x1EDC6F41, 0xFFFFFFFF, True, True, 0),
}


def fnv1a32(data):
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def fnv1_32(data):
    h = 0x811C9DC5
    for b in data:
        h = ((h * 0x01000193) & 0xFFFFFFFF) ^ b
    return h


def djb2(data):
    h = 5381
    for b in data:
        h = ((h * 33) + b) & 0xFFFFFFFF
    return h


def sum32(data):
    return sum(data) & 0xFFFFFFFF


def sum32_le(data):
    s = 0
    for i in range(0, len(data) - 3, 4):
        s = (s + struct.unpack_from("<I", data, i)[0]) & 0xFFFFFFFF
    return s


CHECKSUMS = {
    "FNV-1a": fnv1a32, "FNV-1": fnv1_32, "DJB2": djb2,
    "sum8bit": sum32, "sumU32LE": sum32_le,
    "adler32": zlib.adler32,
}


def analyze(path):
    with open(path, "r", encoding="utf-8") as f:
        d = parse_dump(f.read())
    print(f"=== {path}: {len(d)} bytes ===")
    if not d:
        print("解析失败"); return

    magic, version = d[0:4], struct.unpack_from("<I", d, 4)[0]
    crc_stored_le = struct.unpack_from("<I", d, 8)[0]
    crc_stored_be = struct.unpack_from(">I", d, 8)[0]
    print(f"magic={magic!r} version={version} crc_stored=0x{crc_stored_le:08X} (LE)")

    # 覆盖范围候选
    n = len(d)
    ranges = {
        "跳过CRC域[0:8]+[C:n]": d[0:8] + d[0x0C:n],
        "仅数据[C:n]": d[0x0C:n],
        "数据[VDR1后][10:n]": d[0x10:n],
        "仅头部[0:8]": d[0:8],
        "仅版本[4:8]": d[4:8],
        "CRC清零[0:8]+00*4+[C:n]": d[0:8] + b"\x00" * 4 + d[0x0C:n],
        "全部[0:n]": d[0:n],
        "数据去尾部[C:170]": d[0x0C:0x170],
        "数据去尾部[C:174]": d[0x0C:0x174],
    }
    seeds = [0, 0xFFFFFFFF]
    hits = []
    for rname, blob in ranges.items():
        for s in seeds:
            for aname, fn in CRC_ALGOS.items():
                try:
                    c = fn(blob, s)
                except Exception:
                    continue
                if c in (crc_stored_le, crc_stored_be):
                    hits.append((rname, aname, f"seed=0x{s:08X}", hex(c)))
            for aname, fn in CHECKSUMS.items():
                try:
                    c = fn(blob)
                except Exception:
                    continue
                if c in (crc_stored_le, crc_stored_be):
                    hits.append((rname, aname, "seed=0", hex(c)))
    if hits:
        print(">>> CRC 命中:")
        for h in hits:
            print("   ", h)
    else:
        print(">>> 未命中任何标准 CRC/校验和变体")

    # 数值扫描: 找可能的参数值
    print("\n-- 可辨认的 float(对齐) --")
    for off in range(0, n - 3, 4):
        v = struct.unpack_from("<f", d, off)[0]
        if 1e-6 < abs(v) < 1e6 and (abs(v) > 0.001 or v == 0):
            print(f"  0x{off:02X}: {v:.6g}", end="")
            if abs(v - 0.05) < 1e-9: print("  <- timebase.p?")
            elif v == 0.0: print("  <- timebase.i?")
            elif v == 1.0: print("  <- timebase.d?")
            elif abs(v - 0.999) < 1e-6: print("  <- timebase.k?")
            elif abs(v - 0.95) < 1e-9: print("  <- laser.pwr.k1?")
            elif abs(v - 0.212129) < 1e-4: print("  <- laser.pwr.m?")
            elif abs(v - 1.825058) < 1e-4: print("  <- laser.pwr.b1?")
            elif abs(v + 8.311882) < 1e-4: print("  <- laser.pwr.b2?")
            else: print()
    print("\n-- u32 LE < 2^24 的值(可能是计数器) --")
    for off in range(0, n - 3):
        v = struct.unpack_from("<I", d, off)[0]
        if 0 < v < (1 << 24):
            print(f"  0x{off:02X}: {v} (0x{v:X})")
    print()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(p)
