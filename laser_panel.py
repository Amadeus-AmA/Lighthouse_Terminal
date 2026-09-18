import tkinter as tk
from tkinter import ttk, messagebox
import threading

STATE_PARAMS = [
    ("sys.emission_enable", "全局发射使能"),
    ("laser.enable", "激光使能"),
    ("laser.current", "驱动电流 (mA)"),
    ("laser.pwr", "目标功率"),
    ("laser.pwr.detected", "实测功率"),
    ("laser.pwr.average", "平均功率"),
    ("laser.bias", "偏置"),
    ("laser.phase.on", "开相位"),
    ("laser.phase.off", "关相位"),
    ("laser.apc", "自动功率控制"),
]

BOOL_PARAMS = [
    ("sys.emission_enable", "全局发射使能"),
    ("laser.enable", "激光使能"),
    ("laser.interlock", "激光互锁"),
    ("laser.fullspin", "全周扫描"),
    ("laser.apc", "自动功率控制 APC"),
]

NUM_PARAMS = [
    ("laser.current", "驱动电流 (mA)"),
    ("laser.pwr", "目标功率"),
    ("laser.bias", "偏置"),
    ("laser.phase.on", "开相位"),
    ("laser.phase.off", "关相位"),
    ("laser.apc.i", "APC 积分系数"),
]

# ISL58303 寄存器名 (来自真机 isl58303 dump)
REG_NAMES = [
    "CHIP_ID", "SERIAL_CTRL", "STATUS", "SDIO", "ENABLE",
    "IOUT1_THRESHOLD_SCALE", "IOUT1_COLOR_SCALE", "IOUT1_THRESHOLD_DAC", "IOUT1_COLOR_DAC",
    "IOUT2_THRESHOLD_SCALE", "IOUT2_COLOR_SCALE", "IOUT2_THRESHOLD_DAC", "IOUT2_COLOR_DAC",
    "IOUT3_THRESHOLD_SCALE", "IOUT3_COLOR_SCALE", "IOUT3_THRESHOLD_DAC", "IOUT3_COLOR_DAC",
    "ADC_SELECT", "ADC_RESULT", "ADC_CTRL_1", "ADC_CTRL_2",
]

# 正常基站参考值 (真机/公开 dump 观测)
REF_HINT = "参考值(正常基站): current≈123, pwr≈70, phase.on≈10, phase.off≈350"


class LaserPanel(tk.Frame):
    def __init__(self, parent, serial_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self._serial = serial_manager
        self._auto_id = None
        self._auto_var = tk.BooleanVar(value=False)

        self._build_state_area()
        self._build_control_area()
        self._build_isl_area()

        self._set_auto_refresh(False)

    # ---------- 布局 ----------

    def _build_state_area(self):
        state_frame = tk.LabelFrame(self, text="激光实时状态 (param list)")
        state_frame.pack(fill=tk.X, padx=4, pady=(4, 2))

        self._state_labels = {}
        for i, (key, label) in enumerate(STATE_PARAMS):
            row, col = i // 2, i % 2
            cell = tk.Frame(state_frame)
            cell.grid(row=row, column=col, sticky="w", padx=10, pady=1)
            tk.Label(cell, text=f"{label}:", width=14, anchor="e").pack(side=tk.LEFT)
            val_lbl = tk.Label(cell, text="--", width=16, anchor="w",
                               font=("Consolas", 9), fg="#1a5fb4")
            val_lbl.pack(side=tk.LEFT)
            self._state_labels[key] = val_lbl

        btn_row = tk.Frame(state_frame)
        btn_row.grid(row=(len(STATE_PARAMS) + 1) // 2, column=0, columnspan=2,
                     sticky="w", padx=10, pady=(4, 2))
        ttk.Button(btn_row, text="刷新状态", command=self.refresh).pack(side=tk.LEFT)
        ttk.Checkbutton(btn_row, text="自动刷新 (3秒)", variable=self._auto_var,
                        command=self._toggle_auto).pack(side=tk.LEFT, padx=(12, 0))

    def _build_control_area(self):
        ctrl_frame = tk.LabelFrame(self, text="开关与参数控制 (param set, 修改需谨慎)")
        ctrl_frame.pack(fill=tk.X, padx=4, pady=2)

        self._bool_vars = {}
        for key, label in BOOL_PARAMS:
            row = tk.Frame(ctrl_frame)
            row.pack(fill=tk.X, padx=8, pady=1)
            var = tk.BooleanVar(value=False)
            self._bool_vars[key] = var
            cb = tk.Checkbutton(row, text=label, variable=var)
            cb.pack(side=tk.LEFT)
            ttk.Button(row, text="应用", width=6,
                       command=lambda k=key: self._apply_bool(k)).pack(side=tk.RIGHT)

        num_frame = tk.Frame(ctrl_frame)
        num_frame.pack(fill=tk.X, padx=8, pady=(4, 2))

        self._num_entries = {}
        for i, (key, label) in enumerate(NUM_PARAMS):
            row, col = i // 2, i % 2
            cell = tk.Frame(num_frame)
            cell.grid(row=row, column=col, sticky="w", padx=4, pady=1)
            tk.Label(cell, text=label, width=14, anchor="e").pack(side=tk.LEFT)
            entry = tk.Entry(cell, width=10, font=("Consolas", 9))
            entry.pack(side=tk.LEFT, padx=(4, 4))
            ttk.Button(cell, text="设置", width=5,
                       command=lambda k=key: self._apply_num(k)).pack(side=tk.LEFT)
            self._num_entries[key] = entry

        tk.Label(ctrl_frame, text=REF_HINT,
                 font=("", 8), fg="#7f8c8d").pack(anchor="w", padx=8)
        tk.Label(ctrl_frame, text="提示: 若设备不识别 true/false, 请改在终端发送 param set <参数> 1 或 0",
                 font=("", 8), fg="#7f8c8d").pack(anchor="w", padx=8, pady=(2, 4))

    def _build_isl_area(self):
        bottom = tk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        isl_frame = tk.LabelFrame(bottom, text="ISL58303 激光驱动寄存器")
        isl_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))

        op_row = tk.Frame(isl_frame)
        op_row.pack(fill=tk.X, padx=8, pady=(6, 2))
        ttk.Button(op_row, text="读取全部寄存器", command=self._isl_dump_all).pack(side=tk.LEFT)

        rw_row = tk.Frame(isl_frame)
        rw_row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(rw_row, text="寄存器:").pack(side=tk.LEFT)
        self._reg_combo = ttk.Combobox(rw_row, width=20, values=REG_NAMES, font=("Consolas", 9))
        self._reg_combo.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(rw_row, text="读取寄存器", command=self._isl_read).pack(side=tk.LEFT)
        tk.Label(rw_row, text="值:").pack(side=tk.LEFT, padx=(12, 0))
        self._val_entry = tk.Entry(rw_row, width=12, font=("Consolas", 9))
        self._val_entry.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(rw_row, text="写入寄存器", command=self._isl_write).pack(side=tk.LEFT)

        raw_row = tk.Frame(isl_frame)
        raw_row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(raw_row, text="自定义命令:").pack(side=tk.LEFT)
        self._raw_entry = tk.Entry(raw_row, font=("Consolas", 9))
        self._raw_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        self._raw_entry.bind("<Return>", lambda e: self._isl_raw())
        ttk.Button(raw_row, text="发送", command=self._isl_raw).pack(side=tk.LEFT)

        self._isl_out = tk.Text(isl_frame, height=8, wrap=tk.WORD, state="disabled",
                                bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        self._isl_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 8))

        fpga_frame = tk.LabelFrame(bottom, text="FPGA 激光通道")
        fpga_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(2, 0))

        self._fpga_lbl = tk.Label(fpga_frame, text="LASER_STATUS: --", font=("Consolas", 10),
                                  fg="#7f8c8d", justify=tk.LEFT, anchor="w")
        self._fpga_lbl.pack(anchor="w", padx=10, pady=(6, 4))
        ttk.Button(fpga_frame, text="刷新 (fpga)", command=self._refresh_fpga).pack(anchor="w", padx=10, pady=(0, 8))

    # ---------- 状态刷新 ----------

    def refresh(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return

        def do_refresh():
            resp = self._serial.send_command("param list", wait_response=True, timeout=3.0)
            self.after(0, lambda: self._update_state(resp))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _update_state(self, text: str):
        if not text:
            return
        from data_parser import parse_param_list
        params = parse_param_list(text)
        for key, lbl in self._state_labels.items():
            if key in params:
                val = params[key]
                if isinstance(val, float) and val == int(val):
                    val = int(val)
                lbl.configure(text=str(val))
                if key in self._bool_vars and isinstance(val, str):
                    self._bool_vars[key].set(val.lower() in ("true", "1", "on", "yes"))

    def _toggle_auto(self):
        self._set_auto_refresh(self._auto_var.get())

    def _set_auto_refresh(self, enabled: bool):
        if self._auto_id is not None:
            self.after_cancel(self._auto_id)
            self._auto_id = None
        if enabled:
            self._auto_tick()

    def _auto_tick(self):
        if self._serial.is_connected():
            def do_refresh():
                resp = self._serial.send_command("param list", wait_response=True, timeout=2.0)
                self.after(0, lambda: self._update_state(resp))
            threading.Thread(target=do_refresh, daemon=True).start()
        self._auto_id = self.after(3000, self._auto_tick)

    def _refresh_fpga(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return

        def do_refresh():
            resp = self._serial.send_command("fpga", wait_response=True, timeout=2.0)
            self.after(0, lambda: self._update_fpga(resp))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _update_fpga(self, text: str):
        if not text:
            return
        from data_parser import parse_fpga
        info = parse_fpga(text)
        if "laser_status_hex" not in info:
            return
        desc = info.get("laser_status_desc", "")
        hexv = info.get("laser_status_hex", "")
        lines = [f"LASER_STATUS: 0x{hexv}"]
        if desc:
            lines[0] += f" ( {desc} )"
        for key, name in (("laser_ctrl", "LASER_CTRL"),
                          ("laser_apc_gain", "LASER_APC_GAIN"),
                          ("laser_on_delay", "LASER_ON_DELAY"),
                          ("laser_off_delay", "LASER_OFF_DELAY")):
            if key in info:
                line = f"{name}: {info[key]}"
                if key + "_desc" in info:
                    line += f" ( {info[key + '_desc']} )"
                lines.append(line)
        enabled = "ENABLE" in desc
        self._fpga_lbl.configure(text="\n".join(lines),
                                 foreground="#27ae60" if enabled else "#7f8c8d")

    # ---------- 写操作 ----------

    def _confirm_send(self, cmd: str, extra="") -> bool:
        return messagebox.askyesno(
            "确认修改",
            f"即将发送:\n\n{cmd}\n\n{extra}\n该操作会修改设备参数, 确认执行?",
            icon="warning"
        )

    def _send_and_show(self, cmd: str):
        def do_send():
            resp = self._serial.send_command(cmd, wait_response=True, timeout=2.0)
            self.after(0, lambda: self._append_out(f">>> {cmd}\n{resp}\n"))
            self.after(100, lambda: self._silent_refresh())

        threading.Thread(target=do_send, daemon=True).start()

    def _silent_refresh(self):
        if self._serial.is_connected():
            def do_refresh():
                resp = self._serial.send_command("param list", wait_response=True, timeout=2.0)
                self.after(0, lambda: self._update_state(resp))
            threading.Thread(target=do_refresh, daemon=True).start()

    def _apply_bool(self, key: str):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        value = "true" if self._bool_vars[key].get() else "false"
        cmd = f"param set {key} {value}"
        if self._confirm_send(cmd):
            self._send_and_show(cmd)

    def _apply_num(self, key: str):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        value = self._num_entries[key].get().strip()
        if not value:
            messagebox.showwarning("提示", "请先输入参数值")
            return
        cmd = f"param set {key} {value}"
        if self._confirm_send(cmd):
            self._send_and_show(cmd)

    # ---------- ISL58303 寄存器 ----------

    def _append_out(self, text: str):
        self._isl_out.configure(state="normal")
        self._isl_out.insert(tk.END, text)
        self._isl_out.see(tk.END)
        self._isl_out.configure(state="disabled")

    def _check_connected(self) -> bool:
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return False
        return True

    def _isl_dump_all(self):
        if self._check_connected():
            self._send_and_show("isl58303")

    def _isl_read(self):
        if not self._check_connected():
            return
        reg = self._reg_combo.get().strip()
        if not reg:
            messagebox.showwarning("提示", "请选择或输入寄存器名称/地址")
            return
        self._send_and_show(f"isl58303 {reg}")

    def _isl_write(self):
        if not self._check_connected():
            return
        reg = self._reg_entry.get().strip()
        val = self._val_entry.get().strip()
        if not reg or not val:
            messagebox.showwarning("提示", "请输入寄存器和要写入的值")
            return
        cmd = f"isl58303 {reg} {val}"
        if messagebox.askyesno(
                "确认写入寄存器",
                f"即将直接写入激光驱动芯片寄存器:\n\n{cmd}\n\n"
                "错误取值可能导致激光器件永久损坏!\n确认写入?",
                icon="warning"):
            self._send_and_show(cmd)

    def _isl_raw(self):
        if not self._check_connected():
            return
        suffix = self._raw_entry.get().strip()
        if not suffix:
            return
        self._send_and_show(f"isl58303 {suffix}")

    # ---------- 断开清理 ----------

    def clear(self):
        self._set_auto_refresh(False)
        self._auto_var.set(False)
        for lbl in self._state_labels.values():
            lbl.configure(text="--")
        self._fpga_lbl.configure(text="LASER_STATUS: --", foreground="#7f8c8d")
        for var in self._bool_vars.values():
            var.set(False)
        self._isl_out.configure(state="normal")
        self._isl_out.delete("1.0", tk.END)
        self._isl_out.configure(state="disabled")
