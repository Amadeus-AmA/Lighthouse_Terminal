"""救砖刷固件窗口: isp → CRP DISABLD 引导器盘 → 写入 firmware.bin → 用户断电完成刷写。"""
import ctypes
import hashlib
import os
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, Toplevel

from i18n import tr_text

MAX_FLASH_SIZE = 131072  # 128KB flash


def _find_crp_drive():
    """查找 LPC 引导器挂载的 CRP DISABLD 磁盘 (仅 Windows)。"""
    if os.name != "nt":
        return None
    kernel32 = ctypes.windll.kernel32
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        root = letter + ":\\"
        name = ctypes.create_unicode_buffer(64)
        try:
            if kernel32.GetVolumeInformationW(root, name, 64, None, None, None, None, 0):
                if "CRP" in name.value.upper():
                    return root
        except Exception:
            pass
    return None


class FirmwareFlasher(Toplevel):
    def __init__(self, parent, serial_manager):
        super().__init__(parent)
        self._serial = serial_manager
        self._path = None
        self._busy = False

        self.title(tr_text("固件刷写 (救砖)"))
        self.geometry("720x520")
        self.transient(parent)

        warn = tk.Label(self, text=tr_text(
            "只刷同型号设备的固件文件 (.bin, ≤128KB)。\n"
            "刷写过程: 设备重启进入引导器 → 固件写入引导器盘 → 给基站断电再上电完成。\n"
            "过程中串口断开属正常; EEPROM 参数与设备履历不受影响。"),
            fg="#e67e22", anchor="w", justify=tk.LEFT)
        warn.pack(fill=tk.X, padx=8, pady=(8, 4))

        file_row = tk.Frame(self)
        file_row.pack(fill=tk.X, padx=8)
        tk.Label(file_row, text=tr_text("固件文件 (.bin):")).pack(side=tk.LEFT)
        self._file_var = tk.StringVar()
        ttk.Entry(file_row, textvariable=self._file_var, width=52).pack(side=tk.LEFT, padx=(6, 6))
        ttk.Button(file_row, text=tr_text("浏览..."), command=self._pick_file).pack(side=tk.LEFT)
        self._info = tk.Label(self, text="", fg="#7f8c8d", anchor="w", justify=tk.LEFT)
        self._info.pack(fill=tk.X, padx=8, pady=(2, 4))

        btn_row = tk.Frame(self)
        btn_row.pack(fill=tk.X, padx=8, pady=(2, 4))
        self._flash_btn = ttk.Button(btn_row, text=tr_text("开始刷写"),
                                     command=self._start_flash)
        self._flash_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._backup_btn = ttk.Button(btn_row, text=tr_text("从引导器读取固件..."),
                                      command=self._backup_from_drive)
        self._backup_btn.pack(side=tk.LEFT)

        log_frame = tk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 8))
        self._log = tk.Text(log_frame, height=14, wrap=tk.WORD, state="disabled",
                            bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        ys = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self._log.yview)
        ys.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._log.configure(yscrollcommand=ys.set)

    # ---------- UI helpers ----------

    def _append(self, line: str):
        def work():
            self._log.configure(state="normal")
            self._log.insert("end", line + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, work)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title=tr_text("选择要刷写的固件文件 (.bin)"),
            filetypes=[(tr_text("固件文件"), "*.bin"), (tr_text("所有文件"), "*.*")])
        if not path:
            return
        self._path = path
        self._file_var.set(path)
        try:
            size = os.path.getsize(path)
        except OSError as e:
            self._info.configure(text=tr_text("读取文件失败: {err}").format(err=e), fg="#e74c3c")
            return
        if size > MAX_FLASH_SIZE:
            self._info.configure(
                text=tr_text("文件大小 {size} 字节, 超出 128KB 闪存上限").format(size=size),
                fg="#e74c3c")
            return
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        self._info.configure(text=tr_text("大小 {size} 字节 | SHA-256 {sha}...")
                             .format(size=size, sha=digest[:16]), fg="#27ae60")

    # ---------- flash flow ----------

    def _start_flash(self):
        if self._busy:
            return
        if os.name != "nt":
            messagebox = _messagebox()
            messagebox.showwarning(tr_text("提示"), tr_text("仅支持 Windows 系统"))
            return
        if not self._path or not os.path.exists(self._path):
            messagebox = _messagebox()
            messagebox.showwarning(tr_text("提示"), tr_text("请先选择固件文件"))
            return
        if not self._serial.is_connected():
            messagebox = _messagebox()
            messagebox.showwarning(tr_text("提示"), tr_text("请先连接设备"))
            return
        if not messagebox_askyesno_flash():
            return
        self._busy = True
        self._flash_btn.configure(state="disabled")
        threading.Thread(target=self._flash_work, daemon=True).start()

    def _flash_work(self):
        # 1) 进入引导器: isp 会让设备重启, 串口随之消失 (异常属预期)
        self._append(tr_text("发送 isp, 设备重启进入引导器..."))
        try:
            self._serial.send_command("isp", wait_response=False, timeout=1.0)
        except Exception:
            pass
        time.sleep(0.5)
        try:
            self._serial.disconnect()
        except Exception:
            pass
        self._append(tr_text("串口已断开 (预期行为)"))

        # 2) 等 CRP 盘
        self._append(tr_text("等待 CRP DISABLD 磁盘出现..."))
        drive = None
        for _ in range(30):
            drive = _find_crp_drive()
            if drive:
                break
            time.sleep(1)
        if not drive:
            self._append(tr_text("未检测到 CRP 磁盘。请确认设备已进入引导器")
                         + tr_text("(可按住烧录键重新上电), 再重试。"))
            self._done()
            return
        self._append(tr_text("检测到引导器磁盘 {drive}, 正在写入固件...").format(drive=drive))

        # 3) 写入
        try:
            dst = os.path.join(drive, "firmware.bin")
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copyfile(self._path, dst)
            size = os.path.getsize(dst)
            self._append(tr_text("固件数据已写入 ({size} 字节)。").format(size=size))
        except Exception as e:
            self._append(tr_text("写入失败: {err}").format(err=e))
            self._done()
            return

        # 4) 指引断电
        self._append(tr_text("请给基站断电再上电完成刷写。"))
        self._append(tr_text("断电前无串口属正常现象; 上电后重新连接即可验证。"))
        self._done()

    def _done(self):
        def work():
            self._busy = False
            self._flash_btn.configure(state="normal")
        self.after(0, work)

    # ---------- backup flow ----------

    def _backup_from_drive(self):
        if self._busy:
            return
        drive = _find_crp_drive()
        if not drive:
            messagebox = _messagebox()
            messagebox.showinfo(
                tr_text("提示"),
                tr_text("当前不在引导器模式: 未检测到 CRP 磁盘。\n"
                        "先点击 开始刷写 进入引导器, 或按住烧录键重新上电。"))
            return
        src = os.path.join(drive, "firmware.bin")
        if not os.path.exists(src):
            messagebox = _messagebox()
            messagebox.showwarning(tr_text("提示"), tr_text("引导器盘上没有 firmware.bin, 请稍候重试"))
            return
        path = filedialog.asksaveasfilename(
            title=tr_text("保存固件备份"),
            defaultextension=".bin",
            initialfile="firmware_backup.bin",
            filetypes=[(tr_text("固件文件"), "*.bin")])
        if not path:
            return
        shutil.copyfile(src, path)
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        self._append(tr_text("已保存固件备份: {path}").format(path=path))
        self._append("SHA-256: " + digest)


def _messagebox():
    from tkinter import messagebox
    return messagebox


def messagebox_askyesno_flash():
    from tkinter import messagebox
    return messagebox.askyesno(
        tr_text("确认刷写固件"),
        tr_text("将重启设备进入引导器并写入所选固件。\n"
                "EEPROM 参数与设备履历不受影响。\n"
                "过程中串口断开属正常现象。\n\n继续?"),
        icon="warning")
