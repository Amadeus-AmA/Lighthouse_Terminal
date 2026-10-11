"""Direct serial probe for the Lighthouse base station console.

Usage:
  python tools/serial_cli.py ports                 list COM ports
  python tools/serial_cli.py send "<cmd>"          send one command, print response
  python tools/serial_cli.py tab "<partial>"       send partial command + Tab (completion)
  python tools/serial_cli.py batch <file>          run commands (one per line), save transcript
  python tools/serial_cli.py dump <file>           read full EEPROM 0x000-0xFC0 to file

Options:
  --port COMx        serial port (default: auto-pick the only/first USB serial port)
  --baud 115200      baud rate
  --wait 0.8         seconds to wait for response after each command
"""
import argparse
import sys
import time

import serial
import serial.tools.list_ports

PROMPT = "lhtx>"
BLOCKED = ("crash", "param erase")  # permanent-damage guards


def pick_port(name=None):
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("no serial ports found")
    if name:
        return name
    if len(ports) == 1:
        return ports[0].device
    print("multiple ports, pick one with --port:")
    for p in ports:
        print(f"  {p.device}  {p.description}")
    sys.exit(1)


def open_port(name, baud):
    s = serial.Serial(name, baud, timeout=0.1)
    time.sleep(0.3)
    s.reset_input_buffer()
    return s


def read_available(s, wait):
    time.sleep(wait)
    data = b""
    deadline = time.time() + wait + 2.0
    while time.time() < deadline:
        chunk = s.read(s.in_waiting or 1)
        if chunk:
            data += chunk
            deadline = time.time() + 0.3  # keep reading while data flows
        else:
            break
    return data.decode("utf-8", errors="replace")


def send(s, cmd, wait):
    s.reset_input_buffer()
    s.write((cmd + "\r").encode())
    return read_available(s, wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["ports", "send", "tab", "batch", "dump"])
    ap.add_argument("target", nargs="?", default="")
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--wait", type=float, default=0.8)
    args = ap.parse_args()

    if args.action == "ports":
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("(none)")
        for p in ports:
            print(f"{p.device}  |  {p.description}  |  {p.hwid}")
        return

    target = args.target
    if args.action in ("send", "tab") and target:
        low = target.lower()
        if any(b in low for b in BLOCKED):
            sys.exit(f"blocked for safety: {target} (override by editing tools/serial_cli.py)")

    port = pick_port(args.port)
    s = open_port(port, args.baud)
    try:
        if args.action == "send":
            print(send(s, target, args.wait))
        elif args.action == "tab":
            # completion: no newline, then Tab, read whatever comes back
            s.reset_input_buffer()
            s.write(target.encode())
            time.sleep(0.2)
            s.write(b"\t")
            out = read_available(s, args.wait)
            print(out)
            # second Tab often lists next candidates
            s.write(b"\t")
            out2 = read_available(s, args.wait)
            if out2.strip():
                print("--- tab2 ---")
                print(out2)
        elif args.action == "batch":
            with open(target, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
            transcript = []
            for cmd in lines:
                low = cmd.lower()
                if any(b in low for b in BLOCKED):
                    print(f"### skipped (blocked): {cmd}")
                    transcript.append(f"### skipped (blocked): {cmd}")
                    continue
                out = send(s, cmd, args.wait)
                print(f">>> {cmd}")
                print(out)
                transcript.append(f">>> {cmd}\n{out}")
            with open("transcript.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(transcript))
            print(f"### transcript saved: transcript.txt ({len(lines)} commands)")
        elif args.action == "dump":
            out = send(s, f"eeprom r 0x0 4032", wait=3.0)
            with open(target or "eeprom_full.txt", "w", encoding="utf-8") as f:
                f.write(out)
            print(f"### saved {len(out)} chars to {target or 'eeprom_full.txt'}")
    finally:
        s.close()


if __name__ == "__main__":
    main()
