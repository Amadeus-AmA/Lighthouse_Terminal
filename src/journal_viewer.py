"""履历记录查看器 (journal 记录环 0x580-0xFC0)"""
import json
import os
import re
import struct
import sys
import threading
import time
import tkinter as tk
import zlib
from tkinter import ttk

from i18n import tr_text, trf

RING_BASE = 0x580
RING_SLOTS = 54
REC_SIZE = 48
BOOTS_TOLERANCE = 5

REASON_ZH = {
    'boot': '开机', 'lock': 'PLL 锁定', 'crash': '固件崩溃', 'mark': '标记',
    'fault-set': '故障置位', 'fault-clear': '故障清除', 'fault-motor': '电机故障',
    'fault-laser-dead': '激光失效', 'fault-laser-weak': '激光衰弱',
    'sleep': '进入休眠', 'wake': '休眠唤醒', 'user-request': '用户请求',
    'initial': '出厂初始', 'reset': '复位重启',
}

REASON_BY_IDX = ['initial', 'mark', 'boot', 'reset', 'sleep', 'wake', 'lock',
                 'user-request', 'fault-set', 'crash', 'fault-clear',
                 'fault-motor', 'fault-laser-weak', 'fault-laser-dead']


def _crc48(rec: bytes) -> int:
    b = bytearray(rec)
    b[0x28:0x2C] = b'\x00\x00\x00\x00'
    return zlib.crc32(bytes(b)) & 0xFFFFFFFF


def _parse_hexdump(text: str, base: int, length: int) -> bytes:
    data = {}
    for line in text.splitlines():
        m = re.match(r'^([0-9A-Fa-f]{6,8}):\s+((?:[0-9A-Fa-f]{2}[ \t]+)+)', line)
        if m:
            a = int(m.group(1), 16)
            for h in m.group(2).split():
                data[a] = int(h, 16)
                a += 1
    return bytes(data.get(base + i, 0) for i in range(length))


def _parse_ring(buf: bytes) -> tuple:
    """解析 54×48B 日志环 → (记录列表, 全零槽数, CRC 异常数)。记录含坏 CRC 也返回。"""
    recs, zeros, bad = [], 0, 0
    for i in range(RING_SLOTS):
        r = buf[i * REC_SIZE:(i + 1) * REC_SIZE]
        if len(r) < REC_SIZE or r == bytes(REC_SIZE):
            zeros += 1
            continue
        ok = _crc48(r) == struct.unpack_from('<I', r, 0x28)[0]
        if not ok:
            bad += 1
        ticks = struct.unpack_from('<Q', r, 0)[0]
        boots, locks = struct.unpack_from('<II', r, 8)
        spins, sweeps = struct.unpack_from('<QQ', r, 0x10)
        faults = struct.unpack_from('<I', r, 0x20)[0]
        ridx = r[0x24] if r[0x24] < len(REASON_BY_IDX) else 0
        recs.append({'slot': i, 'life': ticks, 'boots': boots, 'locks': locks,
                     'spins': spins, 'sweeps': sweeps, 'faults': faults,
                     'reason': REASON_BY_IDX[ridx], 'crc_ok': ok})
    recs.sort(key=lambda x: (x['life'], x['slot']))
    return recs, zeros, bad


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


def analyze_consistency(recs: list, cb: int, cf: int, cl: int, st: dict, zs: int = 0) -> list:
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
    if cb >= 60 and zs >= 4:
        out.append('E8')
    return out


def update_store(serial_id: str, recs: list, cb: int, cf: int, cl: int) -> dict:
    st = load_store(serial_id)
    st['b'] = max(st.get('b', 0), cb, max((r['boots'] for r in recs), default=0))
    st['f'] = max(st.get('f', 0), cf, max((r['faults'] for r in recs), default=0))
    st['l'] = max(st.get('l', 0), cl, max((r['life'] for r in recs), default=0))
    save_store(serial_id, st)
    return st


def _parse_journal_list(text: str) -> list:
    """解析固件 `journal list` 的 %JS 行: id, crc, ticks, boots, locks, spins, sweeps, faults, reason"""
    recs = []
    for line in text.splitlines():
        m = re.match(r'%JS\s+(\d+):\s+([0-9A-Fa-f]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)', line.strip())
        if m:
            g = m.groups()
            recs.append({'id': int(g[0]), 'crc': g[1], 'life': int(g[2]),
                         'boots': int(g[3]), 'locks': int(g[4]),
                         'spins': int(g[5]), 'sweeps': int(g[6]),
                         'faults': int(g[7]), 'reason': g[8]})
    recs.sort(key=lambda r: (r['life'], r['id']))
    return recs


def _parse_journal_faults(text: str) -> list:
    """解析 `journal faults` 的故障事件 (%J0 id crc type / %J1 时刻 / %J2 状态)"""
    events = []
    cur = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'%J0\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S+)', line)
        if m:
            cur = {'id': int(m.group(1)), 'crc': m.group(2), 'type': m.group(3)}
            continue
        if cur is None:
            continue
        m = re.match(r'%J1\s+(.*)', line)
        if m:
            cur['when'] = m.group(1).strip()
            continue
        m = re.match(r'%J2\s+(.*)', line)
        if m:
            cur['state'] = m.group(1).strip()
            events.append(cur)
            cur = None
    return events


def compose_laser_warnings(recs: list) -> list:
    counts = {}
    for r in recs:
        counts[r['reason']] = counts.get(r['reason'], 0) + 1
    out = []
    if counts.get('fault-laser-weak'):
        out.append(trf("journal.warn_laser_weak", count=counts['fault-laser-weak']))
    if counts.get('fault-laser-dead'):
        out.append(trf("journal.warn_laser_dead", count=counts['fault-laser-dead']))
    return out


def open_journal_viewer(parent, serial_manager, device_id_provider=None):
    win = tk.Toplevel(parent)
    win.title(tr_text("履历日志查看器 (journal 记录环 0x580-0xFC0)"))
    win.geometry("1020x640")

    verdict = tk.Label(win, text="", anchor="w", font=("", 9, "bold"), justify=tk.LEFT)
    verdict.pack(fill=tk.X, padx=8, pady=(6, 0))

    warn_lbl = tk.Label(win, text="", anchor="w", justify=tk.LEFT, fg="#e67e22")
    warn_lbl.pack(fill=tk.X, padx=8)

    info = tk.Label(win, text=trf("journal.reading"), fg="#7f8c8d", anchor="w")
    info.pack(fill=tk.X, padx=8, pady=(2, 2))

    faults_lbl = tk.Label(win, text="", anchor="w", justify=tk.LEFT,
                          font=("Consolas", 9), fg="#e67e22")
    faults_lbl.pack(fill=tk.X, padx=8)

    cols = ("id", "life", "boots", "locks", "faults", "spins", "sweeps", "reason", "crc")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for key, text, width, anchor in (
            ("id", "ID", 46, "w"),
            ("life", "累计运行", 150, "w"),
            ("boots", "上电次数", 80, "e"),
            ("locks", "PLL 锁定", 80, "e"),
            ("faults", "故障数", 70, "e"),
            ("spins", "spins", 100, "e"),
            ("sweeps", "sweeps", 100, "e"),
            ("reason", "原因", 150, "w"),
            ("crc", "CRC", 60, "center")):
        tree.heading(key, text=tr_text(text))
        tree.column(key, width=width, anchor=anchor)
    tree.tag_configure("newest", background="#fff3cd")
    tree.tag_configure("badcrc", foreground="#e74c3c")

    ys = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=2)
    ys.pack(side=tk.RIGHT, fill=tk.Y)

    summary = tk.Label(win, text="", anchor="w", font=("", 9, "bold"))
    summary.pack(fill=tk.X, padx=8, pady=(2, 0))

    crc_lbl = tk.Label(win, text="", anchor="w", fg="#7f8c8d")
    crc_lbl.pack(fill=tk.X, padx=8)

    legend = tk.Label(win, text="原因: " + "  ".join(
        f"{k}={v}" for k, v in REASON_ZH.items()),
        font=("", 8), fg="#95a5a6", anchor="w", wraplength=990, justify=tk.LEFT)
    legend.pack(fill=tk.X, padx=8, pady=(0, 6))

    # 控件引用 (测试/刷新用)
    win._ui = {'verdict': verdict, 'warn': warn_lbl, 'info': info,
               'faults': faults_lbl, 'tree': tree, 'summary': summary,
               'legend': legend, 'crc': crc_lbl}

    def work():
        try:
            cmd_faults = "journal faults"
            resp_f = serial_manager.send_command(cmd_faults, wait_response=True, timeout=6.0)
            resp_raw = serial_manager.send_command(f"eeprom r 0x{RING_BASE:X} {RING_SLOTS * REC_SIZE}",
                                                   wait_response=True, timeout=20.0)
            cur = {}
            for key in ("journal.boots", "journal.faults", "journal.life"):
                r = serial_manager.send_command(f"param get {key}",
                                                wait_response=True, timeout=2.0)
                for line in r.splitlines():
                    if line.strip().startswith(key):
                        cur[key] = line.strip().split()[1]
        except Exception as e:
            def fail():
                info.configure(text=trf("journal.read_failed") + " " + str(e), fg="#e74c3c")
            win.after(0, fail)
            return

        def done():
            buf = _parse_hexdump(resp_raw, RING_BASE, RING_SLOTS * REC_SIZE)
            recs, zeros, bad = _parse_ring(buf)
            events = _parse_journal_faults(resp_f) if "%J0" in resp_f else []
            for r in recs:
                reason_zh = REASON_ZH.get(r['reason'], r['reason'])
                tags = []
                if r is recs[-1]:
                    tags.append("newest")
                if not r['crc_ok']:
                    tags.append("badcrc")
                tree.insert("", tk.END, values=(
                    f"{r['slot']:02d}",
                    f"{r['life'] / 48_000_000 / 3600:.2f} h",
                    r['boots'], r['locks'], r['faults'], r['spins'], r['sweeps'],
                    f"{r['reason']} {reason_zh}",
                    "OK" if r['crc_ok'] else "BAD"),
                    tags=tuple(tags))
            info.configure(text=trf("journal.source"), fg="#7f8c8d")
            crc_lbl.configure(text=trf("journal.crc_summary", ok=len(recs) - bad,
                                       bad=bad, zero=zeros, total=RING_SLOTS))
            ok_recs = [r for r in recs if r['crc_ok']]
            if ok_recs:
                lo, hi = ok_recs[0], ok_recs[-1]
                summary.configure(text=trf("journal.summary", count=len(ok_recs),
                                           boots0=lo['boots'], boots1=hi['boots'],
                                           faults0=lo['faults'], faults1=hi['faults'],
                                           hours=hi['life'] / 48_000_000 / 3600))
            else:
                summary.configure(text=tr_text("未识别到有效记录"))

            try:
                cur_boots = int(cur.get("journal.boots", 0))
                cur_faults = int(cur.get("journal.faults", 0))
                cur_life = int(cur.get("journal.life", 0))
            except ValueError:
                verdict.configure(text=tr_text("journal.cur_unreadable"), fg="#e67e22")
                return
            sid = device_id_provider() if device_id_provider else ""
            st = load_store(sid)
            codes = analyze_consistency(ok_recs, cur_boots, cur_faults, cur_life, st, zeros)
            if codes:
                verdict.configure(text=trf("journal.verdict_fail", codes=" ".join(codes)),
                                  fg="#e74c3c")
            else:
                verdict.configure(text=trf("journal.verdict_ok"), fg="#27ae60")
            if sid:
                update_store(sid, ok_recs, cur_boots, cur_faults, cur_life)
            # 激光老化预警
            laser_warns = compose_laser_warnings(recs)
            if laser_warns:
                warn_lbl.configure(text="⚠ " + "\n⚠ ".join(laser_warns), fg="#e74c3c")
            else:
                warn_lbl.configure(text="")
            # 故障病史区
            if events:
                ev_text = "\n".join(
                    f"#{e['id']:02d}  {REASON_ZH.get(e['type'], e['type'])} ({e['type']})  @ {e['when']}"
                    for e in events)
                faults_lbl.configure(text=ev_text, fg="#e67e22")

        win.after(0, done)

    threading.Thread(target=work, daemon=True).start()
    return win
