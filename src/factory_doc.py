"""工厂校准只读说明窗口 (双语, 渲染时取当前语言)。"""
import tkinter as tk
from tkinter import ttk, Toplevel

from i18n import current_language, tr_text

FACTORY_DOC_ZH = """=== 工厂校准说明 (只读参考) ===

一、命令总览 (在终端页手动执行)
  factory save-cal                    将当前校准态写入 FACT 分区 (Par2)
  factory load-cal                    从 FACT 分区读回校准态
  factory erase-cal                   擦除 FACT 分区 (危险, 见第四节)
  factory laser-cal <mA1> [mA2] [gain]
  factory calibrate-apc               同 laser-cal (别名)
  factory laser-bias [limit]          自动测定激光阈值并设置偏置
  factory laser-test                  APC 开/关 平均功率对比
  factory laser-sweep <mA1> <mA2> [gain]
                                      电流 × 增益(0-7) 响应矩阵
  factory inspect                     光束检查模式
  factory led [ms] [b1] [b2] [b3]     LED 闪烁测试

二、laser-cal 两点光反馈标定流程
  1. 打开激光发射 (受 sys.emission_enable 门控)
  2. 增益自动扫描: 从 7 档往下试, 每档 100ms, 取第一个不饱和档位
  3. 测零功率偏移: 关激光记录光电二极管本底
  4. 设定激光电流 = mA1, 控制台提示
     "<电流>C: please enter measured power (mW):"
     此时需用外部功率计实测光功率并键入数值
  5. 若给定 mA2, 重复第 4 步测第二点
  6. 两点线性拟合, 结果写入 laser.pwr.m / laser.pwr.b1 / laser.pwr.b2
  7. 关激光恢复现场; 采样无效时报 ERROR: Invalid sensed values

三、出厂校准的完整顺序
  laser-bias      定阈值电流并设置偏置 DAC
  laser-cal       逐通道两点标定光反馈曲线
  laser-test      验证 APC 闭环
  laser-sweep     (可选) 输出特性矩阵存档
  save-cal        全部落盘到 FACT 分区

四、何时需要重跑
  仅当 FACT 分区损坏或空白 (param part 显示 Par2 CRC-BAD,
  或 fcal.0.* / fcal.1.* 参数丢失) 时才需要重新标定。
  日常使用无需、也不应执行任何会写 FACT 分区的命令。

五、安全须知
  * erase-cal / save-cal / laser-cal 都会改写 FACT 分区, 覆盖后
    激光功率特性改变, 没有备份时无法恢复原厂值。
  * 校准过程中激光会实际发光, 请勿直视光路。
  * 校准需要外部功率计配合, 键入的数值直接决定校准质量。

六、官方救援固件
  SteamVR 安装目录带有两个官方救援镜像 (本软件不附带, 需自行获取):
  * factory-reset-rescue  参数分区损坏时的修复环境
  * calibration-rescue    FACT 校准分区损坏/空白时的重跑环境
  可用「固件刷写 (救砖)」窗口刷入。注意: 救援固件没有 USB 串口
  (命令行走板载 UART), 刷入后串口静默、电机不转属正常; 完成修复
  后请刷回正式固件。
  有参数/FCAL 备份时, 优先使用「恢复参数备份 / 写入 FCAL 校准」
  直接恢复, 无需动用救援固件。
"""

FACTORY_DOC_EN = """=== Factory Calibration Guide (read-only reference) ===

1. Command overview (run manually in the terminal tab)
  factory save-cal                    Write current calibration to FACT partition (Par2)
  factory load-cal                    Load calibration back from FACT partition
  factory erase-cal                   Erase FACT partition (dangerous, see section 4)
  factory laser-cal <mA1> [mA2] [gain]
  factory calibrate-apc               Alias of laser-cal
  factory laser-bias [limit]          Auto-measure laser threshold and set bias
  factory laser-test                  Average power comparison, APC on/off
  factory laser-sweep <mA1> <mA2> [gain]
                                      Current x gain(0-7) response matrix
  factory inspect                     Beam inspection mode
  factory led [ms] [b1] [b2] [b3]     LED blink test

2. laser-cal two-point optical feedback calibration
  1. Enables laser emission (gated by sys.emission_enable)
  2. Auto gain scan: tries gain 7 downward, 100ms each, picks the first
     non-saturating stage
  3. Measures the zero-power offset (laser off, photodiode background)
  4. Sets laser current = mA1; the console prompts
     "<current>C: please enter measured power (mW):"
     - you must measure the optical power with an external power meter
       and type the value in
  5. If mA2 is given, step 4 repeats for the second point
  6. Two-point linear fit; the result is stored into
     laser.pwr.m / laser.pwr.b1 / laser.pwr.b2
  7. Laser off, state restored; invalid samples report
     ERROR: Invalid sensed values

3. Full factory calibration sequence
  laser-bias      Determine threshold current and set the bias DAC
  laser-cal       Two-point feedback calibration per channel
  laser-test      Verify the APC closed loop
  laser-sweep     (optional) response matrix for the record
  save-cal        Commit everything to the FACT partition

4. When a re-run is needed
  Only when the FACT partition is damaged or blank (param part shows
  Par2 CRC-BAD, or the fcal.0.* / fcal.1.* parameters are missing).
  Normal operation never needs - and should never run - any command
  that writes the FACT partition.

5. Safety notes
  * erase-cal / save-cal / laser-cal all rewrite the FACT partition;
    once overwritten the laser power characteristics change and the
    original factory values cannot be restored without a backup.
  * The laser actually emits during calibration; never look into the beam.
  * Calibration requires an external power meter; the values you type
    directly determine calibration quality.

6. Official rescue firmware
  The SteamVR install directory ships two official rescue images
  (not bundled with this software; obtain them yourself):
  * factory-reset-rescue  repair environment for damaged parameter partitions
  * calibration-rescue    re-run environment for a damaged/blank FACT partition
  They can be flashed with the "Firmware flash (rescue)" window. Note:
  the rescue firmware has no USB serial console (its command line runs
  on the board UART only) - after flashing, a silent serial port and a
  non-spinning rotor are normal. Flash the regular firmware back when
  the repair is done.
  If you have parameter/FCAL backups, prefer "Restore parameter backup"
  and "Restore FCAL calibration" directly - no need for the rescue
  firmware at all.
"""


def open_factory_doc(parent):
    win = Toplevel(parent)
    win.title(tr_text("工厂校准说明 (只读)"))
    win.geometry("880x640")
    win.transient(parent)

    tip = tk.Label(win, text=tr_text("本页为只读说明, 命令需在终端页手动执行, 执行前请确认理解每个步骤。"),
                   fg="#e67e22", anchor="w", justify=tk.LEFT)
    tip.pack(fill=tk.X, padx=8, pady=(8, 2))

    body = tk.Frame(win)
    body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 4))
    text = tk.Text(body, wrap=tk.NONE, state="disabled",
                   bg="#fbfbf7", font=("Consolas", 10))
    ys = ttk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
    xs = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=text.xview)
    ys.pack(side=tk.RIGHT, fill=tk.Y)
    xs.pack(side=tk.BOTTOM, fill=tk.X)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)

    content = FACTORY_DOC_EN if current_language() == "en" else FACTORY_DOC_ZH
    text.configure(state="normal")
    text.insert("1.0", content)
    text.configure(state="disabled")

    ttk.Button(win, text=tr_text("关闭"), command=win.destroy).pack(pady=(0, 8))
    return win
