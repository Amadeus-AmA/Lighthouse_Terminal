import tkinter as tk
from tkinter import ttk

from data_parser import format_life_ticks


def _format_life(v):
    return format_life_ticks(v)


def _format_radio_voltage(v):
    if isinstance(v, (int, float)):
        return f"{v:.3f} V"
    return str(v)


class StatusPanel(tk.LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="设备状态", **kwargs)

        self._labels = {}
        self._row = 0

        self._add_section("设备信息")
        self._add_field("ootx_model", "OOTX 型号")
        self._add_field("serial_number", "序列号")
        self._add_field("firmware_build", "固件版本")
        self._add_field("fpga_version", "FPGA 版本")
        self._add_field("radio_voltage", "Radio 电压")

        self._add_section("运行状态")
        self._add_field("sys_config", "当前 Mode")
        self._add_field("uptime", "运行时间")
        self._add_field("rotor_status", "转子状态")

        self._add_section("激光状态")
        self._add_field("laser_current", "激光电流")
        self._add_field("laser_power", "激光功率(设定)")
        self._add_field("laser_power_average", "激光功率(平均)")
        self._add_field("laser_bias", "激光偏置")
        self._add_field("laser_enable", "激光使能")

        self._add_section("设备履历 (Journal)")
        self._add_field("journal_boots", "总上电次数")
        self._add_field("journal_locks", "PLL 锁定次数")
        self._add_field("journal_spins", "电机总转数")
        self._add_field("journal_sweeps", "激光扫描总数")
        self._add_field("journal_faults", "历史故障次数")
        self._add_field("journal_life", "累计运行滴答")

    def _add_section(self, title: str):
        lbl = ttk.Label(self, text=title, font=("", 9, "bold"))
        lbl.grid(row=self._row, column=0, columnspan=2, sticky="w", pady=(6, 2), padx=4)
        self._row += 1

    def _add_field(self, key: str, label: str):
        name_lbl = ttk.Label(self, text=f"{label}:", width=16, anchor="e")
        name_lbl.grid(row=self._row, column=0, sticky="e", padx=(4, 2), pady=1)

        value_lbl = ttk.Label(self, text="--", width=28, anchor="w")
        value_lbl.grid(row=self._row, column=1, sticky="w", padx=(2, 4), pady=1)

        self._labels[key] = value_lbl
        self._row += 1

    def update_field(self, key: str, value):
        if key in self._labels:
            if value is not None:
                self._labels[key].configure(text=str(value))
            else:
                self._labels[key].configure(text="--")

    def update_all(self, data: dict):
        field_map = {
            "uptime": ("uptime_str", None),
            "laser_current": ("laser_current", lambda v: f"{v} mA" if isinstance(v, (int, float)) else v),
            "laser_power": ("laser_power", lambda v: f"{v:.1f} %" if isinstance(v, (int, float)) else v),
            "laser_power_average": ("laser_power_average", lambda v: f"{v:.1f} %" if isinstance(v, (int, float)) else v),
            "laser_bias": ("laser_bias", lambda v: f"{v}" if isinstance(v, (int, float)) else v),
            "laser_enable": ("laser_enable", None),
            "rotor_status": ("rotor_status", None),
            "ootx_model": ("ootx_model", None),
            "serial_number": ("serial_number", None),
            "firmware_build": ("firmware_build", None),
            "fpga_version": ("fpga_version", None),
            "sys_config": ("sys_config", None),
            "radio_voltage": ("radio_voltage_v", lambda v: _format_radio_voltage(v)),
            "journal_boots": ("journal_boots", None),
            "journal_locks": ("journal_locks", None),
            "journal_spins": ("journal_spins", lambda v: f"{v:,}" if isinstance(v, int) else v),
            "journal_sweeps": ("journal_sweeps", lambda v: f"{v:,}" if isinstance(v, int) else v),
            "journal_faults": ("journal_faults", None),
            "journal_life": ("journal_life", lambda v: _format_life(v) if isinstance(v, int) else v),
        }
        for ui_key, (data_key, fmt) in field_map.items():
            if data_key not in data:
                continue
            val = data[data_key]
            if val is not None and fmt:
                val = fmt(val)
            self.update_field(ui_key, val)

    def clear_all(self):
        for key in self._labels:
            self._labels[key].configure(text="--")
