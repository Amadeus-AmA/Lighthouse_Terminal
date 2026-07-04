import tkinter as tk
from tkinter import Toplevel
import threading
import time
from collections import defaultdict

TIMEBASE_HZ = 48_000_000

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DumpViewer:
    def __init__(self, serial_manager):
        self._serial = serial_manager
        self._collecting = False
        self._data = []

    def collect_and_show(self, parent_tk):
        if self._collecting:
            return
        if not self._serial.is_connected():
            return

        def run():
            self._collecting = True
            self._data = []

            captured = []

            def temp_callback(text):
                captured.append(text)

            original_cb = self._serial._on_data_callback
            self._serial.set_data_callback(temp_callback)

            self._serial.send_command("dump", wait_response=True, timeout=2.0)

            start = time.time()
            while time.time() - start < 20.0:
                time.sleep(0.2)

            self._serial.send_command("dump", wait_response=True, timeout=2.0)
            time.sleep(0.5)

            self._serial.set_data_callback(original_cb)
            self._collecting = False

            from data_parser import parse_dump_line

            full_text = "".join(captured)
            base_time = None
            for line in full_text.split("\n"):
                parsed = parse_dump_line(line)
                if parsed is not None:
                    if base_time is None:
                        base_time = parsed["timestamp"]
                    rel_time = (parsed["timestamp"] - base_time) / TIMEBASE_HZ
                    self._data.append((rel_time, parsed["phase_error"]))

            parent_tk.after(0, lambda: self._show_chart())

        threading.Thread(target=run, daemon=True).start()

    def _show_chart(self):
        if not self._data:
            return

        window = Toplevel()
        window.title("Dump 相位误差趋势")
        window.geometry("900x400")

        fig = Figure(figsize=(10, 4), dpi=100)
        ax = fig.add_subplot(111)

        times = [d[0] for d in self._data]
        errors = [d[1] for d in self._data]

        ax.plot(times, errors, "#3498db", linewidth=1.2, label="Phase Error")
        ax.fill_between(times, errors, 0, alpha=0.15, color="#3498db")
        ax.axhline(y=0, color="#7f8c8d", linestyle="--", linewidth=0.8)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Phase Error")
        ax.set_title("Dump Phase Error Trend (20s)")
        ax.set_ylim(-50, 50)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
