import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import threading

from serial_manager import SerialManager
from terminal_panel import TerminalPanel
from status_panel import StatusPanel
from param_tree_panel import ParamTreePanel
from fcal_viewer import FcalViewer
from calibration_viewer import CalibrationViewer
from hardware_panel import HardwarePanel
from dump_viewer import DumpViewer
from genealogy_panel import GenealogyPanel
from backup_compare import backup_params_to_json, compare_params, backup_fcal_to_json
from data_parser import (
    parse_id_output, parse_laser_status, parse_rotor_status,
    parse_param_uptime, parse_sys_config, parse_journal,
    parse_isl58303, parse_fpga, parse_genealogy_list
)


class LighthouseConsoleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Lighthouse 基站控制台")
        self.root.geometry("1200x700")

        self._serial = SerialManager()
        self._serial.set_data_callback(self._on_data_received)
        self._is_base_station = False
        self._device_info = {}

        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_quick_buttons()

        self._calibration_viewer = CalibrationViewer(self._serial)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self._on_close)
        menubar.add_cascade(label="文件", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Mode 校准数据图表", command=self._fetch_mode_data)
        tools_menu.add_command(label="参数列表", command=self._fetch_param_list)
        tools_menu.add_command(label="命令参考", command=self._show_command_reference)
        menubar.add_cascade(label="工具", menu=tools_menu)

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=4, pady=4)

        ttk.Label(toolbar, text="串口:").pack(side=tk.LEFT, padx=(0, 4))

        self._port_var = tk.StringVar()
        self._port_combo = ttk.Combobox(toolbar, textvariable=self._port_var, width=20, state="readonly")
        self._port_combo.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Label(toolbar, text="波特率:").pack(side=tk.LEFT, padx=(0, 4))

        self._baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(
            toolbar, textvariable=self._baud_var, width=10,
            values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
        )
        baud_combo.pack(side=tk.LEFT, padx=(0, 4))

        self._scan_btn = ttk.Button(toolbar, text="扫描", command=self._scan_ports)
        self._scan_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._connect_btn = ttk.Button(toolbar, text="连接", command=self._toggle_connect)
        self._connect_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._status_label = ttk.Label(toolbar, text="未连接", foreground="red")
        self._status_label.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(toolbar, text="Mode:").pack(side=tk.LEFT, padx=(12, 2))
        self._mode_var = tk.StringVar(value="--")
        self._mode_combo = ttk.Combobox(
            toolbar, textvariable=self._mode_var, width=4,
            values=[str(i) for i in range(17)], state="readonly"
        )
        self._mode_combo.pack(side=tk.LEFT, padx=(0, 2))
        self._mode_apply_btn = ttk.Button(toolbar, text="应用", command=self._apply_mode)
        self._mode_apply_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._scan_ports()

    def _build_main_area(self):
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        left_frame = tk.Frame(paned)
        paned.add(left_frame, width=350)

        self._status_panel = StatusPanel(left_frame)
        self._status_panel.pack(fill=tk.X, padx=0, pady=0)

        self._hardware_panel = HardwarePanel(left_frame)
        self._hardware_panel.pack(fill=tk.BOTH, expand=True, padx=0, pady=(4, 0))

        right_frame = tk.Frame(paned)
        paned.add(right_frame, width=850)

        self._notebook = ttk.Notebook(right_frame)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        terminal_tab = tk.Frame(self._notebook)
        self._terminal = TerminalPanel(terminal_tab, on_command_callback=self._on_user_command)
        self._terminal.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(terminal_tab, text="终端")

        param_tab = tk.Frame(self._notebook)
        self._param_tree = ParamTreePanel(param_tab)
        self._param_tree.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(param_tab, text="参数树")

        fcal_tab = tk.Frame(self._notebook)
        self._fcal_viewer = FcalViewer(fcal_tab)
        self._fcal_viewer.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(fcal_tab, text="校准参数")

        genealogy_tab = tk.Frame(self._notebook)
        self._genealogy_panel = GenealogyPanel(genealogy_tab)
        self._genealogy_panel.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(genealogy_tab, text="硬件溯源")

        dump_tab = tk.Frame(self._notebook)
        self._dump_viewer = DumpViewer(self._serial)
        self._notebook.add(dump_tab, text="Dump 曲线")
        ttk.Label(dump_tab, text="点击下方按钮开始采集 20 秒 Dump 数据\n采集期间请勿发送其他命令",
                  font=("", 10)).pack(pady=20)
        ttk.Button(dump_tab, text="开始采集 Dump 数据",
                   command=lambda: self._dump_viewer.collect_and_show(self.root)).pack(pady=10)

    def _build_quick_buttons(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        row1 = tk.Frame(btn_frame)
        row1.pack(fill=tk.X)

        commands = [
            ("id", "设备信息"),
            ("uptime", "运行时间"),
            ("freq", "转子频率"),
            ("param list", "参数列表"),
            ("fpga", "FPGA 状态"),
            ("isl58303", "激光驱动"),
            ("perf", "性能测试"),
            ("pwmcal", "粗调电机PWM校准"),         
            ("pwmopt", "粗调 PWM 优化搜索"),
            ("pwmgain", "粗/细 PWM 增益测量"),
        ]
        for cmd, label in commands:
            btn = ttk.Button(row1, text=label,
                             command=lambda c=cmd: self._send_quick_command(c))
            btn.pack(side=tk.LEFT, padx=2)

        row2 = tk.Frame(btn_frame)
        row2.pack(fill=tk.X, pady=(2, 0))

        ttk.Button(row2, text="刷新状态", command=self._poll_status).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="命令列表", command=self._show_command_reference).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="备份参数", command=self._backup_params).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="备份FCAL", command=self._backup_fcal).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="对比参数", command=self._compare_params).pack(side=tk.LEFT, padx=2)

    def _scan_ports(self):
        ports = SerialManager.list_ports()
        self._port_combo["values"] = [f"{p['device']} - {p['description']}" for p in ports]
        if ports:
            self._port_combo.current(0)

    def _toggle_connect(self):
        if self._serial.is_connected():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port_str = self._port_var.get()
        if not port_str:
            messagebox.showwarning("提示", "请先选择串口")
            return
        port_name = port_str.split(" - ")[0]
        baudrate = int(self._baud_var.get())

        self._terminal.append_system(f"正在连接 {port_name} @ {baudrate}...")
        if self._serial.connect(port_name, baudrate):
            self._terminal.append_system("连接成功")
            self._status_label.configure(text=f"已连接 {port_name}", foreground="green")
            self._connect_btn.configure(text="断开")
            self._port_combo.configure(state="disabled")
            self.root.after(500, self._auto_identify)
        else:
            self._terminal.append_error(f"连接失败: {port_name}")
            messagebox.showerror("连接失败", f"无法打开串口 {port_name}")

    def _disconnect(self):
        self._serial.disconnect()
        self._is_base_station = False
        self._device_info = {}
        self._terminal.append_system("已断开连接")
        self._status_label.configure(text="未连接", foreground="red")
        self._connect_btn.configure(text="连接")
        self._port_combo.configure(state="readonly")
        self._status_panel.clear_all()
        self._param_tree.clear()
        self._fcal_viewer.clear()
        self._hardware_panel.clear_all()
        self._genealogy_panel.clear()
        self._mode_var.set("--")

    def _auto_identify(self):
        self._terminal.append_system("正在识别设备...")

        def identify():
            resp = self._serial.send_command("id", wait_response=True, timeout=3.0)
            id_info = parse_id_output(resp)
            if id_info.get("device_name"):
                self._is_base_station = True
                self._device_info.update(id_info)
                self.root.after(0, lambda: self._status_panel.update_all(id_info))
                self.root.after(0, lambda: self._terminal.append_system("已确认: Lighthouse 基站"))
                self.root.after(300, self._poll_status)
            else:
                self.root.after(0, lambda: self._terminal.append_system("未识别到基站设备，但仍可手动发送命令"))

        threading.Thread(target=identify, daemon=True).start()

    def _poll_status(self):
        if not self._serial.is_connected() or not self._is_base_station:
            return

        def poll():
            resp = self._serial.send_command("param list", wait_response=True, timeout=3.0)
            uptime_info = parse_param_uptime(resp)
            laser_info = parse_laser_status(resp)
            rotor_info = parse_rotor_status(resp)
            config_info = parse_sys_config(resp)
            journal_info = parse_journal(resp)
            self.root.after(0, lambda: self._status_panel.update_all(uptime_info))
            self.root.after(0, lambda: self._status_panel.update_all(laser_info))
            self.root.after(0, lambda: self._status_panel.update_all(rotor_info))
            self.root.after(0, lambda: self._status_panel.update_all(config_info))
            self.root.after(0, lambda: self._status_panel.update_all(journal_info))
            self.root.after(0, lambda: self._param_tree.load_from_text(resp))
            self.root.after(0, lambda: self._fcal_viewer.load_from_text(resp))
            if config_info.get("sys_config") is not None:
                self.root.after(0, lambda: self._mode_var.set(str(config_info["sys_config"])))

            isl_resp = self._serial.send_command("isl58303", wait_response=True, timeout=2.0)
            if isl_resp:
                isl_info = parse_isl58303(isl_resp)
                self.root.after(0, lambda: self._hardware_panel.update_from_isl58303(isl_info))

            fpga_resp = self._serial.send_command("fpga", wait_response=True, timeout=2.0)
            if fpga_resp:
                fpga_info = parse_fpga(fpga_resp)
                self.root.after(0, lambda: self._hardware_panel.update_from_fpga(fpga_info))

            genealogy_resp = self._serial.send_command("genealogy list", wait_response=True, timeout=3.0)
            if genealogy_resp:
                self.root.after(0, lambda: self._genealogy_panel.load_from_text(genealogy_resp))

        threading.Thread(target=poll, daemon=True).start()

    def _on_data_received(self, text: str):
        self.root.after(0, self._terminal.append_received, text)

    def _on_user_command(self, cmd: str):
        if not self._serial.is_connected():
            self._terminal.append_error("未连接到设备")
            return

        def execute():
            self._serial.send_command(cmd, wait_response=True, timeout=5.0)

        threading.Thread(target=execute, daemon=True).start()

    def _send_quick_command(self, cmd: str):
        self._terminal.append_sent(cmd)
        self._on_user_command(cmd)

    def _apply_mode(self):
        mode_val = self._mode_var.get()
        if mode_val == "--":
            return
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        ok = messagebox.askyesno(
            "确认切换 Mode",
            f"即将切换到 Mode {mode_val}，这会修改 timebase.period / rotor.pwm / rotor.pll.offset。"
            f"\n确认切换？",
            icon="warning"
        )
        if ok:
            self._terminal.append_system(f"正在切换 Mode {mode_val}...")
            self._send_quick_command(f"mode {mode_val}")

    def _backup_params(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        self._terminal.append_system("正在备份参数...")

        def do_backup():
            backup_params_to_json(self._serial, self.root)
            self.root.after(0, lambda: self._terminal.append_system("参数备份完成"))

        threading.Thread(target=do_backup, daemon=True).start()

    def _compare_params(self):
        compare_params(self.root)

    def _backup_fcal(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        self._terminal.append_system("正在备份 FCAL 校准参数...")

        serial_number = self._device_info.get("serial_number", "")

        def do_backup():
            backup_fcal_to_json(self._serial, self.root, serial_number)
            self.root.after(0, lambda: self._terminal.append_system("FCAL 备份完成"))

        threading.Thread(target=do_backup, daemon=True).start()

    def _fetch_mode_data(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        self._terminal.append_system("正在采集 Mode 0-16 数据...")

        def fetch():
            self._calibration_viewer.show_mode_chart()
            self.root.after(0, lambda: self._terminal.append_system("Mode 数据采集完成"))

        threading.Thread(target=fetch, daemon=True).start()

    def _fetch_param_list(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        self._send_quick_command("param list")

    def _show_command_reference(self):
        ref = Toplevel(self.root)
        ref.title("Lighthouse 命令参考")
        ref.geometry("750x600")

        text = tk.Text(ref, wrap=tk.WORD, font=("Consolas", 10),
                       bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4")
        text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        scroll = ttk.Scrollbar(text, orient=tk.VERTICAL, command=text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scroll.set)

        text.tag_config("title", foreground="#569cd6", font=("Consolas", 12, "bold"))
        text.tag_config("cmd", foreground="#4ec9b0", font=("Consolas", 10, "bold"))
        text.tag_config("desc", foreground="#6a9955")

        content = """=== Lighthouse 基站所有命令参考 ===

[设备信息与系统控制]
id             查看设备标识（名称、序列号、OOTX型号、固件版本、FPGA版本）
reboot         重启基站
shutdown       关机（同时断开控制台）
isp            进入 ISP 引导模式（固件升级用）

[状态与统计]
uptime         显示系统本次运行时间
freq           显示转子当前旋转频率（Hz）
stats          切换统计信息自动打印
clear          清空统计计数器
dump           切换转子数据实时输出
perf           数学性能基准测试（整数/浮点运算速度）

[参数系统]
param list [pattern]    列出所有参数（支持 pattern 过滤）
param info <name>       查看参数详细信息
param get <name>        获取单个参数值
param set <name> <val>  设置参数值
param default <name>    恢复参数为默认值
param default-all       恢复所有参数为默认值
param load [partition]  从闪存加载参数
param save [partition]  保存参数到闪存

[配置模式]
mode <0-16>     设置运行配置模式
                切换后 timebase.period / rotor.pwm / rotor.pll.offset 会变化

[转子/电机]
motor           手动电机驱动控制
auto            切换自动 PWM 调谐
autodebug       切换自动 PWM 调谐调试输出
pll             切换 PLL 控制
plldebug        切换 PLL 调试输出
pwmscan         粗调 PWM 速度扫描
pwmcal          粗调 PWM 校准
pwmopt          粗调 PWM 优化搜索
pwmgain         粗/细 PWM 增益测量

[激光]
isl58303        访问激光驱动器 ISL58303 所有寄存器

[FPGA]
fpga            访问 FPGA 寄存器（载波、OOTX、激光、电机、时基状态）

[加速度计]
lis2dh          访问 LIS2DH 加速度计寄存器

[EEPROM/RAM]
ram             RAM 检查
eeprom          EEPROM 检查和修改

[日志/履历]
genealogy <1|2> 查看系统履历信息（上电次数、运行圈数、故障数等）
log             调整日志设置（级别、来源）

[LED]
led             控制指示灯颜色 (RGBW, 0-255)

[无线/DTM]
dtm             十进制 DTM 测试命令（用于射频认证）
dtm_pwr         调整 DTM 发射功率
serial_dfu      请求无线电 DFU 模式
nonce           生成新的配对码
radio           无线子命令树

[工厂/测试]
factory         工厂测试与校准命令
crash           触发系统崩溃（调试用）"""

        text.insert(tk.END, content)
        text.configure(state="disabled")

    def _on_close(self):
        if self._serial.is_connected():
            self._serial.disconnect()
        self.root.destroy()
