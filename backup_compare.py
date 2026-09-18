import json
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def compare_params(parent_tk):
    file_a = filedialog.askopenfilename(
        parent=parent_tk,
        title="选择第一份参数备份 (文件 A)",
        filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
    )
    if not file_a:
        return

    file_b = filedialog.askopenfilename(
        parent=parent_tk,
        title="选择第二份参数备份 (文件 B)",
        filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
    )
    if not file_b:
        return

    try:
        with open(file_a, "r", encoding="utf-8") as f:
            params_a = json.load(f)
        with open(file_b, "r", encoding="utf-8") as f:
            params_b = json.load(f)
    except Exception as e:
        messagebox.showerror("加载失败", f"无法读取 JSON 文件:\n{e}")
        return

    all_keys = sorted(set(params_a.keys()) | set(params_b.keys()))

    import os
    name_a = os.path.basename(file_a)
    name_b = os.path.basename(file_b)

    window = tk.Toplevel(parent_tk)
    window.title("参数备份对比")
    window.geometry("900x600")

    header = ttk.Label(
        window,
        text=f"对比: {name_a}  vs  {name_b}",
        font=("", 10, "bold")
    )
    header.pack(padx=8, pady=(8, 4))

    tree = ttk.Treeview(window, columns=("val_a", "val_b"), show="tree headings")
    tree.heading("#0", text="参数名称")
    tree.heading("val_a", text=f"文件 A: {name_a}")
    tree.heading("val_b", text=f"文件 B: {name_b}")

    tree.column("#0", width=260)
    tree.column("val_a", width=280, anchor="w")
    tree.column("val_b", width=280, anchor="w")

    scroll_y = ttk.Scrollbar(window, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll_y.set)

    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=4)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    tree.tag_configure("diff", foreground="#e74c3c")
    tree.tag_configure("same", foreground="#27ae60")

    diff_count = 0
    for key in all_keys:
        val_a = params_a.get(key, "")
        val_b = params_b.get(key, "")
        if val_a != val_b:
            diff_count += 1
            tree.insert("", tk.END, text=key, values=(str(val_a), str(val_b)), tags=("diff",))
        else:
            tree.insert("", tk.END, text=key, values=(str(val_a), str(val_b)), tags=("same",))

    summary = ttk.Label(
        window,
        text=f"共 {len(all_keys)} 个参数，其中 {diff_count} 个差异",
        font=("", 9)
    )
    summary.pack(padx=8, pady=(2, 8))


def _save_json(obj, filename: str) -> str:
    _ensure_backup_dir()
    file_path = os.path.join(BACKUP_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return file_path


def backup_id_to_json(serial_manager, serial_number=""):
    resp = serial_manager.send_command("id", wait_response=True, timeout=3.0)
    if not resp:
        return None
    from data_parser import parse_id_output
    info = parse_id_output(resp)
    info["raw"] = resp
    if serial_number:
        filename = f"{serial_number}_id.json"
    else:
        filename = f"id_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return _save_json(info, filename)


def backup_all_to_json(serial_manager, serial_number=""):
    """一键备份: 参数 + FCAL + ID, 自动命名存到 backup/, 返回路径列表"""
    from data_parser import parse_fcal, parse_param_list

    sn = serial_number or "unknown"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []

    resp = serial_manager.send_command("param list", wait_response=True, timeout=3.0)
    if not resp:
        return []
    paths.append(_save_json(parse_param_list(resp), f"{sn}_params_{ts}.json"))

    fcal = parse_fcal(resp)
    if fcal:
        paths.append(_save_json(fcal, f"{sn}_fcal.json"))

    id_path = backup_id_to_json(serial_manager, serial_number)
    if id_path:
        paths.append(id_path)
    return paths


def _format_param_value(val):
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def _apply_params(serial_manager, params, keys, done_cb, summary_win):
    ok, fail = 0, []
    for key in keys:
        cmd = f"param set {key} {_format_param_value(params[key])}"
        resp = serial_manager.send_command(cmd, wait_response=True, timeout=2.0)
        low = resp.lower()
        if resp and not any(w in low for w in ("error", "invalid", "unknown", "usage")):
            ok += 1
        else:
            fail.append(key)
    save_resp = serial_manager.send_command("param save", wait_response=True, timeout=3.0)
    summary_win.after(0, lambda: done_cb(ok, fail, save_resp))


def restore_params_from_json(serial_manager, parent_tk):
    file_path = filedialog.askopenfilename(
        parent=parent_tk,
        title="选择要恢复的参数备份",
        filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
    )
    if not file_path:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            params = json.load(f)
    except Exception as e:
        messagebox.showerror("加载失败", f"无法读取 JSON 文件:\n{e}")
        return
    if not isinstance(params, dict):
        messagebox.showerror("加载失败", "备份文件格式不正确")
        return
    skip = {"param", "list", "raw"}
    keys = [k for k in params if k not in skip and not k.startswith("_")]
    if not keys:
        messagebox.showerror("加载失败", "备份文件中没有可恢复的参数")
        return
    if not messagebox.askyesno(
            "确认恢复参数",
            f"将向设备逐条写入 {len(keys)} 个参数, 最后执行 param save 保存到闪存。\n"
            f"来源: {os.path.basename(file_path)}\n\n参数写错可能改变设备行为, 确认恢复?",
            icon="warning"):
        return

    win = tk.Toplevel(parent_tk)
    win.title("正在恢复参数")
    win.geometry("320x90")
    tk.Label(win, text=f"正在写入参数 (0/{len(keys)})...").pack(pady=10)
    win.grab_set()

    def done(ok, fail, save_resp):
        win.destroy()
        if fail:
            messagebox.showwarning(
                "恢复完成(部分失败)",
                f"成功 {ok} 项, 失败 {len(fail)} 项:\n"
                + "\n".join(fail[:10]) + ("\n..." if len(fail) > 10 else "")
                + f"\n\nparam save: {save_resp.strip().splitlines()[-1] if save_resp.strip() else '(无响应)'}")
        else:
            messagebox.showinfo("恢复完成", f"已恢复 {ok} 个参数并保存到闪存")

    def work():
        _apply_params(serial_manager, params, keys, done, win)

    threading.Thread(target=work, daemon=True).start()


def restore_fcal_to_device(serial_manager, parent_tk):
    file_path = filedialog.askopenfilename(
        parent=parent_tk,
        title="选择 FCAL 校准备份",
        initialdir=BACKUP_DIR,
        filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
    )
    if not file_path:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        messagebox.showerror("加载失败", f"无法读取 JSON 文件:\n{e}")
        return
    keys = [k for k in data
            if k.startswith("fcal_") or k.startswith("fcal.")]
    if not keys:
        messagebox.showerror("加载失败", "备份文件中没有 fcal 校准参数")
        return
    if not messagebox.askyesno(
            "确认写入 FCAL 校准",
            f"即将写入 {len(keys)} 项出厂校准参数并保存到闪存:\n{os.path.basename(file_path)}\n\n"
            "FCAL 每台基站独一无二, 错误的校准值会导致定位失效!\n确认写入?",
            icon="warning"):
        return
    if not messagebox.askyesno("二次确认", "再次确认: 确实要覆盖设备出厂校准?", icon="warning"):
        return

    params = {k: data[k] for k in keys}

    def map_key(k):
        # fcal_0_tilt -> fcal.0.tilt
        parts = k.split("_", 2)
        if len(parts) == 3:
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return k

    win = tk.Toplevel(parent_tk)
    win.title("正在写入 FCAL")
    win.geometry("320x90")
    tk.Label(win, text="正在写入校准参数...").pack(pady=10)
    win.grab_set()

    def done(ok, fail, save_resp):
        win.destroy()
        if fail:
            messagebox.showwarning("写入完成(部分失败)",
                                   f"成功 {ok} 项, 失败: {', '.join(fail)}")
        else:
            messagebox.showinfo("写入完成", f"已写入 {ok} 项 FCAL 校准并保存到闪存")

    def work():
        named = {map_key(k): params[k] for k in keys}
        _apply_params(serial_manager, named, list(named.keys()), done, win)

    threading.Thread(target=work, daemon=True).start()
