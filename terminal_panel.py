import tkinter as tk
from tkinter import scrolledtext, ttk


class TerminalPanel(tk.Frame):
    def __init__(self, parent, on_command_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_command_callback = on_command_callback
        self._command_history = []
        self._history_index = -1

        self.output_text = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, state="disabled",
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#d4d4d4",
            font=("Consolas", 10)
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(2, 0))

        input_frame = tk.Frame(self)
        input_frame.pack(fill=tk.X, padx=2, pady=(2, 2))

        self.cmd_entry = tk.Entry(
            input_frame, bg="#2d2d2d", fg="#d4d4d4",
            insertbackground="#d4d4d4",
            font=("Consolas", 10)
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", self._on_send)
        self.cmd_entry.bind("<Up>", self._on_history_up)
        self.cmd_entry.bind("<Down>", self._on_history_down)

        send_btn = ttk.Button(input_frame, text="发送", command=self._on_send_click)
        send_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self.cmd_entry.bind("<Tab>", self._on_tab)

        self._all_commands = [
            "id", "reboot", "shutdown", "isp", "uptime", "freq", "stats",
            "clear", "dump", "perf", "param list", "param info", "param get",
            "param set", "param default", "param default-all", "param load",
            "param save", "param part", "param erase", "param raw",
            "mode", "genealogy", "motor", "auto", "autodebug", "pll",
            "plldebug", "pwmscan", "pwmcal", "pwmopt", "pwmgain", "isl58303",
            "lis2dh", "fpga", "crash", "factory", "ram", "eeprom",
            "led", "log", "dtm", "dtm_pwr", "serial_dfu", "nonce", "radio",
        ]
        self._tab_match_index = -1
        self._tab_prefix = ""

        self._init_tags()

    def _init_tags(self):
        self.output_text.tag_config("sent", foreground="#569cd6")
        self.output_text.tag_config("system", foreground="#6a9955")
        self.output_text.tag_config("error", foreground="#f44747")

    def append_output(self, text: str, tag: str = None):
        self.output_text.configure(state="normal")
        if tag:
            self.output_text.insert(tk.END, text, tag)
        else:
            self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.configure(state="disabled")

    def append_sent(self, text: str):
        self.append_output(f">>> {text}\n", "sent")

    def append_received(self, text: str):
        self.append_output(text)

    def append_system(self, text: str):
        self.append_output(f"[{text}]\n", "system")

    def append_error(self, text: str):
        self.append_output(f"[错误] {text}\n", "error")

    def _on_send(self, event=None):
        cmd = self.cmd_entry.get().strip()
        if cmd:
            if not self._command_history or self._command_history[-1] != cmd:
                self._command_history.append(cmd)
            self._history_index = len(self._command_history)
            self.append_sent(cmd)
            self.cmd_entry.delete(0, tk.END)
            if self._on_command_callback:
                self._on_command_callback(cmd)

    def _on_send_click(self):
        self._on_send()

    def _on_history_up(self, event=None):
        if not self._command_history:
            return
        if self._history_index > 0:
            self._history_index -= 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self._command_history[self._history_index])

    def _on_history_down(self, event=None):
        if self._history_index < len(self._command_history) - 1:
            self._history_index += 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self._command_history[self._history_index])
        else:
            self._history_index = len(self._command_history)
            self.cmd_entry.delete(0, tk.END)

    def _on_tab(self, event=None):
        prefix = self.cmd_entry.get().strip()

        if not prefix or prefix != self._tab_prefix:
            self._tab_prefix = prefix
            self._tab_match_index = -1

        matches = [c for c in self._all_commands if c.startswith(prefix)]
        if not matches:
            return "break"

        self._tab_match_index = (self._tab_match_index + 1) % len(matches)
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, matches[self._tab_match_index])
        return "break"
