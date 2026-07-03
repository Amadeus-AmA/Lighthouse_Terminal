import serial
import serial.tools.list_ports
import threading
import time
import queue


class SerialManager:
    def __init__(self):
        self._port = None
        self._running = False
        self._read_thread = None
        self._write_lock = threading.Lock()
        self._buffer = ""
        self._data_queue = queue.Queue()
        self._response_event = threading.Event()
        self._last_response = ""
        self._on_data_callback = None

    @staticmethod
    def list_ports():
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            result.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid
            })
        return result

    def set_data_callback(self, callback):
        self._on_data_callback = callback

    def connect(self, port_name: str, baudrate: int = 115200, timeout: float = 0.1) -> bool:
        try:
            self._port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            self._running = True
            self._buffer = ""
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            return True
        except serial.SerialException:
            return False

    def disconnect(self):
        self._running = False
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)
        if self._port and self._port.is_open:
            self._port.close()
        self._port = None

    def is_connected(self) -> bool:
        return self._port is not None and self._port.is_open

    def send_command(self, cmd: str, wait_response: bool = True, timeout: float = 3.0) -> str:
        if not self.is_connected():
            return ""
        with self._write_lock:
            self._response_event.clear()
            if not cmd.endswith("\r"):
                cmd += "\r"
            self._last_response = ""
            self._port.write(cmd.encode("utf-8"))
            if wait_response:
                if self._response_event.wait(timeout=timeout):
                    return self._last_response
                else:
                    return self._last_response
            return ""

    def send_raw(self, data: str):
        if self.is_connected():
            with self._write_lock:
                self._port.write(data.encode("utf-8"))

    def _read_loop(self):
        while self._running:
            try:
                if self._port and self._port.is_open and self._port.in_waiting > 0:
                    data = self._port.read(self._port.in_waiting)
                    text = data.decode("utf-8", errors="replace")
                    self._buffer += text
                    self._data_queue.put(text)
                    if self._on_data_callback:
                        self._on_data_callback(text)
                    if self._detect_prompt(self._buffer):
                        self._last_response = self._buffer
                        self._response_event.set()
                        self._buffer = ""
                else:
                    time.sleep(0.05)
            except (serial.SerialException, OSError):
                self._running = False
                break

    def _detect_prompt(self, text: str) -> bool:
        return text.rstrip().endswith("lhtx>") or text.rstrip().endswith("lhtx> ")

    def get_pending_data(self) -> str:
        result = []
        while not self._data_queue.empty():
            try:
                result.append(self._data_queue.get_nowait())
            except queue.Empty:
                break
        return "".join(result)
