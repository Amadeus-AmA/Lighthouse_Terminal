import tkinter as tk
from tkinter import ttk

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


class GenealogyPanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        header = ttk.Label(
            self, text="硬件溯源 — 设备各组件序列号与版本信息",
            font=("", 9, "bold"), foreground="#e5c07b"
        )
        header.pack(anchor="w", padx=4, pady=(4, 2))

        self._tree = ttk.Treeview(self, columns=("value",), show="tree headings")
        self._tree.heading("#0", text="溯源项")
        self._tree.heading("value", text="信息")

        self._tree.column("#0", width=200)
        self._tree.column("value", width=520, anchor="w")

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.tag_configure("dim", foreground="#7f8c8d")

        for key in ["model", "top", "main", "upper", "antenna", "laser", "motor", "chassis",
                     "spare1", "spare2", "spare3"]:
            label = GENEALOGY_LABELS.get(key, key)
            self._tree.insert("", tk.END, text=label, values=("--",))

    def load_from_text(self, text: str):
        from data_parser import parse_genealogy_list

        data = parse_genealogy_list(text)
        if not data:
            return

        for item in self._tree.get_children():
            self._tree.delete(item)

        for key in ["model", "top", "main", "upper", "antenna", "laser", "motor", "chassis",
                     "spare1", "spare2", "spare3"]:
            label = GENEALOGY_LABELS.get(key, key)
            if key in data:
                value = data[key]["value"]
            else:
                value = "--"
            is_dim = value in ("- -", "-", "--")
            tags = ("dim",) if is_dim else ()
            self._tree.insert("", tk.END, text=label, values=(value,), tags=tags)

    def clear(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for key in ["model", "top", "main", "upper", "antenna", "laser", "motor", "chassis",
                     "spare1", "spare2", "spare3"]:
            label = GENEALOGY_LABELS.get(key, key)
            self._tree.insert("", tk.END, text=label, values=("--",))
