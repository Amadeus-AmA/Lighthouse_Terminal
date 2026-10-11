"""Small runtime i18n helper for Lighthouse Terminal.

UI labels use stable resource keys; protocol commands and device output stay unchanged.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

LANGUAGE_NAMES = {"zh": "中文", "en": "English"}
DEFAULT_LANGUAGE = "zh"

TRANSLATIONS = {
    "app.title": {"zh": "Lighthouse 基站控制台", "en": "Lighthouse Base Station Console"},
    "menu.file": {"zh": "文件", "en": "File"},
    "menu.exit": {"zh": "退出", "en": "Exit"},
    "menu.advanced": {"zh": "高级功能", "en": "Advanced"},
    "menu.advanced_mode": {"zh": "高级模式（显示维护工具）", "en": "Advanced mode (show maintenance tools)"},
    "menu.tools": {"zh": "工具", "en": "Tools"},
    "menu.mode_chart": {"zh": "Mode 校准数据图表", "en": "Mode calibration chart"},
    "menu.param_list": {"zh": "参数列表", "en": "Parameter list"},
    "menu.command_ref": {"zh": "命令参考", "en": "Command reference"},
    "menu.language": {"zh": "语言 / Language", "en": "语言 / Language"},
    "language.zh": {"zh": "中文", "en": "Chinese"},
    "language.en": {"zh": "English", "en": "English"},
    "toolbar.port": {"zh": "串口:", "en": "Port:"},
    "toolbar.baud": {"zh": "波特率:", "en": "Baud rate:"},
    "toolbar.scan": {"zh": "扫描", "en": "Scan"},
    "toolbar.connect": {"zh": "连接", "en": "Connect"},
    "toolbar.disconnect": {"zh": "断开", "en": "Disconnect"},
    "toolbar.not_connected": {"zh": "未连接", "en": "Not connected"},
    "toolbar.connected": {"zh": "已连接 {port}", "en": "Connected: {port}"},
    "toolbar.mode": {"zh": "Mode:", "en": "Mode:"},
    "toolbar.apply": {"zh": "应用", "en": "Apply"},
    "tab.terminal": {"zh": "终端", "en": "Terminal"},
    "tab.params": {"zh": "参数树", "en": "Parameters"},
    "tab.fcal": {"zh": "校准参数", "en": "Calibration"},
    "tab.laser": {"zh": "激光控制", "en": "Laser control"},
    "tab.maintenance": {"zh": "维护工具", "en": "Maintenance"},
    "tab.genealogy": {"zh": "硬件溯源", "en": "Hardware genealogy"},
    "tab.dump": {"zh": "Dump 曲线", "en": "Dump chart"},
    "tab.logs": {"zh": "日志设置", "en": "Log settings"},
    "tab.expert": {"zh": "参数专家", "en": "Param expert"},
    "quick.device": {"zh": "设备信息", "en": "Device info"},
    "quick.uptime": {"zh": "运行时间", "en": "Uptime"},
    "quick.freq": {"zh": "转子频率", "en": "Rotor frequency"},
    "quick.params": {"zh": "参数列表", "en": "Parameter list"},
    "quick.fpga": {"zh": "FPGA 状态", "en": "FPGA status"},
    "quick.laser_driver": {"zh": "激光驱动", "en": "Laser driver"},
    "quick.perf": {"zh": "性能测试", "en": "Performance"},
    "quick.pwmcal": {"zh": "粗调电机PWM校准", "en": "Coarse motor PWM calibration"},
    "quick.pwmopt": {"zh": "粗调 PWM 优化搜索", "en": "Coarse PWM optimization"},
    "quick.pwmgain": {"zh": "粗/细 PWM 增益测量", "en": "Coarse/fine PWM gain"},
    "quick.step": {"zh": "转子阶跃响应", "en": "Rotor step response"},
    "quick.refresh": {"zh": "刷新状态", "en": "Refresh status"},
    "quick.commands": {"zh": "命令列表", "en": "Commands"},
    "quick.save": {"zh": "保存参数(闪存)", "en": "Save parameters"},
    "quick.backup": {"zh": "一键备份", "en": "Backup all"},
    "quick.compare": {"zh": "对比参数", "en": "Compare parameters"},
    "terminal.send": {"zh": "发送", "en": "Send"},
    "terminal.not_connected": {"zh": "未连接到设备", "en": "Device is not connected"},
    "status.title": {"zh": "设备状态", "en": "Device status"},
    "status.device_info": {"zh": "设备信息", "en": "Device information"},
    "status.runtime": {"zh": "运行状态", "en": "Runtime"},
    "status.laser": {"zh": "激光状态", "en": "Laser status"},
    "status.journal": {"zh": "设备履历 (Journal)", "en": "Device history (Journal)"},
    "status.ootx_model": {"zh": "OOTX 型号", "en": "OOTX model"},
    "status.serial": {"zh": "序列号", "en": "Serial number"},
    "status.firmware": {"zh": "固件版本", "en": "Firmware"},
    "status.fpga": {"zh": "FPGA 版本", "en": "FPGA version"},
    "status.radio": {"zh": "Radio 电压", "en": "Radio voltage"},
    "status.mode": {"zh": "当前 Mode", "en": "Current mode"},
    "status.uptime": {"zh": "运行时间", "en": "Uptime"},
    "status.rotor": {"zh": "转子状态", "en": "Rotor status"},
    "status.laser_current": {"zh": "激光电流", "en": "Laser current"},
    "status.laser_power": {"zh": "激光功率(设定)", "en": "Laser power (set)"},
    "status.laser_average": {"zh": "激光功率(平均)", "en": "Laser power (average)"},
    "status.laser_bias": {"zh": "激光偏置", "en": "Laser bias"},
    "status.laser_enable": {"zh": "激光使能", "en": "Laser enabled"},
    "status.boots": {"zh": "总上电次数", "en": "Power-on count"},
    "status.locks": {"zh": "PLL 锁定次数", "en": "PLL lock count"},
    "status.spins": {"zh": "电机总转数", "en": "Total spins"},
    "status.sweeps": {"zh": "激光扫描总数", "en": "Total sweeps"},
    "status.faults": {"zh": "历史故障次数", "en": "Historical faults"},
    "status.life": {"zh": "累计运行滴答", "en": "Accumulated runtime"},
    "hardware.title": {"zh": "硬件健康状态", "en": "Hardware health"},
    "hardware.power": {"zh": "激光供电正常", "en": "Laser power good"},
    "hardware.chip": {"zh": "激光芯片已使能", "en": "Laser chip enabled"},
    "hardware.motor": {"zh": "电机使能", "en": "Motor enabled"},
    "hardware.sync": {"zh": "接收同步信号", "en": "Sync signal"},
    "fcal.title": {"zh": "出厂校准参数 (fcal.*) — 每个基站独一无二，修改需谨慎", "en": "Factory calibration (fcal.*) — unique to each base station"},
    "fcal.item": {"zh": "校准项", "en": "Calibration item"},
    "fcal.tilt": {"zh": "倾角 (弧度)", "en": "Tilt (radians)"},
    "fcal.phase": {"zh": "初始相位偏移 (弧度)", "en": "Initial phase offset (radians)"},
    "fcal.curve": {"zh": "扫描线弯曲校正系数", "en": "Scan curve correction"},
    "fcal.gibphase": {"zh": "Gib 效应相位校正", "en": "Gib phase correction"},
    "fcal.gibmag": {"zh": "Gib 效应幅度校正", "en": "Gib magnitude correction"},
    "fcal.ogeephase": {"zh": "Ogee 效应相位校正", "en": "Ogee phase correction"},
    "fcal.ogeemag": {"zh": "Ogee 效应幅度校正", "en": "Ogee magnitude correction"},
    "genealogy.title": {"zh": "硬件溯源 — 设备各组件序列号与版本信息", "en": "Hardware genealogy — component serials and versions"},
    "genealogy.item": {"zh": "溯源项", "en": "Component"},
    "genealogy.info": {"zh": "信息", "en": "Information"},
    "genealogy.editor": {"zh": "字段编辑 (genealogy set <id> <serial> <part>)", "en": "Field editor (genealogy set <id> <serial> <part>)"},
    "genealogy.field": {"zh": "字段:", "en": "Field:"},
    "genealogy.serial": {"zh": "序列号:", "en": "Serial:"},
    "genealogy.part": {"zh": "版本:", "en": "Part:"},
    "genealogy.write": {"zh": "写入字段", "en": "Write field"},
    "genealogy.hint": {"zh": "提示: 两栏都填 - = 槽位写零, 恢复出厂空置显示 (- -); spare 槽可随意测试; model/top/main/upper 为设备身份字段, 修改需谨慎。", "en": "Tip: enter - in both fields to zero-fill the slot and restore the factory empty state; spare slots are safe to test; identity fields require care."},
    "genealogy.confirm": {"zh": "确认写入", "en": "Confirm write"},
    "genealogy.not_connected": {"zh": "请先连接设备", "en": "Connect to a device first"},
    "genealogy.fields_required": {"zh": "序列号和版本都要填写 (两栏都填 - 可清零恢复空置)", "en": "Enter both serial and part (use - in both fields to zero-fill)"},
    "genealogy.writing": {"zh": "正在写入 {gid} ...", "en": "Writing {gid} ..."},
    "genealogy.cleared": {"zh": "已清零: {detail}", "en": "Zero-filled: {detail}"},
    "genealogy.executed": {"zh": "已执行: {detail}", "en": "Executed: {detail}"},
    "genealogy.failed": {"zh": "写入可能失败 (设备回显: {response})", "en": "Write may have failed (device response: {response})"},
    "laser.title": {"zh": "激光实时状态 (param list)", "en": "Live laser status (param list)"},
    "laser.control": {"zh": "开关与参数控制 (param set, 修改需谨慎)", "en": "Switches and parameters (param set, use with care)"},
    "laser.registers": {"zh": "ISL58303 激光驱动寄存器", "en": "ISL58303 laser driver registers"},
    "laser.fpga": {"zh": "FPGA 激光通道", "en": "FPGA laser channel"},
    "laser.refresh": {"zh": "刷新状态", "en": "Refresh status"},
    "laser.auto": {"zh": "自动刷新 (3秒)", "en": "Auto refresh (3 sec)"},
    "laser.apply": {"zh": "应用", "en": "Apply"},
    "laser.set": {"zh": "设置", "en": "Set"},
    "laser.read_all": {"zh": "读取全部寄存器", "en": "Read all registers"},
    "laser.read": {"zh": "读取寄存器", "en": "Read register"},
    "laser.write": {"zh": "写入寄存器", "en": "Write register"},
    "laser.custom": {"zh": "自定义命令:", "en": "Custom command:"},
    "laser.send": {"zh": "发送", "en": "Send"},
    "laser.reference": {"zh": "参考值(正常基站): current≈123, pwr≈70, phase.on≈10, phase.off≈350", "en": "Reference (normal station): current≈123, pwr≈70, phase.on≈10, phase.off≈350"},
    "maintenance.partition": {"zh": "参数闪存分区 (param part / save / load)", "en": "Parameter flash partitions (param part / save / load)"},
    "maintenance.eeprom": {"zh": "EEPROM 读取 (eeprom r <地址> <长度>)", "en": "EEPROM read (eeprom r <address> <length>)"},
    "maintenance.journal": {"zh": "履历日志 (journal 记录区)", "en": "History log (journal records)"},
    "maintenance.power": {"zh": "基站电源 (sys.standby)", "en": "Base station power (sys.standby)"},
    "maintenance.restore": {"zh": "恢复与固件", "en": "Restore and firmware"},
    "maintenance.refresh_parts": {"zh": "查看分区状态", "en": "Refresh partitions"},
    "maintenance.save_partition": {"zh": "保存到分区 (修复)", "en": "Save to partition (repair)"},
    "maintenance.load_partition": {"zh": "从分区加载", "en": "Load from partition"},
    "maintenance.erase_partition": {"zh": "擦除分区", "en": "Erase partition"},
    "maintenance.read": {"zh": "读取", "en": "Read"},
    "maintenance.backup_partition": {"zh": "备份整个分区", "en": "Backup partition"},
    "maintenance.save_range": {"zh": "保存区间到文件", "en": "Save range to file"},
    "maintenance.sleep": {"zh": "休眠基站", "en": "Sleep base station"},
    "maintenance.wake": {"zh": "唤醒基站", "en": "Wake base station"},
    "maintenance.journal_button": {"zh": "扫描并查看履历日志", "en": "Scan and view history"},
    "maintenance.restore_params": {"zh": "恢复参数备份...", "en": "Restore parameter backup..."},
    "maintenance.restore_fcal": {"zh": "写入 FCAL 校准...", "en": "Write FCAL calibration..."},
    "maintenance.dfu": {"zh": "进入无线 DFU 模式", "en": "Enter wireless DFU mode"},
    "common.confirm": {"zh": "确认", "en": "Confirm"},
    "common.warning": {"zh": "提示", "en": "Notice"},
    "common.error": {"zh": "错误", "en": "Error"},
    "common.complete": {"zh": "完成", "en": "Complete"},
    "common.cancel": {"zh": "取消", "en": "Cancel"},
    "common.close": {"zh": "关闭", "en": "Close"},
    "dialog.not_connected": {"zh": "请先连接设备", "en": "Connect to a device first"},
    "dialog.connecting": {"zh": "正在连接 {port} @ {baudrate}...", "en": "Connecting to {port} @ {baudrate}..."},
    "dialog.connected": {"zh": "连接成功", "en": "Connected"},
    "dialog.connect_failed": {"zh": "连接失败: {port}", "en": "Connection failed: {port}"},
    "dialog.cannot_open": {"zh": "无法打开串口 {port}", "en": "Could not open serial port {port}"},
    "dialog.identifying": {"zh": "正在识别设备...", "en": "Identifying device..."},
    "dialog.identified": {"zh": "已确认: Lighthouse 基站", "en": "Confirmed: Lighthouse base station"},
    "dialog.not_identified": {"zh": "未识别到基站设备, 但仍可手动发送命令", "en": "Base station not identified; manual commands are still available"},
    "dialog.confirm_mode_title": {"zh": "确认切换 Mode", "en": "Confirm mode change"},
    "dialog.confirm_mode": {"zh": "即将切换到 Mode {mode}, 这会修改 timebase.period / rotor.pwm / rotor.pll.offset。\n确认切换?", "en": "Mode {mode} will change timebase.period / rotor.pwm / rotor.pll.offset.\nContinue?"},
    "dialog.backup_running": {"zh": "正在一键备份 (参数 + FCAL + ID)...", "en": "Backing up parameters + FCAL + ID..."},
    "dialog.backup_failed": {"zh": "未获取到设备数据, 请检查连接", "en": "No device data received; check the connection"},
    "dialog.backup_done": {"zh": "一键备份完成", "en": "Backup complete"},
    "dialog.backup_saved": {"zh": "已保存:\n{paths}", "en": "Saved:\n{paths}"},
    "dump.instructions": {"zh": "点击下方按钮开始采集 20 秒 Dump 数据\n采集期间请勿发送其他命令", "en": "Click below to collect 20 seconds of Dump data\nDo not send other commands while collecting"},
    "dump.start": {"zh": "开始采集 Dump 数据", "en": "Collect Dump data"},
    "command.title": {"zh": "Lighthouse 命令参考", "en": "Lighthouse command reference"},
}

# Exact Chinese UI text -> English. Stable protocol values are intentionally omitted.
TEXT_EN = {
    "校准参数": "Calibration", "参数名称": "Parameter", "当前值": "Value", "每个基站独一无二": "unique to each station",
    "出厂校准参数": "Factory calibration", "参数区魔数": "Parameter magic", "本次运行时间": "Current uptime", "当前 Mode 编号": "Current mode",
    "当前故障数": "Current faults", "设备名称": "Device name", "激光发射使能": "Laser emission enabled", "待机模式": "Standby mode",
    "识别模式": "Identify mode", "DFU 模式": "DFU mode", "总上电次数": "Power-on count", "PLL 锁定次数": "PLL lock count",
    "电机总转数": "Total motor spins", "激光扫描总数": "Total laser sweeps", "历史故障数": "Historical faults",
    "累计运行时间": "Accumulated runtime", "日志使能": "Logging enabled", "日志写入间隔(秒)": "Log interval (sec)",
    "上次启动原因": "Last boot reason", "日志调试": "Log debug", "时基周期": "Timebase period", "PLL 锁定": "PLL locked",
    "主/从模式": "Master/slave mode", "时基偏移": "Timebase offset", "P 系数": "P coefficient", "I 系数": "I coefficient",
    "D 系数": "D coefficient", "K 系数": "K coefficient", "当前实际周期": "Current actual period", "TDM 模式": "TDM mode",
    "容差": "Tolerance", "时基调试": "Timebase debug", "时基输出": "Timebase output", "时基来源": "Timebase source",
    "载波使能": "Carrier enabled", "载波调试": "Carrier debug", "连续波模式": "Continuous wave mode", "分频系数": "Divider",
    "多项式 0": "Polynomial 0", "多项式 1": "Polynomial 1", "多项式 f": "Polynomial f", "激光使能": "Laser enabled",
    "激光调试": "Laser debug", "激光互锁": "Laser interlock", "全周扫描": "Full-spin scan", "开相位": "On phase",
    "关相位": "Off phase", "偏置": "Bias", "驱动电流": "Drive current", "目标功率": "Target power", "功率调试": "Power debug",
    "功率校准 b1": "Power calibration b1", "功率校准 b2": "Power calibration b2", "功率校准 m": "Power calibration m",
    "功率校准增益": "Power calibration gain", "功率校准 k1": "Power calibration k1", "平均功率": "Average power",
    "实测功率": "Detected power", "自动功率控制": "Automatic power control", "APC 调试": "APC debug", "APC 积分系数": "APC integral coefficient",
    "电机使能": "Motor enabled", "电机调试": "Motor debug", "转子状态": "Rotor status", "PWM 占空比": "PWM duty cycle",
    "PWM 斜率": "PWM slope", "PWM 截距": "PWM intercept", "PWM 实时值": "PWM live value", "自动 PWM": "Automatic PWM",
    "PWM 积分系数": "PWM integral coefficient", "PWM 积分值": "PWM integral", "PWM 精调基值": "PWM fine base",
    "PLL 使能": "PLL enabled", "PLL 调试": "PLL debug", "PLL P 系数": "PLL P coefficient", "PLL I 系数": "PLL I coefficient",
    "PLL D 系数": "PLL D coefficient", "PLL 动态系数": "PLL dynamic coefficient", "PLL 相位偏移": "PLL phase offset",
    "PLL 抖动容限": "PLL jitter tolerance", "PLL 相位": "PLL phase", "PLL 稳定时间": "PLL settle time", "自动清零": "Auto clear",
    "OOTX 调试": "OOTX debug", "OOTX 调试输出": "OOTX debug output", "需锁相才发": "Require lock to transmit",
    "型号覆盖": "Model override", "随机数": "Nonce", "加速度计使能": "Accelerometer enabled", "加速度计调试": "Accelerometer debug",
    "加速度计 b1": "Accelerometer b1", "X 轴加速度": "X acceleration", "Y 轴加速度": "Y acceleration", "Z 轴加速度": "Z acceleration",
    "合加速度模长": "Acceleration magnitude", "静态判定": "Gravity detected", "X 轴方向": "X direction", "Y 轴方向": "Y direction",
    "Z 轴方向": "Z direction", "温度": "Temperature", "Axis0 倾角": "Axis 0 tilt", "Axis0 相位": "Axis 0 phase",
    "Axis0 弯曲校正": "Axis 0 curve correction", "Axis0 Gib 相位": "Axis 0 Gib phase", "Axis0 Gib 幅度": "Axis 0 Gib magnitude",
    "Axis0 Ogee 相位": "Axis 0 Ogee phase", "Axis0 Ogee 幅度": "Axis 0 Ogee magnitude", "Axis1 倾角": "Axis 1 tilt",
    "Axis1 相位": "Axis 1 phase", "Axis1 弯曲校正": "Axis 1 curve correction", "Axis1 Gib 相位": "Axis 1 Gib phase",
    "Axis1 Gib 幅度": "Axis 1 Gib magnitude", "Axis1 Ogee 相位": "Axis 1 Ogee phase", "Axis1 Ogee 幅度": "Axis 1 Ogee magnitude",
    "LED 使能": "LED enabled", "红色": "Red", "绿色": "Green", "蓝色": "Blue", "白色": "White", "日志级别": "Log level",
    "日志来源": "Log sources", "日志来源使能": "Log sources enabled", "统计打印": "Statistics output", "统计间隔": "Statistics interval",
    "系统参数 (sys)": "System (sys)", "运行履历 (journal)": "History (journal)", "时基与同步 (timebase)": "Timebase and sync (timebase)",
    "载波 (carrier)": "Carrier", "激光驱动 (laser)": "Laser driver", "转子/电机 (rotor)": "Rotor/motor", "OOTX 广播 (ootx)": "OOTX broadcast",
    "加速度计 (accel)": "Accelerometer", "出厂校准 (fcal)": "Factory calibration", "LED 指示灯 (led)": "LED indicators",
    "日志 (log)": "Logging", "统计 (stats)": "Statistics", "参数系统 (param)": "Parameters",
    "整机型号 (协议广播 Model)": "Base station model (broadcast model)", "整机顶层 SN": "Top-level serial", "主板 (Main PCB)": "Main PCB",
    "上层板 (Upper PCB)": "Upper PCB", "天线": "Antenna", "激光模组": "Laser module", "电机总成": "Motor assembly",
    "机壳": "Chassis", "备用位 1": "Spare 1", "备用位 2": "Spare 2", "备用位 3": "Spare 3",
    "硬件溯源 — 设备各组件序列号与版本信息": "Hardware genealogy — component serial numbers and versions",
    "溯源项": "Component", "信息": "Information", "字段编辑 (genealogy set <id> <serial> <part>)": "Edit field (genealogy set <id> <serial> <part>)",
    "字段:": "Field:", "序列号:": "Serial:", "版本:": "Part:", "写入字段": "Write field",
    "确认写入": "Confirm write", "未连接到设备": "Device is not connected", "请先连接设备": "Connect to a device first",
    "提示": "Notice", "错误": "Error", "警告": "Warning", "完成": "Complete", "备份完成": "Backup complete",
    "保存参数备份": "Save parameter backup", "选择第一份参数备份 (文件 A)": "Select first parameter backup (File A)",
    "选择第二份参数备份 (文件 B)": "Select second parameter backup (File B)", "参数备份对比": "Parameter backup comparison",
    "参数名称": "Parameter", "共 ": "Total ", " 个参数，其中 ": " parameters, ", " 个差异": " differences",
    "日志设置": "Log settings", "当前状态": "Current status", "级别:": "Level:", "日志级别": "Log level",
    "日志来源筛选": "Log source filter", "应用筛选": "Apply filter", "操作": "Actions", "从设备刷新状态": "Refresh from device",
    "重置为默认 (Debug + 全开)": "Reset to defaults (Debug + all sources)", "消息": "Messaging", "电机": "Rotor", "激光": "Laser", "系统": "System",
    "正在读取 EEPROM 履历记录区 (0x554-0xFC0, 2668 字节)...": "Reading EEPROM history records (0x554-0xFC0, 2668 bytes)...",
    "扫描并查看履历日志": "Scan and view history log", "正在采集 Mode 0-16 数据...": "Collecting Mode 0-16 data...",
    "Mode 数据采集完成": "Mode data collection complete", "正在连接设备...": "Connecting to device...",
}

# Additional UI strings collected across panels.
TEXT_EN.update({
    # status panel
    "设备状态": "Device status", "OOTX 型号": "OOTX model", "序列号": "Serial number",
    "固件版本": "Firmware build", "FPGA 版本": "FPGA version", "Radio 电压": "Radio voltage",
    "当前 Mode": "Current mode", "运行时间": "Uptime", "转子状态": "Rotor status",
    "激光电流": "Laser current", "激光功率(设定)": "Laser power (set)",
    "激光功率(平均)": "Laser power (average)", "激光偏置": "Laser bias",
    "激光使能": "Laser enabled", "累计运行滴答": "Runtime ticks",
    # toolbar
    "串口": "Port", "波特率": "Baud rate", "扫描": "Scan", "连接": "Connect", "断开": "Disconnect",
    "未连接": "Not connected", "应用": "Apply",
    # laser panel
    "全局发射使能": "Global emission enable", "驱动电流 (mA)": "Drive current (mA)",
    "自动功率控制 APC": "Automatic power control (APC)", "刷新状态": "Refresh status",
    "自动刷新 (3秒)": "Auto refresh (3s)", "设置": "Set", "读取全部寄存器": "Read all registers",
    "读取寄存器": "Read register", "写入寄存器": "Write register", "寄存器": "Register",
    "值": "Value", "自定义命令": "Custom command", "确认修改": "Confirm change",
    "该操作会修改设备参数, 确认执行?": "This changes device parameters. Continue?",
    "即将发送:": "About to send:", "确认写入寄存器": "Confirm register write",
    "错误取值可能导致激光器件永久损坏!": "Wrong values can permanently damage the laser diode!",
    "请选择或输入寄存器名称/地址": "Select or type a register name/address",
    "请输入寄存器和要写入的值": "Enter register and value to write",
    "请先输入参数值": "Enter a parameter value first",
    # maintenance panel
    "分区": "Partition", "类型": "Type", "地址": "Address", "CRC 状态": "CRC status", "版本": "Version",
    "长度": "Length", "未知分区地址": "Unknown partition address",
    "确认保存分区": "Confirm partition save", "确认加载分区": "Confirm partition load",
    "确认擦除分区": "Confirm partition erase", "完成": "Complete", "已保存:": "Saved:",
    "备份分区完成": "Partition backup complete", "未获取到分区数据": "No partition data received",
    "已发送休眠命令": "Sleep command sent", "已发送唤醒命令": "Wake command sent",
    "确认进入 DFU": "Confirm entering DFU", "休眠基站": "Sleep base station", "唤醒基站": "Wake base station",
    "Par0 / Par1 为正常运行参数区 (NORM), Par2 为出厂参数区 (FACT)。\n修复分区 = 用当前内存中的参数重新保存到指定分区; 加载分区 = 用分区内容覆盖当前参数。":
        "Par0/Par1 are the normal parameter partitions (NORM); Par2 is the factory partition (FACT).\n"
        "Save to partition = write current parameters to the selected partition (repair); "
        "Load from partition = overwrite current parameters with the partition contents.",
    "每次开关机都会留下一组 boots/locks/faults/spins/sweeps 快照, 可核查设备的真实使用与断电历史。":
        "Each power cycle leaves a boots/locks/faults/spins/sweeps snapshot for auditing real usage and power-loss history.",
    "休眠后电机与激光停转, 串口控制台仍然可用, 点击唤醒即可恢复。":
        "Motors and lasers stop while asleep; the serial console stays available - wake to resume.",
    "DFU: 进入后控制台关闭, 使用 nrfutil dfu serial -b115200 -prn 1 刷写无线电固件。":
        "DFU: the console closes after entering; flash the radio with nrfutil dfu serial -b115200 -prn 1.",
    "写入可能失败": "Write may have failed", "正在写入": "Writing",
    # log panel
    "级别": "Level", "消息": "Messaging", "系统": "System", "应用筛选": "Apply filter",
    # dialogs
    "确认切换 Mode": "Confirm mode change", "正在切换 Mode": "Switching mode",
    "已断开连接": "Disconnected", "正在识别设备...": "Identifying device...",
    "已确认: Lighthouse 基站": "Confirmed: Lighthouse base station",
    "未识别到基站设备, 但仍可手动发送命令": "Base station not identified; manual commands are still available",
    "正在一键备份 (参数 + FCAL + ID)...": "Backing up parameters + FCAL + ID...",
    "备份失败": "Backup failed", "未获取到设备数据, 请检查连接": "No device data received; check the connection",
    "一键备份完成": "Backup complete", "正在采集 Mode 0-16 数据...": "Collecting Mode 0-16 data...",
    "Mode 数据采集完成": "Mode data collection complete", "模式": "Mode",
    # compare / restore dialogs
    "选择 JSON 文件": "Select JSON file", "加载失败": "Load failed", "对比": "Compare",
    "参数名称": "Parameter", "差异": "diff", "相同": "same",
    "确认恢复参数": "Confirm parameter restore", "恢复完成": "Restore complete",
    "确认写入 FCAL 校准": "Confirm FCAL write", "写入完成": "Write complete",
    "正在恢复参数": "Restoring parameters", "正在写入 FCAL": "Writing FCAL",
    # journal viewer
    "履历日志查看器 (journal 记录区 0x554-0xFC0)": "History log viewer (journal records 0x554-0xFC0)",
    "记录地址": "Record addr", "累计运行": "Accumulated", "上电次数": "Boot count",
    "PLL 锁定": "PLL locks", "故障数": "Faults", "未识别到有效记录": "No valid records found",
    # charts
    "Dump 相位误差趋势": "Dump phase error trend", "Mode 校准数据": "Mode calibration data",
    "PWM 校准数据": "PWM calibration data",
    # laser panel labels
    "激光实时状态 (param list)": "Live laser status (param list)",
    "开关与参数控制 (param set, 修改需谨慎)": "Switches and parameters (param set, use with care)",
    "ISL58303 激光驱动寄存器": "ISL58303 laser driver registers",
    "FPGA 激光通道": "FPGA laser channel",
    "提示: 若设备不识别 true/false, 请改在终端发送 param set <参数> 1 或 0":
        "Tip: if the device rejects true/false, send param set <name> 1 or 0 in the terminal",
    "参考值(正常基站): current≈123, pwr≈70, phase.on≈10, phase.off≈350":
        "Reference (normal station): current≈123, pwr≈70, phase.on≈10, phase.off≈350",
    "刷新 (fpga)": "Refresh (fpga)",
    "即将直接写入激光驱动芯片寄存器:": "Writing directly to the laser driver register:",
    # param tree
    "参数名称": "Parameter name", "当前值": "Value",
    # misc
    "设备信息": "Device information", "运行状态": "Runtime", "激光状态": "Laser status",
    "设备履历 (Journal)": "Device history (Journal)", "发送": "Send", "应用": "Apply",
    "已发送": "Sent",
    "已清零": "Zero-filled", "已执行": "Executed", "数据:": "Data:",
    "保存区间": "Save range", "保存区间完成": "Range saved", "备份分区": "Backup partition",
    # quick buttons
    "运行时间": "Uptime", "转子频率": "Rotor frequency", "参数列表": "Parameter list",
    "FPGA 状态": "FPGA status", "激光驱动": "Laser driver", "性能测试": "Performance",
    "粗调电机PWM校准": "Coarse motor PWM cal", "粗调 PWM 优化搜索": "Coarse PWM optimize",
    "粗/细 PWM 增益测量": "Coarse/fine PWM gain", "转子阶跃响应": "Rotor step response",
    "命令列表": "Commands", "保存参数(闪存)": "Save parameters", "一键备份": "Backup all",
    "对比参数": "Compare parameters",
    # dump tab
    "点击下方按钮开始采集 20 秒 Dump 数据\n采集期间请勿发送其他命令":
        "Click the button below to collect 20 s of Dump data\nDo not send other commands while collecting",
    "开始采集 Dump 数据": "Collect Dump data",
    # param expert panel
    "参数专家": "Param expert", "参数名": "Parameter", "类型": "Type",
    "默认值": "Default", "未保存": "Unsaved", "描述": "Description", "搜索:": "Search:",
    "刷新值": "Refresh values", "采集元数据": "Collect metadata", "保存到闪存": "Save to flash",
    "编辑参数": "Edit parameter", "新值": "New value", "写入": "Write",
    "同时保存到闪存 (param save)": "Also save to flash (param save)",
    "只读参数 (固件拒绝 param set)": "Read-only parameter (firmware rejects param set)",
    "该参数由固件保护, 无法通过串口修改。": "Protected by firmware; not writable over serial.",
    "值必须是数字": "Value must be numeric", "值必须是 true/false": "Value must be true/false",
    "超出类型范围": "Value out of range for type", "是": "Yes",
    "基线": "Baseline", "重设基线": "Re-baseline", "请先刷新参数值": "Refresh parameter values first",
    "未识别到设备序列号": "Device serial not identified yet",
    # menus
    "文件": "File", "高级功能": "Advanced", "工具": "Tools", "退出": "Exit",
    "高级模式（显示维护工具）": "Advanced mode (show maintenance tools)",
    "Mode 校准数据图表": "Mode calibration chart", "命令参考": "Command reference",
    "中文": "Chinese",
})

# Keyed templates with placeholders (use trf()).
TRANSLATIONS.update({
    "maint.save_body": {
        "zh": "将用当前参数执行: param save {n}\n该分区原有内容会被覆盖(修复)。确认?",
        "en": "This runs param save {n}; the partition will be overwritten (repair). Continue?"},
    "maint.load_body": {
        "zh": "将执行: param load {n}\n当前内存中的参数会被分区内容覆盖。确认?",
        "en": "This runs param load {n}; current parameters will be overwritten. Continue?"},
    "maint.erase_body": {
        "zh": "将执行: param erase {n}\n该分区参数将全部丢失, 需重新校准/配置!\n确定要擦除分区 {n} ?",
        "en": "This runs param erase {n}; all parameters in the partition will be lost and recalibration will be needed!\nErase partition {n}?"},
    "maint.saved": {"zh": "已保存到分区 {n}", "en": "Saved to partition {n}"},
    "maint.loaded": {"zh": "已从分区 {n} 加载", "en": "Loaded from partition {n}"},
    "maint.erased": {"zh": "已擦除分区 {n}", "en": "Erased partition {n}"},
    "maint.dfu_body": {
        "zh": "将发送 serial_dfu, 控制台会话随即关闭。\n之后请用 nrfutil 在同一串口刷写无线电固件。\n确认进入?",
        "en": "serial_dfu will be sent and the console session closes.\nFlash the radio with nrfutil on the same port.\nEnter DFU?"},
    "maint.range_saved": {"zh": "已保存:\n{path}", "en": "Saved:\n{path}"},
    "maint.partition_saved": {"zh": "分区 {n} 原始数据已保存:\n{path}", "en": "Raw data of partition {n} saved to:\n{path}"},
    "maint.standby_sent": {"zh": "已发送{action}命令 ({time})", "en": "{action} command sent ({time})"},
    "maint.sleep": {"zh": "休眠", "en": "Sleep"},
    "maint.wake": {"zh": "唤醒", "en": "Wake"},
    "maint.range_empty": {"zh": "未获取到数据", "en": "No data received"},
    "maint.part_empty": {"zh": "未获取到分区 {n} 数据", "en": "No data received for partition {n}"},
    "expert.recapture_body": {
        "zh": "将用当前值覆盖基站 {sn} 的固化基线 ({count} 个参数)。\n此后的差异对比将以新基线为准。确认重设?",
        "en": "Overwrite the fixed baseline of station {sn} with current values ({count} parameters).\nFuture diffs will be against this new baseline. Continue?"},
    "expert.baseline_reset": {"zh": "基线已重设 (SN {sn})", "en": "Baseline reset (SN {sn})"},
    "journal.checking": {
        "zh": "履历校验: 正在读取...",
        "en": "History check: reading..."},
    "journal.check_skip": {
        "zh": "履历校验: 未取得序列号或计数, 本次跳过",
        "en": "History check: skipped (serial/counters unavailable)"},
    "journal.verdict_ok": {
        "zh": "履历校验通过",
        "en": "History check passed"},
    "journal.verdict_fail": {
        "zh": "履历校验未通过 ({codes})",
        "en": "History check failed ({codes})"},
    "journal.cur_unreadable": {
        "zh": "履历校验: 数据读取异常",
        "en": "History check: read error"},
    "expert.collecting": {"zh": "正在采集元数据 {i}/{total} ...", "en": "Collecting metadata {i}/{total} ..."},
    "expert.collected_done": {"zh": "元数据采集完成: {count} 个参数", "en": "Metadata collected: {count} parameters"},
    "expert.values_loaded": {"zh": "已加载 {count} 个参数值", "en": "Loaded {count} parameter values"},
    "genealogy.write_body": {
        "zh": "即将执行:\n\n{cmd}\n{data}\n{extra}\n确认写入?",
        "en": "About to run:\n\n{cmd}\n{data}\n{extra}\nConfirm write?"},
    "genealogy.zero_note": {
        "zh": "将把 {gid} 的槽位 (EEPROM 0x{addr:04X}, {size} 字节) 整体清零,\n恢复出厂空置显示。\n",
        "en": "Slot of {gid} (EEPROM 0x{addr:04X}, {size} bytes) will be zero-filled,\nrestoring the factory empty state.\n"},
    "genealogy.identity_warn": {
        "zh": "该字段是设备身份信息, 修改会影响设备识别!\n",
        "en": "This is a device identity field; changing it affects identification!\n"},
    "journal.reading": {
        "zh": "正在读取 EEPROM 履历记录区 (0x554-0xFC0, 2668 字节)...",
        "en": "Reading EEPROM history records (0x554-0xFC0, 2668 bytes)..."},
    "journal.read_failed": {
        "zh": "读取失败: 未获取到数据, 请确认设备已连接",
        "en": "Read failed: no data received; check the connection"},
    "journal.source": {
        "zh": "数据源: eeprom r 0x554 2668 | 记录按累计运行时间排序, 黄色行为最新一条",
        "en": "Source: eeprom r 0x554 2668 | Sorted by accumulated runtime; the yellow row is the newest"},
    "journal.summary": {
        "zh": "共 {count} 条记录 | 上电次数 {boots0} → {boots1} | 故障 {faults0} → {faults1} | 累计运行 {hours:.1f} h",
        "en": "{count} records | Boots {boots0} → {boots1} | Faults {faults0} → {faults1} | Runtime {hours:.1f} h"},
    "compare.title": {"zh": "参数备份对比", "en": "Parameter backup comparison"},
    "compare.header": {"zh": "对比: {a}  vs  {b}", "en": "Compare: {a}  vs  {b}"},
    "compare.file_a": {"zh": "文件 A: {name}", "en": "File A: {name}"},
    "compare.file_b": {"zh": "文件 B: {name}", "en": "File B: {name}"},
    "compare.summary": {"zh": "共 {total} 个参数，其中 {diff} 个差异", "en": "{total} parameters, {diff} differences"},
    "restore.win_params": {"zh": "正在恢复参数", "en": "Restoring parameters"},
    "restore.win_fcal": {"zh": "正在写入 FCAL", "en": "Writing FCAL"},
    "restore.fcal_writing": {"zh": "正在写入校准参数...", "en": "Writing calibration values..."},
    "restore.confirm": {"zh": "确认恢复参数", "en": "Confirm restore"},
    "restore.confirm_fcal": {"zh": "确认写入 FCAL 校准", "en": "Confirm FCAL write"},
    "restore.confirm_fcal2": {"zh": "二次确认", "en": "Second confirmation"},
    "restore.done_partial": {"zh": "恢复完成(部分失败)", "en": "Restore finished (partial failure)"},
    "restore.save_done_partial": {"zh": "写入完成(部分失败)", "en": "Write finished (partial failure)"},
    "restore.done_title": {"zh": "恢复完成", "en": "Restore complete"},
    "restore.write_title": {"zh": "写入完成", "en": "Write complete"},
    "restore.confirm_body": {
        "zh": "将向设备逐条写入 {count} 个参数, 最后执行 param save 保存到闪存。\n来源: {name}\n\n参数写错可能改变设备行为, 确认恢复?",
        "en": "Writes {count} parameters to the device, then runs param save.\nSource: {name}\n\nWrong values can change device behavior. Restore?"},
    "restore.fcal_confirm": {
        "zh": "即将写入 {count} 项出厂校准参数并保存到闪存:\n{name}\n\nFCAL 每台基站独一无二, 错误的校准值会导致定位失效!\n确认写入?",
        "en": "Writes {count} factory calibration values and saves to flash:\n{name}\n\nFCAL is unique per station; wrong values break tracking!\nContinue?"},
    "restore.fcal_confirm2": {"zh": "再次确认: 确实要覆盖设备出厂校准?", "en": "Confirm again: overwrite factory calibration?"},
    "restore.writing": {"zh": "正在写入参数 (0/{total})...", "en": "Writing parameters (0/{total})..."},
    "restore.done": {"zh": "已恢复 {ok} 个参数并保存到闪存", "en": "Restored {ok} parameters and saved to flash"},
    "restore.partial": {
        "zh": "成功 {ok} 项, 失败 {len} 项:\n{names}",
        "en": "Succeeded {ok}, failed {len}:\n{names}"},
    "restore.fcal_done": {"zh": "已写入 {ok} 项 FCAL 校准并保存到闪存", "en": "Wrote {ok} FCAL values and saved to flash"},
    "restore.title_params": {"zh": "正在恢复参数", "en": "Restoring parameters"},
    "restore.title_fcal": {"zh": "正在写入 FCAL", "en": "Writing FCAL"},
    "restore.failed": {"zh": "无法读取 JSON 文件:\n{error}", "en": "Could not read JSON file:\n{error}"},
    "restore.bad_format": {"zh": "备份文件格式不正确", "en": "Backup file format is invalid"},
    "restore.no_params": {"zh": "备份文件中没有可恢复的参数", "en": "No restorable parameters in the backup"},
    "restore.no_fcal": {"zh": "备份文件中没有 fcal 校准参数", "en": "No FCAL values in the backup"},
    "dump.title": {"zh": "Dump 相位误差趋势", "en": "Dump phase error trend"},
    "cal.mode_title": {"zh": "Mode 校准数据", "en": "Mode calibration data"},
    "cal.pwm_title": {"zh": "PWM 校准数据", "en": "PWM calibration data"},
})


_ZH_LOOKUP = None


def _lookup_table():
    global _ZH_LOOKUP
    if _ZH_LOOKUP is None:
        table = {}
        for resource in TRANSLATIONS.values():
            zh, en = resource.get("zh"), resource.get("en")
            if zh and en:
                table.setdefault(zh, en)
        table.update(TEXT_EN)
        _ZH_LOOKUP = table
    return _ZH_LOOKUP


def translate_text(text: str, language: str) -> str:
    if language == DEFAULT_LANGUAGE:
        return text
    table = _lookup_table()
    if text in table:
        return table[text]
    if text.endswith((":", "：")):
        base = text[:-1]
        if base in table:
            return table[base] + text[-1]
    return text


_current_language = DEFAULT_LANGUAGE


def set_current_language(language: str) -> None:
    global _current_language
    if language in LANGUAGE_NAMES:
        _current_language = language


def current_language() -> str:
    return _current_language


def tr_text(text: str) -> str:
    """Translate a Chinese UI string using the current language."""
    return translate_text(text, _current_language)


def trf(key: str, **values: Any) -> str:
    """Translate a keyed template with placeholders using the current language."""
    resource = TRANSLATIONS.get(key, {})
    text = resource.get(_current_language, resource.get(DEFAULT_LANGUAGE, key))
    try:
        return text.format(**values)
    except (KeyError, ValueError):
        return text


def apply_widget_language(root, language: str) -> None:
    """Translate existing widget text/headings/items, preserving original Chinese labels.

    Treeviews, menus and Text widgets are managed explicitly by their owners
    (tree panels re-render their items; the main window configures menus),
    so device data never passes through this generic pass.
    """
    import tkinter as tk
    from tkinter import ttk

    def visit(widget):
        if not isinstance(widget, (ttk.Treeview, tk.Menu, tk.Text)):
            try:
                original = getattr(widget, "_i18n_zh_text", None)
                if original is None:
                    original = widget.cget("text")
                    if isinstance(original, str):
                        setattr(widget, "_i18n_zh_text", original)
                if isinstance(original, str) and original:
                    value = translate_text(original, language)
                    if value != widget.cget("text"):
                        widget.configure(text=value)
            except (tk.TclError, AttributeError):
                pass

        for child in widget.winfo_children():
            visit(child)

    visit(root)


class Translator:
    def __init__(self, language: str | None = None):
        self.language = language if language in LANGUAGE_NAMES else load_language()

    def set_language(self, language: str) -> None:
        if language in LANGUAGE_NAMES:
            self.language = language
            save_language(language)

    def text(self, text: str) -> str:
        return translate_text(text, self.language)

    def __call__(self, key: str, **values: Any) -> str:
        resource = TRANSLATIONS.get(key, {})
        text = resource.get(self.language, resource.get(DEFAULT_LANGUAGE, key))
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text

def _config_path() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / "LighthouseTerminal" / "config.json"
    return Path.home() / ".lighthouse-terminal" / "config.json"


def load_language() -> str:
    try:
        value = json.loads(_config_path().read_text(encoding="utf-8")).get("language")
        return value if value in LANGUAGE_NAMES else DEFAULT_LANGUAGE
    except (OSError, ValueError, AttributeError):
        return DEFAULT_LANGUAGE


def save_language(language: str) -> None:
    if language not in LANGUAGE_NAMES:
        return
    try:
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"language": language}, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


class Translator:
    def __init__(self, language: str | None = None):
        self.language = language if language in LANGUAGE_NAMES else load_language()

    def set_language(self, language: str) -> None:
        if language in LANGUAGE_NAMES:
            self.language = language
            save_language(language)

    def text(self, text: str) -> str:
        return translate_text(text, self.language)

    def __call__(self, key: str, **values: Any) -> str:
        resource = TRANSLATIONS.get(key, {})
        text = resource.get(self.language, resource.get(DEFAULT_LANGUAGE, key))
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text
