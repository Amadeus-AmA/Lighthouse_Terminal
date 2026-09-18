import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from backup_compare import restore_params_from_json, restore_fcal_to_device

PARTITION_HELP = (
    "Par0 / Par1 为正常运行参数区 (NORM), Par2 为出厂参数区 (FACT)。\n"
    "修复分区 = 用当前内存中的参数重新保存到指定分区; 加载分区 = 用分区内容覆盖当前参数。"
)


class MaintenancePanel(tk.Frame):
    def __init__(self, parent, serial_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self._serial = serial_manager
        self._build_partition_area()
        self._build_eeprom_area()
        self._build_power_area()
        self._build_restore_area()

    # ---------- 分区 ----------

    def _build_partition_area(self):
        part_frame = tk.LabelFrame(self, text="参数闪存分区 (param part / save / load)")
        part_frame.pack(fill=tk.X, padx=4, pady=(4, 2))

        cols = ("index", "type", "addr", "crc", "version")
        self._tree = ttk.Treeview(part_frame, columns=cols, show="headings", height=3)
        self._tree.heading("index", text="分区")
        self._tree.heading("type", text="类型")
        self._tree.heading("addr", text="地址")
        self._tree.heading("crc", text="CRC 状态")
        self._tree.heading("version", text="版本")
        for col, width in (("index", 60), ("type", 70), ("addr", 90),
                           ("crc", 130), ("version", 70)):
            self._tree.column(col, width=width, anchor="w")
        self._tree.pack(fill=tk.X, padx=8, pady=(6, 2))
        self._tree.tag_configure("bad", foreground="#e74c3c")

        op_row = tk.Frame(part_frame)
        op_row.pack(fill=tk.X, padx=8, pady=(2, 4))
        tk.Label(op_row, text="分区:").pack(side=tk.LEFT)
        self._part_var = tk.StringVar(value="0")
        ttk.Combobox(op_row, textvariable=self._part_var, width=4,
                     values=["0", "1", "2"], state="readonly").pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(op_row, text="查看分区状态", command=self._refresh_parts).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(op_row, text="保存到分区 (修复)", command=self._save_partition).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(op_row, text="从分区加载", command=self._load_partition).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(op_row, text="擦除分区", command=self._erase_partition).pack(side=tk.LEFT)

        tk.Label(part_frame, text=PARTITION_HELP, font=("", 8), fg="#7f8c8d",
                 justify=tk.LEFT, anchor="w").pack(anchor="w", padx=8, pady=(0, 6))

    def _refresh_parts(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return

        def work():
            resp = self._serial.send_command("param part", wait_response=True, timeout=2.0)
            self.after(0, lambda: self._update_parts(resp))

        threading.Thread(target=work, daemon=True).start()

    def _update_parts(self, text: str):
        if not text:
            return
        from data_parser import parse_param_part
        parts = parse_param_part(text)
        if not parts:
            return
        for item in self._tree.get_children():
            self._tree.delete(item)
        for p in parts:
            self._tree.insert("", tk.END, values=(
                f"Par{p['index']}", p["type"], p["address"],
                "CRC-OK" if p["crc_ok"] else f"CRC-BAD ({p['crc_stored']}≠{p['crc_calc']})",
                p["version"]),
                tags=() if p["crc_ok"] else ("bad",))

    def _save_partition(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        n = self._part_var.get()
        if messagebox.askyesno(
                "确认保存分区",
                f"将用当前参数执行: param save {n}\n该分区原有内容会被覆盖(修复)。确认?",
                icon="warning"):
            self._send_async(f"param save {n}", f"已保存到分区 {n}")

    def _load_partition(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        n = self._part_var.get()
        if messagebox.askyesno(
                "确认加载分区",
                f"将执行: param load {n}\n当前内存中的参数会被分区内容覆盖。确认?",
                icon="warning"):
            self._send_async(f"param load {n}", f"已从分区 {n} 加载")

    def _erase_partition(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        n = self._part_var.get()
        if messagebox.askyesno(
                "确认擦除分区",
                f"将执行: param erase {n}\n该分区参数将全部丢失, 需重新校准/配置!\n确定要擦除分区 {n} ?",
                icon="warning"):
            self._send_async(f"param erase {n}", f"已擦除分区 {n}")

    def _send_async(self, cmd: str, done_msg: str):
        def work():
            resp = self._serial.send_command(cmd, wait_response=True, timeout=3.0)
            self.after(0, lambda: messagebox.showinfo("完成", f"{done_msg}\n\n{resp.strip()[-200:]}"))

        threading.Thread(target=work, daemon=True).start()

    # ---------- EEPROM ----------

    def _build_eeprom_area(self):
        ee_frame = tk.LabelFrame(self, text="EEPROM 读取 (eeprom r <地址> <长度>)")
        ee_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        op_row = tk.Frame(ee_frame)
        op_row.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(op_row, text="地址:").pack(side=tk.LEFT)
        self._ee_addr = tk.Entry(op_row, width=10, font=("Consolas", 9))
        self._ee_addr.insert(0, "0x00")
        self._ee_addr.pack(side=tk.LEFT, padx=(4, 12))
        tk.Label(op_row, text="长度:").pack(side=tk.LEFT)
        self._ee_len = tk.Entry(op_row, width=8, font=("Consolas", 9))
        self._ee_len.insert(0, "16")
        self._ee_len.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(op_row, text="读取", command=self._eeprom_read).pack(side=tk.LEFT)

        ee_body = tk.Frame(ee_frame)
        ee_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 6))

        self._ee_out = tk.Text(ee_body, height=8, wrap=tk.NONE, state="disabled",
                               bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        ee_scroll = ttk.Scrollbar(ee_body, orient=tk.HORIZONTAL, command=self._ee_out.xview)
        ee_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self._ee_out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._ee_out.configure(xscrollcommand=ee_scroll.set)

    def _eeprom_read(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        addr = self._ee_addr.get().strip() or "0x00"
        length = self._ee_len.get().strip() or "16"
        cmd = f"eeprom r {addr} {length}"

        def work():
            resp = self._serial.send_command(cmd, wait_response=True, timeout=2.0)
            self.after(0, lambda: self._ee_append(f">>> {cmd}\n{resp}\n"))

        threading.Thread(target=work, daemon=True).start()

    def _ee_append(self, text: str):
        self._ee_out.configure(state="normal")
        self._ee_out.insert("1.0", text)
        self._ee_out.configure(state="disabled")

    # ---------- 基站电源 ----------

    def _build_power_area(self):
        power_frame = tk.LabelFrame(self, text="基站电源 (sys.standby)")
        power_frame.pack(fill=tk.X, padx=4, pady=2)

        btn_row = tk.Frame(power_frame)
        btn_row.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btn_row, text="休眠基站", command=lambda: self._standby(True)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="唤醒基站", command=lambda: self._standby(False)).pack(side=tk.LEFT, padx=(0, 12))
        self._power_status = tk.Label(btn_row, text="", fg="#27ae60")
        self._power_status.pack(side=tk.LEFT)

        tk.Label(power_frame,
                 text="休眠后电机与激光停转, 串口控制台仍然可用, 点击唤醒即可恢复。",
                 font=("", 8), fg="#7f8c8d", anchor="w").pack(anchor="w", padx=8, pady=(0, 6))

    def _standby(self, sleep: bool):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        cmd = f"param set sys.standby {'true' if sleep else 'false'}"
        action = "休眠" if sleep else "唤醒"

        def work():
            self._serial.send_command(cmd, wait_response=True, timeout=2.0)
            self.after(0, lambda: self._power_status.configure(
                text=f"已发送{action}命令 ({time.strftime('%H:%M:%S')})"))

        threading.Thread(target=work, daemon=True).start()

    # ---------- 恢复 / DFU ----------

    def _build_restore_area(self):
        rst_frame = tk.LabelFrame(self, text="恢复与固件")
        rst_frame.pack(fill=tk.X, padx=4, pady=(2, 4))

        btn_row = tk.Frame(rst_frame)
        btn_row.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btn_row, text="恢复参数备份...", command=self._restore_params).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="写入 FCAL 校准...", command=self._restore_fcal).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="进入无线 DFU 模式", command=self._enter_dfu).pack(side=tk.LEFT)

        tk.Label(rst_frame,
                 text="DFU: 进入后控制台关闭, 使用 nrfutil dfu serial -b115200 -prn 1 刷写无线电固件。",
                 font=("", 8), fg="#7f8c8d", anchor="w").pack(anchor="w", padx=8, pady=(0, 6))

    def _check_connected(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return False
        return True

    def _restore_params(self):
        if self._check_connected():
            restore_params_from_json(self._serial, self)

    def _restore_fcal(self):
        if self._check_connected():
            restore_fcal_to_device(self._serial, self)

    def _enter_dfu(self):
        if not self._check_connected():
            return
        if messagebox.askyesno(
                "确认进入 DFU",
                "将发送 serial_dfu, 控制台会话随即关闭,\n"
                "之后请用 nrfutil 在同一串口刷写无线电固件。\n确认进入?",
                icon="warning"):
            def work():
                self._serial.send_command("serial_dfu", wait_response=True, timeout=2.0)
            threading.Thread(target=work, daemon=True).start()

    def clear(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
