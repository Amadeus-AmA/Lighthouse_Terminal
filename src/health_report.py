"""一键体检报告: 参数分区 + 设备履历 + 转子状态 汇总, 正式排版, 问题项加粗红字。"""
import re
import threading
import time
import tkinter as tk
from tkinter import ttk, Toplevel

from i18n import current_language, tr_text, trf
from journal_viewer import (RING_SLOTS, _crc48, _parse_hexdump, _parse_ring,
                            analyze_consistency, load_store, update_store)

MAX_JITTER_PPM = 50.0


def _parse_stats(text: str):
    m = re.search(r'mu\s*=\s*([0-9.]+)\s*ms\s*,\s*sigma\s*=\s*([0-9.]+)\s*us'
                  r'\s*\(\s*([0-9.]+)\s*ppm\s*\)', text)
    if not m:
        return None
    return {'mu': float(m.group(1)), 'sigma': float(m.group(2)), 'ppm': float(m.group(3))}


def _parse_freq(text: str):
    m = re.search(r'([0-9.]+)\s*Hz', text)
    if not m:
        return None
    return float(m.group(1))


class HealthReport(Toplevel):
    def __init__(self, parent, serial_manager, device_id_provider=None):
        super().__init__(parent)
        self._serial = serial_manager
        self._device_id_provider = device_id_provider

        self.title(tr_text("一键体检报告"))
        self.geometry("760x620")
        self.transient(parent)

        bar = tk.Frame(self)
        bar.pack(fill=tk.X, padx=8, pady=(8, 2))
        ttk.Button(bar, text=tr_text("重新体检"), command=self.refresh).pack(side=tk.LEFT)
        self._status = tk.Label(bar, text="", fg="#7f8c8d")
        self._status.pack(side=tk.LEFT, padx=(10, 0))

        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 8))
        self._text = tk.Text(body, wrap=tk.WORD, state="disabled",
                             bg="#fbfbf7", font=("Consolas", 10))
        ys = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self._text.yview)
        ys.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._text.configure(yscrollcommand=ys.set)

        self._text.tag_configure("title", font=("Consolas", 12, "bold"),
                                 justify=tk.CENTER, spacing3=4)
        self._text.tag_configure("section", font=("Consolas", 11, "bold"),
                                 foreground="#2c3e50", spacing1=8, spacing3=2)
        self._text.tag_configure("problem", font=("Consolas", 10, "bold"),
                                 foreground="#e74c3c")
        self._text.tag_configure("ok", foreground="#27ae60")
        self._text.tag_configure("dim", foreground="#95a5a6")
        self._text.tag_configure("rule", foreground="#bdc3c7")

        self.refresh()

    # ---------- 渲染 ----------

    def _line(self, text="", tags=()):
        self._text.insert("end", text + "\n", tags)

    def _begin_report(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._line("═" * 52, ("rule",))
        self._line(tr_text("Lighthouse 基站体检报告"), ("title",))
        self._line(tr_text("生成时间: {t}").format(t=time.strftime("%Y-%m-%d %H:%M:%S")), ("dim",))
        self._line("═" * 52, ("rule",))

    def _end_report(self, problems: int, checks: int):
        if problems:
            self._line(tr_text("结论: {n} 项检查, {p} 项需要关注").format(n=checks, p=problems),
                       ("problem",))
        else:
            self._line(tr_text("结论: {n} 项检查, 全部正常").format(n=checks), ("ok",))
        self._line("═" * 52, ("rule",))
        self._text.configure(state="disabled")

    # ---------- 数据采集 ----------

    def refresh(self):
        self._status.configure(text=tr_text("正在采集..."))
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._line(tr_text("正在采集数据, 请稍候..."), ("dim",))
        self._text.configure(state="disabled")
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            d = {}
            d['parts'] = self._serial.send_command("param part", wait_response=True, timeout=3.0)
            # stats 命令是开关 (toggle): 开流后等最多 10 秒抓统计行 (抓到即止), 关流恢复原状
            d['stats'] = ""
            try:
                captured = [self._serial.send_command("stats", wait_response=True, timeout=2.0)]
                got = False
                for _ in range(20):
                    time.sleep(0.5)
                    probe = self._serial.send_command("uptime", wait_response=True, timeout=2.0)
                    captured.append(probe)
                    if 'rotor (k' in probe:
                        got = True
                        break
                self._serial.send_command("stats", wait_response=True, timeout=2.0)
                # 若统计流原本就开着, 探测并恢复关闭状态
                for _ in range(2):
                    probe = self._serial.send_command("uptime", wait_response=True, timeout=2.0)
                    if 'rotor (k' not in probe:
                        break
                    self._serial.send_command("stats", wait_response=True, timeout=2.0)
                d['stats'] = '\n'.join(c for c in captured if c)
            except Exception:
                pass
            d['freq'] = self._serial.send_command("freq", wait_response=True, timeout=3.0)
            d['ring'] = self._serial.send_command(
                "eeprom r 0x580 2624", wait_response=True, timeout=20.0)
            d['params'] = {}
            for key in ("journal.boots", "journal.faults", "journal.life", "sys.name"):
                r = self._serial.send_command(f"param get {key}",
                                              wait_response=True, timeout=2.0)
                for line in r.splitlines():
                    line = line.strip()
                    if line.startswith(key):
                        d['params'][key] = line.split()[1]
            d['sid'] = self._device_id_provider() if self._device_id_provider else ""
            d['err'] = None
            # 履历校验 (环先读、活值后读; 竞态码重测一次定案)
            recs, zeros, bad = _parse_ring(_parse_hexdump(d['ring'], 0x580, RING_SLOTS * 48))
            ok_recs = [r for r in recs if r['crc_ok']]
            try:
                cb = int(d['params'].get("journal.boots", 0))
                cf = int(d['params'].get("journal.faults", 0))
                cl = int(d['params'].get("journal.life", 0))
            except ValueError:
                cb = cf = cl = 0
            st = load_store(d['sid'])
            codes = analyze_consistency(ok_recs, cb, cf, cl, st, zeros)
            if any(c in codes for c in ('E1', 'E2', 'E3')):
                d['ring'] = self._serial.send_command(
                    "eeprom r 0x580 2624", wait_response=True, timeout=20.0)
                recs, zeros, bad = _parse_ring(_parse_hexdump(d['ring'], 0x580, RING_SLOTS * 48))
                ok_recs = [r for r in recs if r['crc_ok']]
                try:
                    cb = int(d['params'].get("journal.boots", 0))
                    cf = int(d['params'].get("journal.faults", 0))
                    cl = int(d['params'].get("journal.life", 0))
                except ValueError:
                    pass
                codes = analyze_consistency(ok_recs, cb, cf, cl, st, zeros)
            d.update(recs=recs, zeros=zeros, bad=bad, codes=codes)
        except Exception as e:
            d = {'err': str(e)}
        self.after(0, lambda: self._render(d))

    # ---------- 渲染 ----------

    def _render(self, d):
        from data_parser import parse_param_part

        self._begin_report()
        problems = 0
        checks = 0

        if d.get('err'):
            self._line(tr_text("数据采集失败: {err}").format(err=d['err']), ("problem",))
            self._line(tr_text("请重新体检; 若反复失败, 检查串口连接与设备状态。"), ("dim",))
            self._end_report(1, 1)
            self._status.configure(text=tr_text("完成"))
            return

        name = d['params'].get("sys.name", "")
        port = getattr(self._serial, "port", "") or ""
        self._line(tr_text("设备名称: {name}    端口: {port}").format(name=name or "-", port=port or "-"),
                   ("dim",))
        self._line("")

        # ◆ 参数分区
        self._line(tr_text("◆ 参数分区"), ("section",))
        parts = parse_param_part(d['parts']) if d['parts'] else []
        for p in parts:
            checks += 1
            state = "CRC-OK" if p['crc_ok'] else "CRC-BAD"
            line = "  Par{index}  {type:<5} {state:<8} v{version}".format(
                index=p['index'], type=p['type'], state=state, version=p['version'])
            if p['crc_ok']:
                self._line(line + "   " + tr_text("正常"), ("ok",))
            else:
                problems += 1
                self._line(line + "   " + tr_text("分区 CRC 异常, 参数可能损坏"), ("problem",))
        if not parts:
            self._line(tr_text("无法读取分区状态"), ("problem",))
            problems += 1
            checks += 1
        self._line("")

        # ◆ 设备履历
        self._line(tr_text("◆ 设备履历"), ("section",))
        try:
            cb = int(d['params'].get("journal.boots", 0))
            cf = int(d['params'].get("journal.faults", 0))
            cl = int(d['params'].get("journal.life", 0))
        except ValueError:
            cb = cf = cl = 0
        self._line(tr_text("上电次数: {b}    累计运行: {h} h    历史故障: {f}").format(
            b=cb, h="%.1f" % (cl / 48_000_000 / 3600), f=cf))
        recs = d.get('recs', [])
        zeros = d.get('zeros', 0)
        bad = d.get('bad', 0)
        codes = d.get('codes', [])
        ok_recs = [r for r in recs if r['crc_ok']]
        checks += 1
        if bad == 0:
            self._line(tr_text("记录 CRC: {ok} 有效 / {bad} 异常").format(
                ok=len(ok_recs), bad=bad), ("ok",))
        elif bad <= 2:
            self._line(tr_text("记录 CRC: {ok} 有效 / {bad} 异常").format(
                ok=len(ok_recs), bad=bad), ("dim",))
            self._line(tr_text("少量坏记录常见于写入时断电或读取竞态, 一般非人为改动"), ("dim",))
        else:
            problems += 1
            self._line(tr_text("记录 CRC: {ok} 有效 / {bad} 异常").format(
                ok=len(ok_recs), bad=bad), ("problem",))
        checks += 1
        if cb >= 60 and zeros >= 4:
            problems += 1
            self._line(tr_text("空槽: {z}/{n} — 偏多").format(
                z=zeros, n=RING_SLOTS), ("problem",))
        else:
            self._line(tr_text("空槽: {z}/{n}").format(z=zeros, n=RING_SLOTS), ("ok",))
        checks += 1
        sid = d['sid']
        codes = d.get('codes', [])
        if codes:
            problems += 1
            self._line(trf("journal.verdict_fail", codes=" ".join(codes)), ("problem",))
        elif ok_recs or cb:
            self._line(trf("journal.verdict_ok"), ("ok",))
        if sid:
            update_store(sid, ok_recs, cb, cf, cl)
        self._line("")

        # ◆ 转子
        self._line(tr_text("◆ 转子"), ("section",))
        st_info = _parse_stats(d['stats']) if d['stats'] else None
        freq = _parse_freq(d['freq']) if d['freq'] else None
        checks += 1
        if st_info:
            line = tr_text("抖动 σ={s}us ({p} ppm)").format(s=st_info['sigma'], p=st_info['ppm'])
            if freq:
                line = tr_text("转速 {f} Hz    ").format(f=freq) + line
            if st_info['ppm'] <= MAX_JITTER_PPM:
                self._line(line + "   " + tr_text("正常"), ("ok",))
            else:
                problems += 1
                self._line(line + "   " + tr_text("抖动偏大, 建议关注轴承状态"), ("problem",))
        else:
            self._line(tr_text("无法读取转子统计 (设备可能处于休眠)"), ("dim",))
            if d['stats']:
                self._line("  " + d['stats'].strip()[:140], ("dim",))
            checks -= 1
        self._line("")

        self._end_report(problems, checks)
        self._status.configure(text=tr_text("完成"))


def open_health_report(parent, serial_manager, device_id_provider=None):
    return HealthReport(parent, serial_manager, device_id_provider)
