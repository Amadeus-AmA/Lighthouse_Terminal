import tkinter as tk
from tkinter import ttk

FCAL_MAP = [
    ("tilt", "倾角 (弧度)"),
    ("phase", "初始相位偏移 (弧度)"),
    ("curve", "扫描线弯曲校正系数"),
    ("gibphase", "Gib 效应相位校正"),
    ("gibmag", "Gib 效应幅度校正"),
    ("ogeephase", "Ogee 效应相位校正"),
    ("ogeemag", "Ogee 效应幅度校正"),
]


class FcalViewer(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        header = ttk.Label(self, text="出厂校准参数 (fcal.*) — 每个基站独一无二，修改需谨慎",
                           font=("", 9, "bold"), foreground="#e5c07b")
        header.pack(anchor="w", padx=4, pady=(4, 2))

        self._tree = ttk.Treeview(self, columns=("axis0", "axis1"), show="tree headings")
        self._tree.heading("#0", text="校准项")
        self._tree.heading("axis0", text="Axis 0")
        self._tree.heading("axis1", text="Axis 1")

        self._tree.column("#0", width=220)
        self._tree.column("axis0", width=140, anchor="e")
        self._tree.column("axis1", width=140, anchor="e")

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        for key, label in FCAL_MAP:
            self._tree.insert("", tk.END, text=label, values=("--", "--"))

    def load_from_text(self, text: str):
        from data_parser import parse_fcal

        data = parse_fcal(text)
        for item in self._tree.get_children():
            name = self._tree.item(item, "text")
            key_part = next((k for k, v in FCAL_MAP if v == name), None)
            if key_part is None:
                continue
            v0 = data.get(f"fcal_0_{key_part}", "--")
            v1 = data.get(f"fcal_1_{key_part}", "--")
            self._tree.item(item, values=(str(v0), str(v1)))

    def clear(self):
        for item in self._tree.get_children():
            self._tree.item(item, values=("--", "--"))
