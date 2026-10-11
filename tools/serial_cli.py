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
NOISE = "isl58303_reg_set"


def _clean(text: str) -> str:
    lines = [ln for ln in text.splitlines() if NOISE not in ln]
    return "\n".join(ln for ln in lines if ln.strip())


def _signature(text: str) -> str:
    body = _clean(text)
    body = body.replace(PROMPT, "").strip()
    # collapse whitespace so echoed input and formatting noise do not mask diffs
    return " ".join(body.split())


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
    # write_timeout 防 HALT 挂死: 固件断言后 USB 停止收发, 写会永久阻塞
    s = serial.Serial(name, baud, timeout=0.1, write_timeout=3.0)
    time.sleep(0.3)
    s.reset_input_buffer()
    # 探活: 写一个回车, 失败即固件未就绪
    try:
        s.write(b"\r")
        time.sleep(0.4)
        s.reset_input_buffer()
    except serial.SerialTimeoutException:
        s.close()
        sys.exit("firmware not responding (likely HALT) - power-cycle the base station")
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
    try:
        s.write((cmd + "\r").encode())
    except serial.SerialTimeoutException:
        sys.exit("firmware stopped responding (likely HALT) - power-cycle the base station")
    return read_available(s, wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["ports", "send", "tab", "batch", "dump", "probe"])
    ap.add_argument("target", nargs="?", default="")
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--wait", type=float, default=0.8)
    ap.add_argument("--data", default="", help="comma-separated candidates for probe")
    args = ap.parse_args()

    if args.action == "ports":
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("(none)")
        for p in ports:
            print(f"{p.device}  |  {p.description}  |  {p.hwid}")
        return

    if args.action == "probe" and not args.data:
        sys.exit("probe needs --data word1,word2,...")

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
            # clean the line editor first (executes an empty line -> fresh prompt)
            s.reset_input_buffer()
            s.write(b"\r")
            read_available(s, 0.4)
            # completion: type partial text, then Tab
            s.write(target.encode())
            time.sleep(0.15)
            s.write(b"\t")
            out = read_available(s, args.wait)
            print(out)
            s.write(b"\t")
            out2 = read_available(s, args.wait)
            if out2.strip():
                print("--- tab2 ---")
                print(out2)
            # cleanup: execute whatever is left, restore prompt
            s.write(b"\r")
            tail = read_available(s, 0.5)
            if tail.strip():
                print("--- cleanup ---")
                print(tail)
        elif args.action == "probe":
            # probe prefix + candidate words; a VALID subcommand responds without usage
            prefix = target
            candidates = [w.strip() for w in (args.data or "").split(",") if w.strip()]
            s.reset_input_buffer()
            s.write(b"\r")
            read_available(s, 0.4)
            baseline = send(s, prefix + " zzqqxx", args.wait)
            print("=== baseline (invalid) ===")
            print(_clean(baseline))
            hits = []
            for word in candidates:
                out = send(s, f"{prefix} {word}", args.wait)
                clean = _clean(out)
                if "usage:" not in clean.lower():
                    hits.append((word, clean))
                    print(f"### NON-USAGE RESPONSE: {prefix} {word}")
                    print(clean)
            print(f"=== probed {len(candidates)} candidates, {len(hits)} non-usage ===")
            for w, c in hits:
                print(f"  HIT: {prefix} {w}")
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
