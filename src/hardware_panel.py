import tkinter as tk
from tkinter import ttk

GREEN = "#27ae60"
RED = "#e74c3c"
BLUE = "#3498db"
GRAY = "#7f8c8d"


class HardwarePanel(tk.LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="硬件健康状态", **kwargs)

        self._indicators = {}
        indicator_width = 20
        indicator_height = 20

        indicators = [
            ("power_good", "激光供电正常"),
            ("chip_en", "激光芯片已使能"),
            ("motor_enable", "电机使能"),
            ("sync_signal", "接收同步信号"),
        ]

        for key, label in indicators:
            row = tk.Frame(self)
            row.pack(fill=tk.X, padx=8, pady=3)

            canvas = tk.Canvas(row, width=indicator_width, height=indicator_height,
                               bg=self.cget("bg") if self.cget("bg") else "#f0f0f0",
                               highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=(0, 8))

            desc_lbl = tk.Label(row, text=label, anchor="w", font=("", 9))
            desc_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self._indicators[key] = {"canvas": canvas, "label": desc_lbl}

        self.clear_all()

    def _set_indicator(self, key: str, color: str):
        if key in self._indicators:
            canvas = self._indicators[key]["canvas"]
            canvas.delete("all")
            w = canvas.winfo_reqwidth()
            h = canvas.winfo_reqheight()
            if w <= 2 or h <= 2:
                w, h = 20, 20
            canvas.create_oval(2, 2, w - 2, h - 2, fill=color, outline=color)

    def update_from_isl58303(self, data: dict):
        if not data:
            return
        power_good = data.get("power_good")
        chip_en = data.get("chip_en")

        if power_good is not None:
            self._set_indicator("power_good", GREEN if power_good == 1 else RED)
        if chip_en is not None:
            self._set_indicator("chip_en", GREEN if chip_en == 1 else RED)

    def update_from_fpga(self, data: dict):
        if not data:
            return

        motor_enable = data.get("motor_enable")
        irq_opto_fe = data.get("irq_opto_fe")
        irq_opto_re = data.get("irq_opto_re")

        if motor_enable is not None:
            self._set_indicator("motor_enable", GREEN if motor_enable else RED)

        if irq_opto_fe is not None and irq_opto_re is not None:
            triggered = irq_opto_fe or irq_opto_re
            self._set_indicator("sync_signal", BLUE if triggered else GRAY)

    def clear_all(self):
        for key in self._indicators:
            self._set_indicator(key, GRAY)
