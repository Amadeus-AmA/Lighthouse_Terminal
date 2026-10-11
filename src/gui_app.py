import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import threading

from serial_manager import SerialManager
from terminal_panel import TerminalPanel
from status_panel import StatusPanel
from param_tree_panel import ParamTreePanel
from param_expert import ParamExpertPanel
from fcal_viewer import FcalViewer
from calibration_viewer import CalibrationViewer
from hardware_panel import HardwarePanel
from dump_viewer import DumpViewer
from genealogy_panel import GenealogyPanel
from laser_panel import LaserPanel
from maintenance_panel import MaintenancePanel
from backup_compare import backup_all_to_json, compare_params
from log_panel import LogPanel
from data_parser import (
    parse_id_output, parse_laser_status, parse_rotor_status,
    parse_param_uptime, parse_sys_config, parse_journal,
    parse_isl58303, parse_fpga, parse_genealogy_list
)
from i18n import Translator, apply_widget_language, set_current_language, tr_text, current_language

COMMAND_REFERENCE_EN = """=== Lighthouse base station command reference ===

[Device info and system control]
id             Show device identity (name, serial, OOTX model, firmware, FPGA)
reboot         Reboot the base station
shutdown       Power off (also closes this console)
isp            Enter ISP boot mode (firmware flashing)
param set sys.standby true/false   Sleep/wake the station (verified on hardware)

[Status and statistics]
uptime         Show current uptime
freq           Show rotor frequency (Hz)
stats          Toggle automatic statistics output
clear          Clear statistics counters
dump           Toggle live rotor data output
perf           Math benchmark (integer/float speed)

[Parameter system]
param list [pattern]    List all parameters (optional pattern filter)
param info <name>       Show parameter details
param get <name>        Get a parameter value
param set <name> <val>  Set a parameter (booleans use true/false)
param default <name>    Restore a parameter to its default
param default-all       Restore all parameters to defaults
param load [partition]  Load parameters from a flash partition
param save [partition]  Save parameters to a flash partition
param part              Show partition status (Par0/1=NORM, Par2=FACT)
param erase <partition> Erase a partition (dangerous)
param raw <r|w> <addr>  Load/save the 235-byte table to/from EEPROM (dangerous)

[Configuration modes]
mode <0-16>     Select the running configuration mode
                Changing it modifies timebase.period / rotor.pwm / rotor.pll.offset

[Rotor/motor]
motor          Manual motor drive control
auto           Toggle automatic PWM tuning
autodebug      Toggle automatic PWM tuning debug output
pll            Toggle PLL control
plldebug       Toggle PLL debug output
pwmscan        Coarse PWM speed scan
pwmcal         Coarse PWM calibration
pwmopt         Coarse PWM optimization search
pwmgain        Coarse/fine PWM gain measurement
step           Rotor step response test (motor health diagnostics)

[Laser]
isl58303         Access all ISL58303 laser driver registers
isl58303 <reg>          Read a register (e.g. STATUS / ENABLE)
isl58303 <reg> <val>    Write a register (dangerous)
param set laser.enable <true|false>   Switch the laser (verified on hardware)
laser.current / laser.pwr / laser.bias        Laser current/power/bias
laser.phase.on / laser.phase.off              Scan on/off phase
laser.interlock / laser.fullspin / laser.apc  Interlock/full spin/APC
sys.emission_enable     Global laser emission enable

[FPGA]
fpga           Access FPGA registers (carrier, OOTX, laser, motor, timebase)

[Accelerometer]
lis2dh         Access LIS2DH accelerometer registers

[EEPROM/RAM]
ram            RAM inspection (bare command dumps 8 KB)
eeprom r <addr> <len>   Read EEPROM (hexdump; parameter partitions start at 0x0000,
                        magic CPRM + version + CRC match `param part`)
eeprom w <addr> <len>   Write EEPROM (length in decimal, then data line; be careful)

[Log/history]
genealogy <list|get|set> [id] [serial part]   Component serials and history
log            Adjust log settings (level, sources)

[LED]
led            Control indicator color (RGBW, 0-255)

[Radio/DTM]
dtm            Decimal DTM test command (RF certification)
dtm_pwr        Adjust DTM transmit power
serial_dfu     Request radio DFU mode (flash with nrfutil dfu serial -b115200 -prn 1)
nonce          Generate a new pairing code
radio          Radio sub-command tree

[Factory/test]
factory        Factory test and calibration commands
crash          Trigger a system crash (debug)"""

COMMAND_REFERENCE_ZH = """=== Lighthouse 基站所有命令参考 ===

[设备信息与系统控制]
id             查看设备标识（名称、序列号、OOTX型号、固件版本、FPGA版本）
reboot         重启基站
shutdown       关机（同时断开控制台）
isp            进入 ISP 引导模式（固件升级用）
param set sys.standby true/false   休眠/唤醒基站（真机验证可用）

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
param set <name> <val>  设置参数值（布尔参数用 true/false）
param default <name>    恢复参数为默认值
param default-all       恢复所有参数为默认值
param load [partition]  从闪存分区加载参数
param save [partition]  保存参数到闪存分区
param part              查看分区状态（Par0/1=NORM 参数区, Par2=FACT 出厂区）
param erase <partition> 擦除指定分区（危险）
param raw <r|w> <addr>  加载/保存 235 字节参数表到 EEPROM（危险）

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
step            测试转子阶跃响应（电机健康诊断）

[激光]
isl58303        访问激光驱动器 ISL58303 所有寄存器
isl58303 <reg>          读取指定寄存器（如 STATUS / ENABLE）
isl58303 <reg> <val>    写入指定寄存器（危险，慎用）
param set laser.enable <true|false>   开关激光（已在真机验证）
laser.current / laser.pwr / laser.bias        激光电流/功率/偏置
laser.phase.on / laser.phase.off              扫描开/关相位
laser.interlock / laser.fullspin / laser.apc  互锁/全周扫描/自动功率控制
sys.emission_enable     全局激光发射使能总开关

[FPGA]
fpga            访问 FPGA 寄存器（载波、OOTX、激光、电机、时基状态）

[加速度计]
lis2dh          访问 LIS2DH 加速度计寄存器

[EEPROM/RAM]
ram             RAM 检查（裸命令转储 8KB）
eeprom r <addr> <len>   读取 EEPROM（hexdump，参数分区从 0x0000 开始，
                        魔数 CPRM + 版本号 + CRC 与 param part 对应）
eeprom w <addr> <len>   EEPROM 写入（长度为十进制，随后输入数据行，慎用）

[日志/履历]
genealogy <list|get|set> [id] [serial part]   组件序列号与履历信息
log             调整日志设置（级别、来源）

[LED]
led             控制指示灯颜色 (RGBW, 0-255)

[无线/DTM]
dtm             十进制 DTM 测试命令（用于射频认证）
dtm_pwr         调整 DTM 发射功率
serial_dfu      请求无线电 DFU 模式（之后用 nrfutil dfu serial -b115200 -prn 1 刷写）
nonce           生成新的配对码
radio           无线子命令树

[工厂/测试]
factory         工厂测试与校准命令
crash           触发系统崩溃（调试用）"""


class LighthouseConsoleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._translator = Translator()
        self.root.title(self._translator("app.title"))
        self.root.geometry("1200x800")

        self._serial = SerialManager()
        self._serial.set_data_callback(self._on_data_received)
        self._is_base_station = False
        self._device_info = {}
        self._current_port = ""

        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_quick_buttons()

        self._calibration_viewer = CalibrationViewer(self._serial)

        self._set_language(self._translator.language)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _t(self, key, **values):
        return self._translator(key, **values)

    def _set_language(self, language):
        self._translator.set_language(language)
        set_current_language(language)
        self.root.title(self._t("app.title"))
        apply_widget_language(self.root, language)

        self._file_menu.entryconfigure(0, label=self._t("menu.exit"))
        self._view_menu.entryconfigure(0, label=self._t("menu.advanced_mode"))
        self._tools_menu.entryconfigure(0, label=self._t("menu.mode_chart"))
        self._tools_menu.entryconfigure(1, label=self._t("menu.param_list"))
        self._tools_menu.entryconfigure(2, label=self._t("menu.command_ref"))
        self._lang_menu.entryconfigure(0, label=self._t("language.zh"))
        self._lang_menu.entryconfigure(1, label=self._t("language.en"))
        self._menubar.entryconfigure(self._file_cascade_index, label=self._t("menu.file"))
        self._menubar.entryconfigure(self._view_cascade_index, label=self._t("menu.advanced"))
        self._menubar.entryconfigure(self._tools_cascade_index, label=self._t("menu.tools"))
        self._menubar.entryconfigure(self._language_cascade_index, label=self._t("menu.language"))
        self._language_var.set(language)

        tab_keys = ["tab.terminal", "tab.params", "tab.expert", "tab.fcal", "tab.laser",
                    "tab.maintenance", "tab.genealogy", "tab.dump", "tab.logs"]
        current_tabs = set(self._notebook.tabs())
        for frame, key in zip(self._tab_frames, tab_keys):
            if str(frame) in current_tabs:
                self._notebook.tab(frame, text=self._t(key))
        self._connect_btn.configure(text=self._t("toolbar.disconnect") if self._serial.is_connected() else self._t("toolbar.connect"))
        self._status_label.configure(text=(self._t("toolbar.connected", port=self._current_port)
                                           if self._serial.is_connected() else self._t("toolbar.not_connected")))
        for panel in (self._terminal, self._status_panel, self._hardware_panel,
                      self._param_tree, self._param_expert, self._fcal_viewer,
                      self._laser_panel, self._maintenance_panel,
                      self._genealogy_panel, self._log_panel):
            setter = getattr(panel, "set_language", None)
            if setter:
                setter(language)

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self._menubar = menubar
        self.root.config(menu=menubar)

        self._file_menu = tk.Menu(menubar, tearoff=0)
        self._file_menu.add_command(label="退出", command=self._on_close)
        self._file_cascade_index = menubar.index("end") + 1
        menubar.add_cascade(label="文件", menu=self._file_menu)

        self._view_menu = tk.Menu(menubar, tearoff=0)
        self._advanced_var = tk.BooleanVar(value=False)
        self._view_menu.add_checkbutton(label="高级模式（显示维护工具）",
                                        variable=self._advanced_var,
                                        command=self._toggle_advanced)
        self._view_cascade_index = menubar.index("end") + 1
        menubar.add_cascade(label="高级功能", menu=self._view_menu)

        self._tools_menu = tk.Menu(menubar, tearoff=0)
        self._tools_menu.add_command(label="Mode 校准数据图表", command=self._fetch_mode_data)
        self._tools_menu.add_command(label="参数列表", command=self._fetch_param_list)
        self._tools_menu.add_command(label="命令参考", command=self._show_command_reference)
        self._tools_cascade_index = menubar.index("end") + 1
        menubar.add_cascade(label="工具", menu=self._tools_menu)

        self._lang_menu = tk.Menu(menubar, tearoff=0)
        self._language_var = tk.StringVar(value=self._translator.language)
        self._lang_menu.add_radiobutton(label="中文", value="zh", variable=self._language_var,
                                        command=lambda: self._set_language("zh"))
        self._lang_menu.add_radiobutton(label="English", value="en", variable=self._language_var,
                                        command=lambda: self._set_language("en"))
        self._language_cascade_index = menubar.index("end") + 1
        menubar.add_cascade(label="语言 / Language", menu=self._lang_menu)

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

        expert_tab = tk.Frame(self._notebook)
        self._param_expert = ParamExpertPanel(expert_tab, self._serial)
        self._param_expert.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(expert_tab, text="参数专家")

        fcal_tab = tk.Frame(self._notebook)
        self._fcal_viewer = FcalViewer(fcal_tab)
        self._fcal_viewer.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(fcal_tab, text="校准参数")

        laser_tab = tk.Frame(self._notebook)
        self._laser_panel = LaserPanel(laser_tab, self._serial)
        self._laser_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._notebook.add(laser_tab, text="激光控制")

        maint_tab = tk.Frame(self._notebook)
        self._maintenance_panel = MaintenancePanel(maint_tab, self._serial)
        self._maintenance_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._notebook.add(maint_tab, text="维护工具")

        self._laser_tab = laser_tab
        self._maint_tab = maint_tab
        self._notebook.forget(maint_tab)

        genealogy_tab = tk.Frame(self._notebook)
        self._genealogy_panel = GenealogyPanel(genealogy_tab, self._serial)
        self._genealogy_panel.pack(fill=tk.BOTH, expand=True)
        self._notebook.add(genealogy_tab, text="硬件溯源")

        dump_tab = tk.Frame(self._notebook)
        self._dump_viewer = DumpViewer(self._serial)
        self._notebook.add(dump_tab, text="Dump 曲线")
        ttk.Label(dump_tab, text="点击下方按钮开始采集 20 秒 Dump 数据\n采集期间请勿发送其他命令",
                  font=("", 10)).pack(pady=20)
        ttk.Button(dump_tab, text="开始采集 Dump 数据",
                   command=lambda: self._dump_viewer.collect_and_show(self.root)).pack(pady=10)

        log_tab = tk.Frame(self._notebook)
        self._log_panel = LogPanel(log_tab, self._serial, self._terminal)
        self._log_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._notebook.add(log_tab, text="日志设置")

        self._log_tab = log_tab
        self._tab_frames = [terminal_tab, param_tab, expert_tab, fcal_tab, laser_tab,
                            maint_tab, genealogy_tab, dump_tab, log_tab]

        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

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
            ("step", "转子阶跃响应"),
        ]
        for cmd, label in commands:
            btn = ttk.Button(row1, text=label,
                             command=lambda c=cmd: self._send_quick_command(c))
            btn.pack(side=tk.LEFT, padx=2)

        row2 = tk.Frame(btn_frame)
        row2.pack(fill=tk.X, pady=(2, 0))

        ttk.Button(row2, text="刷新状态", command=self._poll_status).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="命令列表", command=self._show_command_reference).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="保存参数(闪存)", command=lambda: self._send_quick_command("param save")).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="一键备份", command=self._backup_all).pack(side=tk.LEFT, padx=2)
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
            messagebox.showwarning(tr_text("提示"), tr_text("请先选择串口"))
            return
        port_name = port_str.split(" - ")[0]
        baudrate = int(self._baud_var.get())

        self._terminal.append_system(self._t("dialog.connecting", port=port_name, baudrate=baudrate))
        if self._serial.connect(port_name, baudrate):
            self._current_port = port_name
            self._terminal.append_system(self._t("dialog.connected"))
            self._status_label.configure(text=self._t("toolbar.connected", port=port_name), foreground="green")
            self._connect_btn.configure(text=self._t("toolbar.disconnect"))
            self._port_combo.configure(state="disabled")
            self.root.after(500, self._auto_identify)
        else:
            self._terminal.append_error(self._t("dialog.connect_failed", port=port_name))
            messagebox.showerror(tr_text("连接失败"), self._t("dialog.cannot_open", port=port_name))

    def _disconnect(self):
        self._serial.disconnect()
        self._is_base_station = False
        self._device_info = {}
        self._current_port = ""
        self._terminal.append_system("已断开连接")
        self._status_label.configure(text=self._t("toolbar.not_connected"), foreground="red")
        self._connect_btn.configure(text=self._t("toolbar.connect"))
        self._port_combo.configure(state="readonly")
        self._status_panel.clear_all()
        self._param_tree.clear()
        self._fcal_viewer.clear()
        self._hardware_panel.clear_all()
        self._genealogy_panel.clear()
        self._laser_panel.clear()
        self._maintenance_panel.clear()
        self._mode_var.set("--")

    def _auto_identify(self):
        self._terminal.append_system(tr_text("正在识别设备..."))

        def identify():
            resp = self._serial.send_command("id", wait_response=True, timeout=3.0)
            id_info = parse_id_output(resp)
            if id_info.get("device_name"):
                self._is_base_station = True
                self._device_info.update(id_info)
                self.root.after(0, lambda: self._status_panel.update_all(id_info))
                self.root.after(0, lambda: self._terminal.append_system(tr_text("已确认: Lighthouse 基站")))
                self.root.after(300, self._poll_status)
            else:
                self.root.after(0, lambda: self._terminal.append_system(tr_text("未识别到基站设备, 但仍可手动发送命令")))

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
            self._terminal.append_error(self._t("terminal.not_connected"))
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
            messagebox.showwarning(tr_text("提示"), tr_text("请先连接设备"))
            return
        ok = messagebox.askyesno(
            tr_text("确认切换 Mode"),
            self._t("dialog.confirm_mode", mode=mode_val),
            icon="warning"
        )
        if ok:
            self._terminal.append_system(f"{tr_text('正在切换 Mode')} {mode_val}...")
            self._send_quick_command(f"mode {mode_val}")

    def _toggle_advanced(self):
        managed = str(self._maint_tab) in self._notebook.tabs()
        if self._advanced_var.get() and not managed:
            pos = self._notebook.index(self._laser_tab) + 1
            self._notebook.insert(pos, self._maint_tab, text=self._t("tab.maintenance"))
        elif not self._advanced_var.get() and managed:
            self._notebook.forget(self._maint_tab)

    def _backup_all(self):
        if not self._serial.is_connected():
            messagebox.showwarning(tr_text("提示"), tr_text("请先连接设备"))
            return
        self._terminal.append_system(tr_text("正在一键备份 (参数 + FCAL + ID)..."))

        def do_backup():
            paths = backup_all_to_json(self._serial, self._device_info.get("serial_number", ""))
            self.root.after(0, lambda: self._backup_all_done(paths))

        threading.Thread(target=do_backup, daemon=True).start()

    def _backup_all_done(self, paths):
        if not paths:
            messagebox.showerror(tr_text("备份失败"), tr_text("未获取到设备数据, 请检查连接"))
            return
        import os
        self._terminal.append_system(tr_text("一键备份完成") + ": " + ", ".join(os.path.basename(p) for p in paths))
        messagebox.showinfo(tr_text("一键备份完成"), self._t("dialog.backup_saved", paths="\n".join(paths)))

    def _compare_params(self):
        compare_params(self.root)

    def _on_tab_changed(self, event):
        if not self._serial.is_connected():
            return
        if self._notebook.select() == str(self._log_tab):
            self._log_panel.refresh()

    def _fetch_mode_data(self):
        if not self._serial.is_connected():
            messagebox.showwarning(tr_text("提示"), tr_text("请先连接设备"))
            return
        self._terminal.append_system(tr_text("正在采集 Mode 0-16 数据..."))

        def fetch():
            self._calibration_viewer.show_mode_chart()
            self.root.after(0, lambda: self._terminal.append_system(tr_text("Mode 数据采集完成")))

        threading.Thread(target=fetch, daemon=True).start()

    def _fetch_param_list(self):
        if not self._serial.is_connected():
            messagebox.showwarning("提示", "请先连接设备")
            return
        self._send_quick_command("param list")

    def _show_command_reference(self):
        ref = Toplevel(self.root)
        ref.title(tr_text("Lighthouse 命令参考"))
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

        content = COMMAND_REFERENCE_EN if current_language() == "en" else COMMAND_REFERENCE_ZH

        text.insert(tk.END, content)
        text.configure(state="disabled")

    def _on_close(self):
        if self._serial.is_connected():
            self._serial.disconnect()
        self.root.destroy()
