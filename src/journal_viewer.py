"""履历记录查看器 (0x554-0xFC0)"""
import json
import os
import re
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from i18n import tr_text, trf

LOG_BASE = 0x554
LOG_TOP = 0xFC0
READ_LEN = LOG_TOP - LOG_BASE  # 2668
BOOTS_TOLERANCE = 5


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


# ---------- 校验 ----------

def _store_path(serial_id: str):
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        d = os.path.dirname(os.path.abspath(__file__))
        base = os.path.dirname(d) if os.path.basename(d) == "src" else d
    return os.path.join(base, ".lht", f"{serial_id}.json")


def load_store(serial_id: str) -> dict:
    if not serial_id:
        return {}
    try:
        return json.loads(open(_store_path(serial_id), encoding="utf-8").read())
    except (OSError, ValueError):
        return {}


def save_store(serial_id: str, data: dict) -> None:
    if not serial_id:
        return
    path = _store_path(serial_id)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data["t"] = time.strftime("%y%m%d%H%M")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=0)
    except OSError:
        pass


def analyze_consistency(recs: list, cb: int, cf: int, cl: int, st: dict) -> list:
    out = []
    mb = max((r['boots'] for r in recs), default=0)
    mf = max((r['faults'] for r in recs), default=0)
    ml = max((r['life'] for r in recs), default=0)
    lb = st.get('b', 0)
    lf = st.get('f', 0)
    ll = st.get('l', 0)
    if recs and cb < mb:
        out.append('E1')
    if recs and cf < mf:
        out.append('E2')
    if recs and cl < ml:
        out.append('E3')
    if not recs and (cb > 10 or lb > 10):
        out.append('E4')
    if lb and cb < lb:
        out.append('E5')
    if ll and cl < ll:
        out.append('E6')
    if recs and cb > mb + BOOTS_TOLERANCE:
        out.append('E7')
    return out


def update_store(serial_id: str, recs: list, cb: int, cf: int, cl: int) -> dict:
    st = load_store(serial_id)
    st['b'] = max(st.get('b', 0), cb, max((r['boots'] for r in recs), default=0))
    st['f'] = max(st.get('f', 0), cf, max((r['faults'] for r in recs), default=0))
    st['l'] = max(st.get('l', 0), cl, max((r['life'] for r in recs), default=0))
    save_store(serial_id, st)
    return st


def open_journal_viewer(parent, serial_manager, device_id_provider=None):
    win = tk.Toplevel(parent)
    win.title(tr_text("履历日志查看器 (journal 记录区 0x554-0xFC0)"))
    win.geometry("1020x640")

    verdict = tk.Label(win, text="", anchor="w", font=("", 9, "bold"), justify=tk.LEFT)
    verdict.pack(fill=tk.X, padx=8, pady=(6, 0))

    info = tk.Label(win, text=trf("journal.reading"), fg="#7f8c8d", anchor="w")
    info.pack(fill=tk.X, padx=8, pady=(2, 2))

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
        tree.heading(key, text=tr_text(text))
        tree.column(key, width=width, anchor=anchor)
    tree.tag_configure("newest", background="#fff3cd")

    ys = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=2)
    ys.pack(side=tk.RIGHT, fill=tk.Y)

    summary = tk.Label(win, text="", anchor="w", font=("", 9, "bold"))
    summary.pack(fill=tk.X, padx=8, pady=(2, 6))

    def work():
        # 1) 日志区
        cmd = f"eeprom r 0x{LOG_BASE:X} {READ_LEN}"
        resp = serial_manager.send_command(cmd, wait_response=True, timeout=20.0)
        # 2) 当前参数计数
        cur = {}
        for key in ("journal.boots", "journal.faults", "journal.life"):
            r = serial_manager.send_command(f"param get {key}",
                                            wait_response=True, timeout=2.0)
            for line in r.splitlines():
                if line.strip().startswith(key):
                    cur[key] = line.strip().split()[1]

        def done():
            if ":" not in resp:
                info.configure(text=trf("journal.read_failed"), fg="#e74c3c")
                return
            buf = _parse_hexdump(resp)
            recs = _extract_records(buf)
            for r in recs:
                tree.insert("", tk.END, values=(
                    f"0x{r['addr']:04X}",
                    f"{r['life']} s ({r['life'] / 3600:.2f} h)",
                    r['boots'], r['locks'], r['faults'], r['spins'], r['sweeps']),
                    tags=("newest",) if r is recs[-1] else ())
            info.configure(text=trf("journal.source"), fg="#7f8c8d")
            if recs:
                lo, hi = recs[0], recs[-1]
                summary.configure(text=trf("journal.summary", count=len(recs),
                                           boots0=lo['boots'], boots1=hi['boots'],
                                           faults0=lo['faults'], faults1=hi['faults'],
                                           hours=hi['life'] / 3600))
            else:
                summary.configure(text=tr_text("未识别到有效记录"))

            # 3) 校验
            try:
                cb = int(cur.get("journal.boots", 0))
                cf = int(cur.get("journal.faults", 0))
                cl = int(cur.get("journal.life", 0))
            except ValueError:
                verdict.configure(text=tr_text("journal.cur_unreadable"), fg="#e67e22")
                return
            sid = device_id_provider() if device_id_provider else ""
            st = load_store(sid)
            codes = analyze_consistency(recs, cb, cf, cl, st)
            if codes:
                verdict.configure(text=trf("journal.verdict_fail", codes=" ".join(codes)),
                                  fg="#e74c3c")
            else:
                verdict.configure(text=trf("journal.verdict_ok"), fg="#27ae60")
            if sid:
                update_store(sid, recs, cb, cf, cl)

        win.after(0, done)

    threading.Thread(target=work, daemon=True).start()
