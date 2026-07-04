import re


def parse_id_output(text: str) -> dict:
    result = {}
    patterns = {
        "device_name": r"Device Name:\s*(.+)",
        "serial_number": r"Serial Number:\s*(.+)",
        "firmware_build": r"Firmware Build:\s*(.+)",
        "radio_build": r"Radio Build:\s*(.+)",
        "fpga_version": r"FPGA Code Version:\s*(\d+)",
        "ootx_model": r"OOTX Model:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            result[key] = m.group(1).strip()

    radio_raw = result.get("radio_build", "")
    m = re.search(r"HW\s+[\d.]+\s*,\s*(\d+)\s*mV", radio_raw)
    if m:
        voltage_mv = int(m.group(1))
        result["radio_voltage_mv"] = voltage_mv
        result["radio_voltage_v"] = voltage_mv / 1000.0
    return result


def parse_uptime_output(text: str) -> dict:
    result = {}
    m = re.search(r"(\d+)\s*seconds", text)
    if m:
        seconds = int(m.group(1))
        result["uptime_seconds"] = seconds
        result["uptime_str"] = format_uptime(seconds)
        return result
    m = re.search(r"(\d+)\s*day\s+(\d+):(\d+):([\d.]+)", text)
    if m:
        days = int(m.group(1))
        hours = int(m.group(2))
        minutes = int(m.group(3))
        seconds = int(float(m.group(4)))
        total = days * 86400 + hours * 3600 + minutes * 60 + seconds
        result["uptime_seconds"] = total
        result["uptime_str"] = format_uptime(total)
    return result


def parse_freq_output(text: str) -> dict:
    result = {}
    m = re.search(r"Rotor Frequency:\s*([\d.]+)\s*Hz", text)
    if m:
        result["rotor_freq"] = float(m.group(1))
    return result


def parse_laser_status(text: str) -> dict:
    result = {}
    patterns = {
        "laser_current": r"laser\.current\s+([\d.]+)",
        "laser_power": r"laser\.pwr\s+([\d.]+)",
        "laser_power_detected": r"laser\.pwr\.detected\s+([\d.]+)",
        "laser_power_average": r"laser\.pwr\.average\s+([\d.]+)",
        "laser_bias": r"laser\.bias\s+([\d.]+)",
        "laser_enable": r"laser\.enable\s+(\w+)",
        "laser_apc": r"laser\.apc\s+(\w+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def parse_rotor_status(text: str) -> dict:
    result = {}
    patterns = {
        "rotor_status": r"rotor\.status\s+(\w+)",
        "rotor_pwm": r"rotor\.pwm\s+([\d.]+)",
        "rotor_pwm_auto": r"rotor\.pwm\.auto\s+(\w+)",
        "rotor_pll_offset": r"rotor\.pll\.offset\s+([\d.]+)",
        "rotor_enable": r"rotor\.enable\s+(\w+)",
        "timebase_period": r"timebase\.period\s+([\d.]+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def parse_mode_output(text: str) -> list:
    result = []
    pattern = (
        r"timebase\.period\s*=\s*(\d+)\s*\n"
        r"rotor\.pwm\s*=\s*(\d+)\s*\n"
        r"rotor\.pll\.offset\s*=\s*(\d+)"
    )
    for m in re.finditer(pattern, text):
        result.append({
            "period": int(m.group(1)),
            "pwm": int(m.group(2)),
            "offset": int(m.group(3)),
        })
    return result


def parse_param_uptime(text: str) -> dict:
    result = {}
    m = re.search(r"sys\.uptime\s+(\d+)", text)
    if m:
        seconds = int(m.group(1))
        result["uptime_seconds"] = seconds
        result["uptime_str"] = format_uptime(seconds)
    return result


def parse_param_list(text: str) -> dict:
    result = {}
    for line in text.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 2:
            key = parts[0]
            value = parts[1]
            try:
                result[key] = float(value)
            except ValueError:
                result[key] = value
    return result


def parse_sys_config(text: str) -> dict:
    result = {}
    m = re.search(r"sys\.config\s+(\d+)", text)
    if m:
        result["sys_config"] = int(m.group(1))
    return result


def parse_journal(text: str) -> dict:
    result = {}
    patterns = {
        "journal_boots": r"journal\.boots\s+(\d+)",
        "journal_locks": r"journal\.locks\s+(\d+)",
        "journal_spins": r"journal\.spins\s+(\d+)",
        "journal_sweeps": r"journal\.sweeps\s+(\d+)",
        "journal_faults": r"journal\.faults\s+(\d+)",
        "journal_life": r"journal\.life\s+(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            try:
                result[key] = int(m.group(1))
            except ValueError:
                result[key] = m.group(1)
    return result


def parse_fcal(text: str) -> dict:
    result = {}
    patterns = {
        "fcal_0_tilt": r"fcal\.0\.tilt\s+([\d.\-]+)",
        "fcal_0_phase": r"fcal\.0\.phase\s+([\d.\-]+)",
        "fcal_0_curve": r"fcal\.0\.curve\s+([\d.\-]+)",
        "fcal_0_gibphase": r"fcal\.0\.gibphase\s+([\d.\-]+)",
        "fcal_0_gibmag": r"fcal\.0\.gibmag\s+([\d.\-]+)",
        "fcal_0_ogeephase": r"fcal\.0\.ogeephase\s+([\d.\-]+)",
        "fcal_0_ogeemag": r"fcal\.0\.ogeemag\s+([\d.\-]+)",
        "fcal_1_tilt": r"fcal\.1\.tilt\s+([\d.\-]+)",
        "fcal_1_phase": r"fcal\.1\.phase\s+([\d.\-]+)",
        "fcal_1_curve": r"fcal\.1\.curve\s+([\d.\-]+)",
        "fcal_1_gibphase": r"fcal\.1\.gibphase\s+([\d.\-]+)",
        "fcal_1_gibmag": r"fcal\.1\.gibmag\s+([\d.\-]+)",
        "fcal_1_ogeephase": r"fcal\.1\.ogeephase\s+([\d.\-]+)",
        "fcal_1_ogeemag": r"fcal\.1\.ogeemag\s+([\d.\-]+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def parse_accel(text: str) -> dict:
    result = {}
    patterns = {
        "accel_x": r"accel\.x\s+([\d.\-]+)",
        "accel_y": r"accel\.y\s+([\d.\-]+)",
        "accel_z": r"accel\.z\s+([\d.\-]+)",
        "accel_magnitude": r"accel\.magnitude\s+([\d.\-]+)",
        "accel_is_gravity": r"accel\.is_gravity\s+(\w+)",
        "accel_temp": r"accel\.temp\s+([\d.\-]+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def parse_carrier(text: str) -> dict:
    result = {}
    patterns = {
        "carrier_enable": r"carrier\.enable\s+(\w+)",
        "carrier_divider": r"carrier\.divider\s+(\d+)",
        "carrier_poly_0": r"carrier\.poly\.0\s+(\d+)",
        "carrier_poly_1": r"carrier\.poly\.1\s+(\d+)",
        "carrier_poly_f": r"carrier\.poly\.f\s+(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def parse_timebase(text: str) -> dict:
    result = {}
    patterns = {
        "timebase_period": r"timebase\.period\s+([\d.]+)",
        "timebase_locked": r"timebase\.locked\s+(\w+)",
        "timebase_mode": r"timebase\.mode\s+(\S+)",
        "timebase_offset": r"timebase\.offset\s+([\d.\-]+)",
        "timebase_current": r"timebase\.current\s+([\d.]+)",
        "timebase_tdm": r"timebase\.tdm\s+(\w+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def parse_ootx(text: str) -> dict:
    result = {}
    patterns = {
        "ootx_enable": r"ootx\.enable\s+(\w+)",
        "ootx_lock_required": r"ootx\.lock_required\s+(\w+)",
        "ootx_model_override": r"ootx\.model_override\s+(\d+)",
        "ootx_nonce": r"ootx\.nonce\s+(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            val = m.group(1).strip()
            try:
                result[key] = float(val)
            except ValueError:
                result[key] = val
    return result


def format_uptime(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"


def format_life_ticks(ticks: int) -> str:
    """48MHz 时钟滴答 → 可读时间"""
    seconds = ticks / 48_000_000
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def parse_isl58303(text: str) -> dict:
    result = {}
    m = re.search(r'POWER_GOOD:(\d)', text)
    if m:
        result["power_good"] = int(m.group(1))
    m = re.search(r'CHIP_EN:(\d)', text)
    if m:
        result["chip_en"] = int(m.group(1))
    return result


def parse_fpga(text: str) -> dict:
    result = {}
    m = re.search(r'MOTOR_STATUS:\s*0x([0-9A-Fa-f]+)\s*\(\s*([^)]*)\)', text)
    if m:
        result["motor_status_hex"] = m.group(1)
        result["motor_status_desc"] = m.group(2).strip()
        val = int(m.group(1), 16)
        result["motor_fg"] = bool(val & 0x01)
        result["motor_spinning"] = bool(val & 0x02)
    m = re.search(r'MOTOR_CTRL:\s*0x([0-9A-Fa-f]+)\s*\(\s*([^)]*)\)', text)
    if m:
        result["motor_ctrl_hex"] = m.group(1)
        result["motor_ctrl_desc"] = m.group(2).strip()
        val = int(m.group(1), 16)
        result["motor_enable"] = bool(val & 0x01)
    m = re.search(r'LASER_STATUS:\s*0x([0-9A-Fa-f]+)\s*\(\s*([^)]*)\)', text)
    if m:
        result["laser_status_hex"] = m.group(1)
        result["laser_status_desc"] = m.group(2).strip()
        val = int(m.group(1), 16)
        result["laser_mcu_en"] = bool(val & 0x01)
        result["laser_hw_enable"] = bool(val & 0x02)
    m = re.search(r'IRQ:\s*0x([0-9A-Fa-f]+)\s*\(\s*([^)]*)\)', text)
    if m:
        result["irq_hex"] = m.group(1)
        result["irq_desc"] = m.group(2).strip()
        val = int(m.group(1), 16)
        result["irq_opto_fe"] = bool(val & 0x10)
        result["irq_opto_re"] = bool(val & 0x20)
    return result


def parse_genealogy_list(text: str) -> dict:
    result = {}
    for line in text.split("\n"):
        m = re.match(r'%GENE\s+(\w+)\s+([\w\s]+?)\s{2,}(.+)', line)
        if m:
            key = m.group(1)
            category = m.group(2).strip()
            value = m.group(3).strip()
            result[key] = {"category": category, "value": value}
    return result


def parse_dump_line(line: str) -> dict:
    parts = line.strip().split()
    if len(parts) == 5 and parts[0] == "%R":
        try:
            return {
                "timestamp": float(parts[1]),
                "target_pwm": float(parts[2]),
                "actual_pwm": float(parts[3]),
                "phase_error": float(parts[4]),
            }
        except ValueError:
            pass
    return None


def parse_ootx_hexdump(text: str) -> bytes:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        if "OOTX frame" in line:
            start_idx = i + 1
            break
    all_bytes = []
    for line in lines[start_idx:]:
        m = re.match(r'^[0-9A-Fa-f]{8}:\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})+)', line)
        if m:
            for h in m.group(1).split():
                all_bytes.append(int(h, 16))
    if len(all_bytes) >= 43:
        return bytes(all_bytes)
    return b""
