"""履历日志查看器 — 解析 EEPROM journal 记录区 (0x554-0xFC0)

记录 48 字节/条, 地址 ≡ 0x14 (mod 0x30):
  +0x00 累计运行秒 (journal.life 高 32 位)   +0x04 boots   +0x08 locks
  +0x0C spins   +0x14 sweeps   +0x1C faults   +0x24 nonce   +0x2C 尾部校验字
固件在每次开关机时成批写入 3-4 条冗余记录, 位置由磨损均衡决定。
"""
import re
import struct
import tkinter as tk
from tkinter import ttk
import threading

LOG_BASE = 0x554
LOG_TOP = 0xFC0
READ_LEN = LOG_TOP - LOG_BASE  # 2668


def _parse_hexdump(text: str) -> bytes:
    data = {}
    for line in text.splitlines():
        m = re.match(r'^([0-9A-Fa-f]{6,8}):\s+((?:[0-9A-Fa-f]{2}[ \t]+)+)', line)
        if m:
            a = int(m.group(1), 16)
            for h in m.group(2).split():
                data[a] = int(h, 16)
                a += 1
    return bytes(data.get(LOG_BASE + i, 0) for i in range(READ_LEN))


def _extract_records(buf: bytes) -> list:
    recs = []
    for k in range((READ_LEN - 48) // 48 + 1):
        off = k * 48
        s = buf[off:off + 48]
        if s[0x10] or s[0x18] or s[0x28]:
            continue
        life, boots, locks = struct.unpack_from('<III', s, 0)
        spins = struct.unpack_from('<I', s, 0x0C)[0]
        sweeps = struct.unpack_from('<I', s, 0x14)[0]
        faults = struct.unpack_from('<I', s, 0x1C)[0]
        if not (1000 < life < (1 << 24)) or boots > (1 << 20) or locks > (1 << 20) or faults > (1 << 16):
            continue
        recs.append({'addr': LOG_BASE + off, 'life': life, 'boots': boots,
                     'locks': locks, 'spins': spins, 'sweeps': sweeps,
                     'faults': faults})
    recs.sort(key=lambda r: (r['life'], r['addr']))
    return recs


def open_journal_viewer(parent, serial_manager):
    win = tk.Toplevel(parent)
    win.title("履历日志查看器 (journal 记录区 0x554-0xFC0)")
    win.geometry("1020x600")

    info = tk.Label(win, text="正在读取 EEPROM 履历记录区 (0x554-0xFC0, 2668 字节)...",
                    fg="#7f8c8d", anchor="w")
    info.pack(fill=tk.X, padx=8, pady=(6, 2))

    cols = ("addr", "life", "boots", "locks", "faults", "spins", "sweeps")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for key, text, width, anchor in (
            ("addr", "记录地址", 90, "w"),
            ("life", "累计运行", 170, "w"),
            ("boots", "上电次数", 90, "e"),
            ("locks", "PLL 锁定", 90, "e"),
            ("faults", "故障数", 80, "e"),
            ("spins", "spins", 110, "e"),
            ("sweeps", "sweeps", 110, "e")):
        tree.heading(key, text=text)
        tree.column(key, width=width, anchor=anchor)
    tree.tag_configure("newest", background="#fff3cd")

    ys = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=2)
    ys.pack(side=tk.RIGHT, fill=tk.Y)

    summary = tk.Label(win, text="", anchor="w", font=("", 9, "bold"))
    summary.pack(fill=tk.X, padx=8, pady=(2, 6))

    def work():
        cmd = f"eeprom r 0x{LOG_BASE:X} {READ_LEN}"
        resp = serial_manager.send_command(cmd, wait_response=True, timeout=20.0)

        def done():
            if ":" not in resp:
                info.configure(text="读取失败: 未获取到数据, 请确认设备已连接", fg="#e74c3c")
                return
            buf = _parse_hexdump(resp)
            recs = _extract_records(buf)
            for r in recs:
                tree.insert("", tk.END, values=(
                    f"0x{r['addr']:04X}",
                    f"{r['life']} s ({r['life'] / 3600:.2f} h)",
                    r['boots'], r['locks'], r['faults'], r['spins'], r['sweeps']),
                    tags=("newest",) if r is recs[-1] else ())
            info.configure(text=f"数据源: eeprom r 0x{LOG_BASE:X} {READ_LEN} | "
                                f"记录按累计运行时间排序, 黄色行为最新一条", fg="#7f8c8d")
            if recs:
                lo, hi = recs[0], recs[-1]
                summary.configure(text=(
                    f"共 {len(recs)} 条记录 | 上电次数 {lo['boots']} → {hi['boots']} | "
                    f"故障 {lo['faults']} → {hi['faults']} | "
                    f"累计运行 {hi['life'] / 3600:.1f} h"))
            else:
                summary.configure(text="未识别到有效记录")

        win.after(0, done)

    threading.Thread(target=work, daemon=True).start()
