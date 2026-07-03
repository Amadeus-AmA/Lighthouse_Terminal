import tkinter as tk
from tkinter import ttk

CATEGORIES = [
    ("sys", "系统参数 (sys)"),
    ("journal", "运行履历 (journal)"),
    ("timebase", "时基与同步 (timebase)"),
    ("carrier", "载波 (carrier)"),
    ("laser", "激光驱动 (laser)"),
    ("rotor", "转子/电机 (rotor)"),
    ("ootx", "OOTX 广播 (ootx)"),
    ("accel", "加速度计 (accel)"),
    ("fcal", "出厂校准 (fcal)"),
    ("led", "LED 指示灯 (led)"),
    ("log", "日志 (log)"),
    ("stats", "统计 (stats)"),
    ("param", "参数系统 (param)"),
]

LABELS = {
    "magic": "参数区魔数",
    "sys.uptime": "本次运行时间",
    "sys.config": "当前 Mode 编号",
    "sys.faults": "当前故障数",
    "sys.name": "设备名称",
    "sys.emission_enable": "激光发射使能",
    "sys.standby": "待机模式",
    "sys.identify": "识别模式",
    "sys.dfu": "DFU 模式",
    "journal.boots": "总上电次数",
    "journal.locks": "PLL 锁定次数",
    "journal.spins": "电机总转数",
    "journal.sweeps": "激光扫描总数",
    "journal.faults": "历史故障数",
    "journal.life": "累计运行时间",
    "journal.enable": "日志使能",
    "journal.interval": "日志写入间隔(秒)",
    "journal.reason": "上次启动原因",
    "journal.debug": "日志调试",
    "timebase.period": "时基周期",
    "timebase.locked": "PLL 锁定",
    "timebase.mode": "主/从模式",
    "timebase.offset": "时基偏移",
    "timebase.p": "P 系数",
    "timebase.i": "I 系数",
    "timebase.d": "D 系数",
    "timebase.k": "K 系数",
    "timebase.current": "当前实际周期",
    "timebase.tdm": "TDM 模式",
    "timebase.tolerance": "容差",
    "timebase.debug": "时基调试",
    "timebase.output": "时基输出",
    "timebase.source": "时基来源",
    "carrier.enable": "载波使能",
    "carrier.debug": "载波调试",
    "carrier.cw": "连续波模式",
    "carrier.divider": "分频系数",
    "carrier.poly.0": "多项式 0",
    "carrier.poly.1": "多项式 1",
    "carrier.poly.f": "多项式 f",
    "laser.enable": "激光使能",
    "laser.debug": "激光调试",
    "laser.interlock": "激光互锁",
    "laser.fullspin": "全周扫描",
    "laser.phase.on": "开相位",
    "laser.phase.off": "关相位",
    "laser.bias": "偏置",
    "laser.current": "驱动电流",
    "laser.pwr": "目标功率",
    "laser.pwr.debug": "功率调试",
    "laser.pwr.b1": "功率校准 b1",
    "laser.pwr.b2": "功率校准 b2",
    "laser.pwr.m": "功率校准 m",
    "laser.pwr.gain": "功率校准增益",
    "laser.pwr.k1": "功率校准 k1",
    "laser.pwr.average": "平均功率",
    "laser.pwr.detected": "实测功率",
    "laser.apc": "自动功率控制",
    "laser.apc.debug": "APC 调试",
    "laser.apc.i": "APC 积分系数",
    "rotor.enable": "电机使能",
    "rotor.debug": "电机调试",
    "rotor.status": "转子状态",
    "rotor.pwm": "PWM 占空比",
    "rotor.pwm.m": "PWM 斜率",
    "rotor.pwm.b": "PWM 截距",
    "rotor.pwm.rt": "PWM 实时值",
    "rotor.pwm.auto": "自动 PWM",
    "rotor.pwm.i": "PWM 积分系数",
    "rotor.pwm.int": "PWM 积分值",
    "rotor.pwm.fine": "PWM 精调基值",
    "rotor.pll.enable": "PLL 使能",
    "rotor.pll.debug": "PLL 调试",
    "rotor.pll.p": "PLL P 系数",
    "rotor.pll.i": "PLL I 系数",
    "rotor.pll.d": "PLL D 系数",
    "rotor.pll.s": "PLL 动态系数",
    "rotor.pll.offset": "PLL 相位偏移",
    "rotor.pll.jitter": "PLL 抖动容限",
    "rotor.pll.phase": "PLL 相位",
    "rotor.pll.settle": "PLL 稳定时间",
    "rotor.autoclear": "自动清零",
    "ootx.enable": "OOTX 调试",
    "ootx.debug": "OOTX 调试输出",
    "ootx.lock_required": "需锁相才发",
    "ootx.model_override": "型号覆盖",
    "ootx.nonce": "随机数",
    "accel.enable": "加速度计使能",
    "accel.debug": "加速度计调试",
    "accel.b1": "加速度计 b1",
    "accel.x": "X 轴加速度",
    "accel.y": "Y 轴加速度",
    "accel.z": "Z 轴加速度",
    "accel.magnitude": "合加速度模长",
    "accel.is_gravity": "静态判定",
    "accel.dir_x": "X 轴方向",
    "accel.dir_y": "Y 轴方向",
    "accel.dir_z": "Z 轴方向",
    "accel.temp": "温度",
    "fcal.0.tilt": "Axis0 倾角",
    "fcal.0.phase": "Axis0 相位",
    "fcal.0.curve": "Axis0 弯曲校正",
    "fcal.0.gibphase": "Axis0 Gib 相位",
    "fcal.0.gibmag": "Axis0 Gib 幅度",
    "fcal.0.ogeephase": "Axis0 Ogee 相位",
    "fcal.0.ogeemag": "Axis0 Ogee 幅度",
    "fcal.1.tilt": "Axis1 倾角",
    "fcal.1.phase": "Axis1 相位",
    "fcal.1.curve": "Axis1 弯曲校正",
    "fcal.1.gibphase": "Axis1 Gib 相位",
    "fcal.1.gibmag": "Axis1 Gib 幅度",
    "fcal.1.ogeephase": "Axis1 Ogee 相位",
    "fcal.1.ogeemag": "Axis1 Ogee 幅度",
    "led.enable": "LED 使能",
    "led.r": "红色",
    "led.g": "绿色",
    "led.b": "蓝色",
    "led.w": "白色",
    "log.level": "日志级别",
    "log.sources": "日志来源",
    "log.srcs_en": "日志来源使能",
    "stats.enable": "统计打印",
    "stats.interval": "统计间隔",
}

LIFE_FORMAT_KEYS = {"journal.life"}


class ParamTreePanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self._tree = ttk.Treeview(self, columns=("value", "dynamic"), show="tree headings")
        self._tree.heading("#0", text="参数名称")
        self._tree.heading("value", text="当前值")
        self._tree.heading("dynamic", text="")

        self._tree.column("#0", width=260)
        self._tree.column("value", width=180, anchor="w")
        self._tree.column("dynamic", width=40, anchor="center", stretch=False)

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.tag_configure("dynamic", foreground="#e5c07b")

        for prefix, label in CATEGORIES:
            self._tree.insert("", tk.END, iid=prefix, text=label, open=False)

    def load_from_text(self, text: str):
        from data_parser import parse_param_list, format_life_ticks

        params = parse_param_list(text)

        for item in self._tree.get_children():
            self._tree.delete(*self._tree.get_children(item))

        for key, value in params.items():
            category = key.split(".")[0] if "." in key else "_other"
            if category not in [c[0] for c in CATEGORIES]:
                continue

            label = LABELS.get(key, key.split(".", 1)[-1] if "." in key else key)

            raw_line = None
            for line in text.strip().split("\n"):
                if line.strip().startswith(key):
                    raw_line = line
                    break

            if key == "journal.life" and isinstance(value, (int, float)):
                value = format_life_ticks(int(value))

            value_str = str(value)
            if isinstance(value, float) and value == int(value):
                value_str = str(int(value))

            if raw_line and raw_line.rstrip().endswith("*"):
                self._tree.insert(category, tk.END, text=label, values=(value_str, "*"), tags=("dynamic",))
            else:
                self._tree.insert(category, tk.END, text=label, values=(value_str, ""))

    def clear(self):
        for item in self._tree.get_children():
            self._tree.delete(*self._tree.get_children(item))
