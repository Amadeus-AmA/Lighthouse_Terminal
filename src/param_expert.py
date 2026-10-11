"""Parameter expert panel — full firmware parameter table with type-aware editing.

Metadata comes from `param info` sweeps (src/param_meta.py, refreshable from device);
values come from `param list`. Double-click a row to edit with type validation.
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from i18n import tr_text, trf
from param_meta import PARAM_META

# params the firmware refuses to set (verified on hardware)
KNOWN_READONLY = tuple(e["name"] for e in PARAM_META if e.get("readonly"))

INT_RANGES = {
    "uint8": (0, 255), "uint16": (0, 65535),
    "uint32": (0, 2**32 - 1), "uint64": (0, 2**64 - 1),
    "int8": (-128, 127), "int32": (-2**31, 2**31 - 1),
}


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    d = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(d) if os.path.basename(d) == "src" else d


def _baseline_path(serial_id: str):
    # 每台基站(按序列号)一份固化基线, 互不干扰
    return os.path.join(_app_dir(), "baselines", f"{serial_id}.json")


class ParamExpertPanel(tk.Frame):
    def __init__(self, parent, serial_manager, device_id_provider=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._serial = serial_manager
        self._device_id_provider = device_id_provider
        self._sweeping = False
        self._meta = self._load_meta()
        self._values = {}
        self._unsaved = set()
        self._baseline = None
        self._baseline_serial = None

        bar = tk.Frame(self)
        bar.pack(fill=tk.X, padx=4, pady=(4, 2))

        tk.Label(bar, text="搜索:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        ent = tk.Entry(bar, textvariable=self._search_var, width=18)
        ent.pack(side=tk.LEFT, padx=(4, 10))
        ent.bind("<KeyRelease>", lambda e: self._render())

        tk.Label(bar, text="类型:").pack(side=tk.LEFT)
        self._type_var = tk.StringVar(value="")
        types = sorted({e["type"] for e in self._meta.values()})
        self._type_combo = ttk.Combobox(bar, textvariable=self._type_var, state="readonly",
                                        width=12, values=[""] + types)
        self._type_combo.pack(side=tk.LEFT, padx=(4, 10))
        self._type_combo.bind("<<ComboboxSelected>>", lambda e: self._render())

        self._refresh_btn = ttk.Button(bar, text="刷新值", command=self.refresh_values)
        self._refresh_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._collect_btn = ttk.Button(bar, text="采集元数据", command=self._collect_meta)
        self._collect_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._save_btn = ttk.Button(bar, text="保存到闪存",
                                    command=lambda: self._send("param save"))
        self._save_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._baseline_btn = ttk.Button(bar, text="重设基线", command=self._recapture_baseline)
        self._baseline_btn.pack(side=tk.LEFT)

        self._status = tk.Label(self, text="", fg="#7f8c8d", anchor="w")
        self._status.pack(fill=tk.X, padx=6)

        cols = ("type", "value", "baseline", "unsaved", "desc")
        self._tree = ttk.Treeview(self, columns=cols, show="tree headings")
        self._tree.heading("#0", text="参数名")
        self._tree.heading("type", text="类型")
        self._tree.heading("value", text="当前值")
        self._tree.heading("baseline", text="基线")
        self._tree.heading("unsaved", text="未保存")
        self._tree.heading("desc", text="描述")
        self._tree.column("#0", width=230)
        self._tree.column("type", width=90, anchor="w")
        self._tree.column("value", width=130, anchor="w")
        self._tree.column("baseline", width=130, anchor="w")
        self._tree.column("unsaved", width=60, anchor="center")
        self._tree.column("desc", width=190, anchor="w")

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)

        self._tree.tag_configure("unsaved", foreground="#e67e22")
        self._tree.tag_configure("readonly", foreground="#95a5a6")
        self._tree.tag_configure("diff", foreground="#1a5fb4")
        self._tree.bind("<Double-1>", self._on_edit)

        self._tree.pack(fill=tk.BOTH, expand=True, padx=(4, 0))
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_btn.invoke() if self._serial.is_connected() else self._render()

    # ---------- 元数据 ----------

    def _load_meta(self):
        override = os.path.join(_app_dir(), "param_meta_override.json")
        entries = PARAM_META
        try:
            entries = json.loads(open(override, encoding="utf-8").read())
        except (OSError, ValueError):
            pass
        return {e["name"]: e for e in entries}

    def _collect_meta(self):
        if self._sweeping:
            return
        if not self._serial.is_connected():
            messagebox.showwarning(tr_text("提示"), tr_text("请先连接设备"))
            return
        self._sweeping = True
        self._collect_btn.configure(state="disabled")
        names = sorted(self._meta.keys())
        total = len(names)

        def work():
            collected = []
            for i, name in enumerate(names):
                resp = self._serial.send_command(f"param info {name}",
                                                 wait_response=True, timeout=2.0)
                entry = {"name": name}
                for line in resp.splitlines():
                    m = line.strip()
                    for field in ("type", "offset", "default", "description"):
                        if m.startswith(field + ":"):
                            entry[field] = m.split(":", 1)[1].strip()
                    if m.startswith("unsaved:"):
                        entry["unsaved"] = m.split(":", 1)[1].strip()
                collected.append(entry)
                if i % 5 == 0 or i == total - 1:
                    self.after(0, lambda i=i, total=total: self._status.configure(
                        text=trf("expert.collecting", i=i, total=total)))
            self.after(0, lambda: self._meta_done(collected))

        threading.Thread(target=work, daemon=True).start()

    def _meta_done(self, collected):
        self._sweeping = False
        self._collect_btn.configure(state="normal")
        self._meta = {e["name"]: e for e in collected}
        try:
            path = os.path.join(_app_dir(), "param_meta_override.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(collected, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
        self._status.configure(text=trf("expert.collected_done", count=len(collected)),
                               fg="#27ae60")
        self._render()

    # ---------- 数值 ----------

    def refresh_values(self):
        if not self._serial.is_connected():
            self._render()
            return

        def work():
            resp = self._serial.send_command("param list", wait_response=True, timeout=3.0)
            self.after(0, lambda: self._values_done(resp))

        threading.Thread(target=work, daemon=True).start()

    def _values_done(self, resp):
        if not resp:
            self._status.configure(text=tr_text("未连接到设备"), fg="#e74c3c")
            return
        from data_parser import parse_param_list
        self._values = parse_param_list(resp)
        self._ensure_baseline(self._values)
        self._status.configure(text=trf("expert.values_loaded", count=len(self._values)),
                               fg="#7f8c8d")
        self._render()

    # ---------- 基线 (按设备序列号固化, 不随后续修改/换机而变) ----------

    def _baseline_file(self):
        get_id = self._device_id_provider
        serial_id = get_id() if get_id else ""
        if not serial_id:
            return None
        return _baseline_path(serial_id)

    def _ensure_baseline(self, values):
        """首次从某台基站采集参数时固化基线; 之后不再改动, 除非显式重设。"""
        path = self._baseline_file()
        if not path:
            self._baseline = None
            self._baseline_serial = None
            return
        serial_id = os.path.splitext(os.path.basename(path))[0]
        if self._baseline_serial == serial_id and self._baseline is not None:
            return  # 已有本会话基线
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            self._baseline = data.get("values", {})
            self._baseline_serial = serial_id
            return
        except (OSError, ValueError):
            pass
        # 首次采集: 以当前值固化
        self._baseline = dict(values)
        self._baseline_serial = serial_id
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"serial": serial_id,
                           "captured": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "values": self._baseline},
                          f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def _recapture_baseline(self):
        if not self._values:
            messagebox.showwarning(tr_text("提示"), tr_text("请先刷新参数值"))
            return
        path = self._baseline_file()
        if not path:
            messagebox.showwarning(tr_text("提示"), tr_text("未识别到设备序列号"))
            return
        serial_id = os.path.splitext(os.path.basename(path))[0]
        if not messagebox.askyesno(
                tr_text("重设基线"),
                trf("expert.recapture_body", sn=serial_id, count=len(self._values)),
                icon="warning"):
            return
        self._baseline = dict(self._values)
        self._baseline_serial = serial_id
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"serial": serial_id,
                           "captured": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "values": self._baseline},
                          f, ensure_ascii=False, indent=1)
        except OSError:
            pass
        self._status.configure(text=trf("expert.baseline_reset", sn=serial_id), fg="#27ae60")
        self._render()

    # ---------- 渲染 ----------

    def _render(self):
        query = self._search_var.get().strip().lower()
        type_filter = self._type_var.get()
        for item in self._tree.get_children():
            self._tree.delete(item)
        for name in sorted(self._meta):
            meta = self._meta[name]
            if query and query not in name.lower() and query not in meta.get("description", "").lower():
                continue
            if type_filter and meta.get("type") != type_filter:
                continue
            value = str(self._values.get(name, "--"))
            baseline = str(self._baseline.get(name, "--")) if self._baseline else "--"
            unsaved = tr_text("是") if name in self._unsaved else ""
            tags = []
            if name in self._unsaved:
                tags.append("unsaved")
            if name.startswith("journal."):
                tags.append("readonly")
            if self._baseline and value != baseline and value != "--":
                tags.append("diff")
            self._tree.insert("", tk.END, iid=name, text=name,
                              values=(meta.get("type", ""), value, baseline,
                                      unsaved, meta.get("description", "")),
                              tags=tuple(tags))

    def set_language(self, language=None):
        self._tree.heading("#0", text=tr_text("参数名"))
        self._tree.heading("type", text=tr_text("类型"))
        self._tree.heading("value", text=tr_text("当前值"))
        self._tree.heading("baseline", text=tr_text("基线"))
        self._tree.heading("unsaved", text=tr_text("未保存"))
        self._tree.heading("desc", text=tr_text("描述"))
        self._refresh_btn.configure(text=tr_text("刷新值"))
        self._collect_btn.configure(text=tr_text("采集元数据"))
        self._save_btn.configure(text=tr_text("保存到闪存"))
        self._baseline_btn.configure(text=tr_text("重设基线"))
        self._render()

    # ---------- 编辑 ----------

    def _on_edit(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        name = sel[0]
        meta = self._meta.get(name)
        if not meta:
            return
        if name.startswith("journal."):
            messagebox.showinfo(
                tr_text("提示"),
                tr_text("只读参数 (固件拒绝 param set)") + f"\n{name}\n\n"
                + tr_text("该参数由固件保护, 无法通过串口修改。"))
            return
        current = str(self._values.get(name, meta.get("default", "")))
        self._open_editor(name, meta, current)

    def _open_editor(self, name, meta, current):
        ptype = meta.get("type", "")
        default = str(meta.get("default", ""))
        desc = meta.get("description", "")

        win = tk.Toplevel(self)
        win.title(tr_text("编辑参数") + f" - {name}")
        win.geometry("460x300")
        win.transient(self.winfo_toplevel())

        tk.Label(win, text=f"{name}  [{ptype}]", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        tk.Label(win, text=f"{tr_text('当前值')}: {current}   {tr_text('默认值')}: {default}",
                 fg="#7f8c8d", anchor="w").pack(fill=tk.X, padx=10)
        if desc:
            tk.Label(win, text=tr_text("描述") + f": {desc}", fg="#7f8c8d",
                     anchor="w").pack(fill=tk.X, padx=10)

        tk.Label(win, text=tr_text("新值") + ":").pack(anchor="w", padx=10, pady=(10, 0))
        var = tk.StringVar(value=current)
        if ptype == "bool":
            entry = ttk.Combobox(win, textvariable=var, values=["true", "false"], state="readonly")
        else:
            entry = tk.Entry(win, textvariable=var, font=("Consolas", 10))
        entry.pack(fill=tk.X, padx=10)
        entry.focus_set()

        save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text=tr_text("同时保存到闪存 (param save)"),
                        variable=save_var).pack(anchor="w", padx=10, pady=(8, 0))

        status = tk.Label(win, text="", fg="#e74c3c", anchor="w")
        status.pack(fill=tk.X, padx=10)

        def validate():
            v = var.get().strip()
            if ptype == "bool":
                if v not in ("true", "false"):
                    status.configure(text=tr_text("值必须是 true/false")); return None
                return v
            if ptype in INT_RANGES:
                try:
                    iv = int(v, 0)
                except ValueError:
                    status.configure(text=tr_text("值必须是数字")); return None
                lo, hi = INT_RANGES[ptype]
                if not lo <= iv <= hi:
                    status.configure(text=f"{tr_text('超出类型范围')} [{lo}, {hi}]"); return None
                return str(iv)
            if ptype == "float":
                try:
                    return repr(float(v))
                except ValueError:
                    status.configure(text=tr_text("值必须是数字")); return None
            if not v:
                status.configure(text=tr_text("值必须是数字")); return None
            return v

        def commit():
            value = validate()
            if value is None:
                return
            changed = value != current
            if not changed and not save_var.get():
                win.destroy(); return
            if not messagebox.askyesno(
                    tr_text("确认写入"),
                    f"param set {name} {value}\n\n{tr_text('该操作会修改设备参数, 确认执行?')}",
                    icon="warning"):
                return
            cmds = [f"param set {name} {value}"]
            if save_var.get():
                cmds.append("param save")
            btn.configure(state="disabled")

            def work():
                outputs = []
                for c in cmds:
                    outputs.append(self._serial.send_command(c, wait_response=True, timeout=2.0))
                info = self._serial.send_command(f"param info {name}",
                                                 wait_response=True, timeout=2.0)
                self.after(0, lambda: self._edit_done(win, name, value, save_var.get(),
                                                      outputs, info, status, btn))

            threading.Thread(target=work, daemon=True).start()

        btn = ttk.Button(win, text=tr_text("写入"), command=commit)
        btn.pack(pady=10)
        win.bind("<Return>", lambda e: commit())

    def _edit_done(self, win, name, value, do_save, outputs, info, status, btn):
        btn.configure(state="normal")
        blob = "\n".join(outputs)
        low = blob.lower()
        if any(w in low for w in ("error", "invalid", "usage", "read-only")):
            status.configure(text=trf("genealogy.failed", response=blob.strip()[:80]))
            return
        # 用 param info 的 unsaved/value 刷新本地视图
        for line in info.splitlines():
            line = line.strip()
            if line.startswith("value:"):
                self._values[name] = line.split(":", 1)[1].strip()
            if line.startswith("unsaved:") and line.split(":", 1)[1].strip().lower() == "true":
                self._unsaved.add(name)
        self._render()
        status.configure(text=tr_text("完成") + f": param set {name} {value}", fg="#27ae60")
        if do_save:
            self._unsaved.discard(name)
            self._render()
        win.after(600, win.destroy)

    def _send(self, cmd):
        if not self._serial.is_connected():
            messagebox.showwarning(tr_text("提示"), tr_text("请先连接设备"))
            return
        if not messagebox.askyesno(tr_text("确认写入"), cmd, icon="warning"):
            return

        def work():
            self._serial.send_command(cmd, wait_response=True, timeout=3.0)

        threading.Thread(target=work, daemon=True).start()

    def clear(self):
        self._values = {}
        self._unsaved = set()
        self._render()
