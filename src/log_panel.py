import tkinter as tk
from tkinter import ttk
import threading
import time

LOG_LEVELS = ["Debug", "Info", "WARN", "WARN_HIGH", "ERROR", "CRITICAL_ERROR", "Disabled"]

LOG_SOURCES = ["radio", "messaging", "rotor", "laser", "ootx", "system"]

LOG_SOURCE_LABELS = {
    "radio": "Radio",
    "messaging": "消息",
    "rotor": "电机",
    "laser": "激光",
    "ootx": "OOTX",
    "system": "系统",
}


class LogPanel(tk.Frame):
    def __init__(self, parent, serial_manager, terminal, **kwargs):
        super().__init__(parent, **kwargs)
        self._serial = serial_manager
        self._terminal = terminal

        status_frame = tk.LabelFrame(self, text="当前状态")
        status_frame.pack(fill=tk.X, padx=4, pady=(4, 8))

        inner = tk.Frame(status_frame)
        inner.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(inner, text="级别:").pack(side=tk.LEFT)
        self._status_level = tk.Label(inner, text="--", font=("", 9, "bold"))
        self._status_level.pack(side=tk.LEFT, padx=(4, 16))

        level_frame = tk.LabelFrame(self, text="日志级别")
        level_frame.pack(fill=tk.X, padx=4, pady=(0, 8))

        level_row = tk.Frame(level_frame)
        level_row.pack(fill=tk.X, padx=8, pady=6)

        self._level_var = tk.StringVar(value="Info")
        level_combo = ttk.Combobox(level_row, textvariable=self._level_var,
                                   values=LOG_LEVELS, state="readonly", width=14)
        level_combo.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(level_row, text="应用", command=self._apply_level).pack(side=tk.LEFT)

        src_frame = tk.LabelFrame(self, text="日志来源筛选")
        src_frame.pack(fill=tk.X, padx=4, pady=(0, 8))

        self._check_vars = {}

        grid = tk.Frame(src_frame)
        grid.pack(padx=8, pady=6, fill=tk.X)

        for i, src in enumerate(LOG_SOURCES):
            label = LOG_SOURCE_LABELS.get(src, src)
            var = tk.BooleanVar(value=True)
            self._check_vars[src] = var
            row = i // 3
            col = i % 3
            cb = tk.Checkbutton(grid, text=label, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=8, pady=2)

        btn_row = tk.Frame(src_frame)
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Button(btn_row, text="应用筛选", command=self._apply_sources).pack(side=tk.RIGHT)

        op_frame = tk.LabelFrame(self, text="操作")
        op_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        op_row = tk.Frame(op_frame)
        op_row.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(op_row, text="从设备刷新状态", command=self.refresh).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(op_row, text="重置为默认 (Debug + 全开)",
                   command=self._reset_default).pack(side=tk.LEFT)

    def refresh(self):
        if not self._serial.is_connected():
            return

        def do_refresh():
            resp_level = self._serial.send_command("log get level", wait_response=True, timeout=2.0)
            level_text = "--"
            if resp_level:
                for lv in LOG_LEVELS:
                    if lv in resp_level:
                        level_text = lv
                        break

            resp_srcs = self._serial.send_command("log get srcs", wait_response=True, timeout=2.0)
            all_words = " ".join(resp_srcs.strip().split("\n")).split()
            has_all = "all" in all_words
            active = {w for w in all_words if w in LOG_SOURCES}

            if has_all:
                active = set(LOG_SOURCES)

            self.after(0, lambda: self._status_level.configure(text=level_text))
            self.after(0, lambda: self._level_var.set(level_text if level_text in LOG_LEVELS else "Info"))
            for src, var in self._check_vars.items():
                self.after(0, lambda v=var, s=src: v.set(s in active))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _apply_level(self):
        if not self._serial.is_connected():
            return
        level = self._level_var.get()

        def do_send():
            self._serial.send_command(f"log set {level}", wait_response=True, timeout=2.0)
            self.after(0, lambda: self._status_level.configure(text=level))

        threading.Thread(target=do_send, daemon=True).start()

    def _apply_sources(self):
        if not self._serial.is_connected():
            return
        selected = [src for src, var in self._check_vars.items() if var.get()]
        if not selected:
            return
        if len(selected) == len(LOG_SOURCES):
            cmd = "log set srcs all"
        else:
            cmd = f"log set srcs {' '.join(selected)}"

        def do_send():
            self._serial.send_command(cmd, wait_response=True, timeout=2.0)

        threading.Thread(target=do_send, daemon=True).start()

    def _reset_default(self):
        if not self._serial.is_connected():
            return

        def do_reset():
            self._serial.send_command("log set Debug", wait_response=True, timeout=2.0)
            self._serial.send_command("log set srcs all", wait_response=True, timeout=2.0)
            self.after(0, lambda: self._status_level.configure(text="Debug"))
            self.after(0, lambda: self._level_var.set("Debug"))
            for var in self._check_vars.values():
                self.after(0, lambda v=var: v.set(True))

        threading.Thread(target=do_reset, daemon=True).start()
