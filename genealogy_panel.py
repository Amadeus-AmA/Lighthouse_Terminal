import tkinter as tk
from tkinter import ttk, messagebox
import threading

GENEALOGY_IDS = ["model", "top", "main", "upper", "antenna", "laser", "motor",
                 "chassis", "spare1", "spare2", "spare3"]

GENEALOGY_LABELS = {
    "model": "整机型号 (协议广播 Model)",
    "top": "整机顶层 SN",
    "main": "主板 (Main PCB)",
    "upper": "上层板 (Upper PCB)",
    "antenna": "天线",
    "laser": "激光模组",
    "motor": "电机总成",
    "chassis": "机壳",
    "spare1": "备用位 1",
    "spare2": "备用位 2",
    "spare3": "备用位 3",
}

# 修改会影响设备识别的字段, 写入前加强确认
SENSITIVE_IDS = {"model", "top", "main", "upper"}

# 家谱区槽位: model 4 字节, 其余 25 字节/槽 (字符串 null 结尾, 空置 = 全零)
GENEALOGY_SLOTS = {
    "model": (0x480, 4),
    "top": (0x484, 25),
    "main": (0x49D, 25),
    "upper": (0x4B6, 25),
    "antenna": (0x4CF, 25),
    "laser": (0x4E8, 25),
    "motor": (0x501, 25),
    "chassis": (0x51A, 25),
    "spare1": (0x533, 25),
    "spare2": (0x54C, 25),
    "spare3": (0x565, 25),
}


def _display(gid: str) -> str:
    return f"{gid} — {GENEALOGY_LABELS[gid]}"


class GenealogyPanel(tk.Frame):
    def __init__(self, parent, serial_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._serial = serial_manager
        self._writing = False

        header = ttk.Label(
            self, text="硬件溯源 — 设备各组件序列号与版本信息",
            font=("", 9, "bold"), foreground="#e5c07b"
        )
        header.pack(anchor="w", padx=4, pady=(4, 2))

        # 底部编辑区先占位, 再让日志树占满剩余空间
        self._build_editor()

        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        self._tree = ttk.Treeview(body, columns=("value",), show="tree headings")
        self._tree.heading("#0", text="溯源项")
        self._tree.heading("value", text="信息")
        self._tree.column("#0", width=200)
        self._tree.column("value", width=520, anchor="w")
        self._tree.tag_configure("dim", foreground="#7f8c8d")
        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)

        scroll_y = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        for key in GENEALOGY_IDS:
            label = GENEALOGY_LABELS.get(key, key)
            self._tree.insert("", tk.END, text=label, values=("--",))

    # ---------- 编辑区 ----------

    def _build_editor(self):
        editor = tk.LabelFrame(self, text="字段编辑 (genealogy set <id> <serial> <part>)")
        editor.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=(2, 4))

        row = tk.Frame(editor)
        row.pack(fill=tk.X, padx=8, pady=(6, 2))

        tk.Label(row, text="字段:").pack(side=tk.LEFT)
        self._edit_field = tk.StringVar(value=_display(GENEALOGY_IDS[0]))
        combo = ttk.Combobox(row, textvariable=self._edit_field, state="readonly",
                             width=28, values=[_display(g) for g in GENEALOGY_IDS])
        combo.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(row, text="序列号:").pack(side=tk.LEFT)
        self._edit_serial = tk.Entry(row, width=16, font=("Consolas", 9))
        self._edit_serial.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(row, text="版本:").pack(side=tk.LEFT)
        self._edit_part = tk.Entry(row, width=14, font=("Consolas", 9))
        self._edit_part.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(row, text="写入字段", command=self._write_field).pack(side=tk.LEFT)

        self._edit_status = tk.Label(
            editor, text="提示: 两栏都填 - = 槽位写零, 恢复出厂空置显示 (- -); "
                         "spare 槽可随意测试; model/top/main/upper 为设备身份字段, 修改需谨慎。",
            font=("", 8), fg="#7f8c8d", anchor="w")
        self._edit_status.pack(anchor="w", padx=8, pady=(0, 6))

    def _gid_from_display(self, text: str):
        gid = text.split(" — ")[0].strip()
        return gid if gid in GENEALOGY_IDS else None

    def _on_row_select(self, event=None):
        sel = self._tree.selection()
        if not sel:
            return
        label = self._tree.item(sel[0], "text")
        for gid in GENEALOGY_IDS:
            if GENEALOGY_LABELS[gid] == label:
                self._edit_field.set(_display(gid))
                return

    # ---------- 写入 ----------

    def _write_field(self):
        if self._writing:
            return
        if self._serial is None or not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        gid = self._gid_from_display(self._edit_field.get())
        serial = self._edit_serial.get().strip()
        part = self._edit_part.get().strip()
        if not gid:
            return

        # 两栏都填 - = 槽位写零, 恢复出厂空置 (genealogy set 只能写入可见字符, 达不到空置态)
        zero_fill = (serial == "-" and part == "-")
        if zero_fill:
            addr, size = GENEALOGY_SLOTS[gid]
            cmd = f"eeprom w 0x{addr:04X} {size}"
            data = " ".join(["00"] * size)
        else:
            if not serial or not part:
                messagebox.showwarning("提示", "序列号和版本都要填写 (两栏都填 - 可清零恢复空置)")
                return
            cmd = f"genealogy set {gid} {serial} {part}"
            data = None

        sensitive = gid in SENSITIVE_IDS
        msg = f"即将执行:\n\n{cmd}\n"
        if data:
            msg += f"数据: {data}\n"
        msg += "\n"
        if zero_fill:
            msg += f"将把 {gid} 的槽位 (EEPROM 0x{addr:04X}, {size} 字节) 整体清零,\n恢复出厂空置显示。\n"
        if sensitive:
            msg += "该字段是设备身份信息, 修改会影响设备识别!\n"
        msg += "\n确认写入?"
        if not messagebox.askyesno("确认写入", msg,
                                   icon="warning" if (sensitive or zero_fill) else "info"):
            return

        self._writing = True
        self._edit_status.configure(text=f"正在写入 {gid} ...", fg="#7f8c8d")

        def work():
            if zero_fill:
                # 进入 eeprom 数据录入模式 (此步无提示符, 不等待), 再发数据行
                self._serial.send_command(cmd, wait_response=False)
                resp = self._serial.send_command(data, wait_response=True, timeout=3.0)
            else:
                resp = self._serial.send_command(cmd, wait_response=True, timeout=2.0)
            lst = self._serial.send_command("genealogy list", wait_response=True, timeout=2.0)
            self.after(0, lambda: self._after_write(zero_fill, gid, cmd, data, resp, lst))

        threading.Thread(target=work, daemon=True).start()

    def _after_write(self, zero_fill, gid, cmd, data, resp, lst):
        self._writing = False
        ok = lst and "%GENE" in lst
        if ok:
            self.load_from_text(lst)
        if ok:
            prefix = "已清零" if zero_fill else "已执行"
            detail = f"{cmd}\n{data}" if data else cmd
            self._edit_status.configure(text=f"{prefix}: {detail}", fg="#27ae60")
        else:
            self._edit_status.configure(text=f"写入可能失败 (设备回显: {resp.strip()[:60]})",
                                        fg="#e74c3c")

    # ---------- 数据加载 ----------

    def load_from_text(self, text: str):
        data = self._parse_genealogy(text)
        if not data:
            return

        for item in self._tree.get_children():
            self._tree.delete(item)

        for key in GENEALOGY_IDS:
            label = GENEALOGY_LABELS.get(key, key)
            value = data.get(key, "--")
            is_dim = value in ("- -", "-", "--") or set(value.split()) == {"-"}
            tags = ("dim",) if is_dim else ()
            self._tree.insert("", tk.END, text=label, values=(value,), tags=tags)

    @staticmethod
    def _parse_genealogy(text: str) -> dict:
        import re
        result = {}
        for line in text.split("\n"):
            m = re.match(r'%GENE\s+(\w+)\s+([\w\s]+?)\s{2,}(.+)', line)
            if m:
                result[m.group(1)] = m.group(3).strip()
        return result

    def clear(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for key in GENEALOGY_IDS:
            label = GENEALOGY_LABELS.get(key, key)
            self._tree.insert("", tk.END, text=label, values=("--",))
