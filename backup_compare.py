import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_fcal_to_json(serial_manager, parent_tk, serial_number=""):
    resp = serial_manager.send_command("param list", wait_response=True, timeout=3.0)
    if not resp:
        messagebox.showwarning("提示", "未获取到参数数据")
        return

    from data_parser import parse_fcal
    fcal = parse_fcal(resp)
    if not fcal:
        messagebox.showwarning("提示", "未提取到 fcal 校准参数")
        return

    _ensure_backup_dir()

    if serial_number:
        filename = f"{serial_number}_fcal.json"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fcal_{timestamp}.json"
    file_path = os.path.join(BACKUP_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(fcal, f, indent=2, ensure_ascii=False)

    messagebox.showinfo("备份完成", f"FCAL 校准参数已保存到:\n{file_path}")


def backup_params_to_json(serial_manager, parent_tk):
    resp = serial_manager.send_command("param list", wait_response=True, timeout=3.0)
    if not resp:
        messagebox.showwarning("提示", "未获取到参数数据")
        return

    from data_parser import parse_param_list
    params = parse_param_list(resp)

    file_path = filedialog.asksaveasfilename(
        parent=parent_tk,
        title="保存参数备份",
        defaultextension=".json",
        filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
    )
    if not file_path:
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, ensure_ascii=False)

    messagebox.showinfo("备份完成", f"参数已保存到:\n{file_path}")


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
