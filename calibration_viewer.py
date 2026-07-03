import tkinter as tk
from tkinter import Toplevel
import re

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class CalibrationViewer:
    def __init__(self, serial_manager):
        self._serial = serial_manager
        self._window = None
        self._canvas = None

    def show_mode_chart(self):
        from data_parser import parse_mode_output

        self._serial.send_command("\r", wait_response=True, timeout=1.0)
        raw = ""
        for i in range(17):
            resp = self._serial.send_command(f"mode {i}", wait_response=True, timeout=2.0)
            raw += resp + "\n"

        mode_data = parse_mode_output(raw)

        if not mode_data:
            return

        if self._window is None or not Toplevel.winfo_exists(self._window):
            self._window = Toplevel()
            self._window.title("Mode 校准数据")
            self._window.geometry("800x500")

        for widget in self._window.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(8, 5), dpi=100)
        modes = list(range(len(mode_data)))
        periods = [d["period"] for d in mode_data]
        pwms = [d["pwm"] for d in mode_data]
        offsets = [d["offset"] for d in mode_data]

        ax1 = fig.add_subplot(311)
        ax1.plot(modes, periods, "b-o", markersize=4)
        ax1.set_ylabel("Period")
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(312)
        ax2.plot(modes, pwms, "r-o", markersize=4)
        ax2.set_ylabel("PWM")
        ax2.grid(True, alpha=0.3)

        ax3 = fig.add_subplot(313)
        ax3.plot(modes, offsets, "g-o", markersize=4)
        ax3.set_xlabel("Mode")
        ax3.set_ylabel("PLL Offset")
        ax3.grid(True, alpha=0.3)

        fig.tight_layout()

        self._canvas = FigureCanvasTkAgg(fig, master=self._window)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def show_pwm_scan_chart(self, raw_output: str):
        data_points = []
        for line in raw_output.strip().split("\n"):
            m = re.search(r"(\d+)\s+([\d.]+)", line)
            if m:
                data_points.append((int(m.group(1)), float(m.group(2))))

        if not data_points:
            return

        if self._window is None or not Toplevel.winfo_exists(self._window):
            self._window = Toplevel()
            self._window.title("PWM 校准数据")
            self._window.geometry("600x400")

        for widget in self._window.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(6, 4), dpi=100)
        x_vals = [d[0] for d in data_points]
        y_vals = [d[1] for d in data_points]

        ax = fig.add_subplot(111)
        ax.plot(x_vals, y_vals, "b-o", markersize=3)
        ax.set_xlabel("PWM Value")
        ax.set_ylabel("Measurement")
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        self._canvas = FigureCanvasTkAgg(fig, master=self._window)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
