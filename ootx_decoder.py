import tkinter as tk
from tkinter import ttk
import threading
import struct

OOTX_FRAME_SIZE = 56


class OotxDecoderPanel(tk.Frame):
    def __init__(self, parent, serial_manager, terminal, **kwargs):
        super().__init__(parent, **kwargs)
        self._serial = serial_manager
        self._terminal = terminal

        header = ttk.Label(self, text="OOTX Frame 443 bits (56 字节) — 三重视角解码",
                           font=("", 9, "bold"), foreground="#e5c07b")
        header.pack(anchor="w", padx=4, pady=(4, 2))

        table_frame = tk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self._tree = ttk.Treeview(table_frame,
            columns=("offset", "hex", "int16", "float32", "uint32"),
            show="tree headings")
        self._tree.heading("#0", text="#")
        self._tree.heading("offset", text="偏移")
        self._tree.heading("hex", text="Hex")
        self._tree.heading("int16", text="int16 LE (2B)")
        self._tree.heading("float32", text="float32 LE (4B)")
        self._tree.heading("uint32", text="uint32 LE hex (4B)")

        self._tree.column("#0", width=30, stretch=False)
        self._tree.column("offset", width=55, stretch=False, anchor="center")
        self._tree.column("hex", width=350, anchor="w")
        self._tree.column("int16", width=250, anchor="w")
        self._tree.column("float32", width=260, anchor="w")
        self._tree.column("uint32", width=200, anchor="w")

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        for off in range(0, OOTX_FRAME_SIZE, 16):
            end = min(off + 16, OOTX_FRAME_SIZE)
            off_label = f"{off:02X}-{(end-1):02X}"
            self._tree.insert("", tk.END, text=f"{off//16:02d}",
                              values=(off_label, "", "", "", ""))

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=4, pady=(4, 0))
        ttk.Button(btn_frame, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=(0, 8))

    def refresh(self):
        if not self._serial.is_connected():
            return

        def do_refresh():
            resp = self._serial.send_command("fpga", wait_response=True, timeout=3.0)
            from data_parser import parse_ootx_hexdump
            raw = parse_ootx_hexdump(resp)
            if len(raw) < 43:
                raw = b""
            self.after(0, lambda: self._render(raw))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _render(self, data: bytes):
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        if len(data) < 43:
            for off in range(0, OOTX_FRAME_SIZE, 16):
                end = min(off + 16, OOTX_FRAME_SIZE)
                self._tree.insert("", tk.END, text=f"{off//16:02d}",
                                  values=(f"{off:02X}-{(end-1):02X}", "", "", "", ""))
            return

        display_size = max(56, len(data))
        if display_size > len(data):
            data = data + b"\x00" * (display_size - len(data))

        for off in range(0, display_size, 16):
            end = min(off + 16, display_size)
            chunk = data[off:end]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            off_label = f"{off:02X}-{(end-1):02X}"

            int16_vals = []
            for p in range(0, len(chunk), 2):
                if p + 1 < len(chunk):
                    val = struct.unpack_from("<h", chunk, p)[0]
                    int16_vals.append(f"+{p:02X}:{val:>7d}")
            int16_str = "  ".join(int16_vals) if int16_vals else ""

            float32_vals = []
            for p in range(0, len(chunk), 4):
                if p + 3 < len(chunk):
                    try:
                        val = struct.unpack_from("<f", chunk, p)[0]
                        float32_vals.append(f"+{p:02X}:{val:>12.6f}")
                    except Exception:
                        float32_vals.append(f"+{p:02X}: (err)")
            float32_str = "  ".join(float32_vals) if float32_vals else ""

            uint32_vals = []
            for p in range(0, len(chunk), 4):
                if p + 3 < len(chunk):
                    val = struct.unpack_from("<I", chunk, p)[0]
                    uint32_vals.append(f"+{p:02X}: 0x{val:08X}")
                elif p + 1 < len(chunk):
                    val = struct.unpack_from("<H", chunk, p)[0]
                    uint32_vals.append(f"+{p:02X}: 0x{val:04X}(u16)")
            uint32_str = "  ".join(uint32_vals) if uint32_vals else ""

            self._tree.insert("", tk.END, text=f"{off//16:02d}",
                              values=(off_label, hex_str, int16_str, float32_str, uint32_str))

    def clear(self):
        self._render(b"")
