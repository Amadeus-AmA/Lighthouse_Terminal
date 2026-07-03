# Lighthouse Terminal

Lighthouse 基站串口控制台 — 基于 Python Tkinter 的图形化调试与维修工具，用于 HTC Vive Lighthouse 定位基站的串口交互、参数管理、硬件状态监控和校准数据分析。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-orange)
---

## 功能特性

### 🔌 串口终端
- 扫描/选择串口
- 命令历史（上下箭头）和 Tab 键命令自动补全
- 暗色主题终端界面，区分发送/接收/系统消息颜色
- 40+ 内置快捷命令按钮和完整命令参考弹窗

### 📊 参数系统
- **参数树**：按 `sys / journal / timebase / carrier / laser / rotor / ootx / accel / fcal / led / log / stats` 前缀分组展示所有参数
- 带 `*` 标记的动态参数高亮为橙色
- **校准参数面板**：Axis 0 / Axis 1 并排对比 7 项 fcal 出厂校准值
- **Mode 切换器**：下拉选择 + 确认弹窗，一键切换基站运行配置模式（0-16）

### 🩺 硬件健康状态指示灯
从 `isl58303` 和 `fpga` 寄存器输出实时提取状态位，绿色/红色/蓝色圆点直观显示：

| 指示灯 | 数据来源 | 正常 |
|---|---|---|
| 激光供电正常 | isl58303 STATUS → POWER_GOOD | 🟢 |
| 激光芯片已使能 | isl58303 ENABLE → CHIP_EN | 🟢 |
| 电机使能 | fpga MOTOR_CTRL → ENABLE | 🟢 |
| 接收同步信号 | fpga IRQ → OPTO_FE / OPTO_RE | 🔵 |

### 📡 Radio 供电电压监控
从 `id` 命令输出的 `Radio Build` 行自动提取无线电模块实时电压（mV → V），低于 3.0V 提示供电异常。

### 📈 Dump 相位误差曲线图
- 采集 20 秒 `dump` 数据
- matplotlib 绘制相位误差 vs 时间折线图（±50 范围，0 参考线）
- 用于判断 PLL 稳定性、电机轴承老化

### 🔬 Mode 校准图表
- 一键采集 Mode 0-16 全部配置参数
- 三子图：Period / PWM / PLL Offset vs Mode

### 📦 参数备份与对比
- **备份参数**：一键保存当前 `param list` 为 JSON
- **备份 FCAL**：一键保存出厂校准参数到 `backup/` 目录，文件名为 `{SN}_fcal.json`
- **对比参数**：加载两份 JSON 备份，差异行红色高亮

### 🔍 硬件溯源
- `genealogy list` 解析为结构化面板
- 展示整机型号、主板 SN、激光模组 SN、电机总成 SN、机壳 SN、天线类型等
- 备用位（值为 `- -`）自动灰色淡化

---

## 运行环境

- Python 3.10+
- Windows / macOS / Linux
- 依赖：pyserial、matplotlib

## 安装

```bash
git clone https://github.com/yourname/lighthouse-terminal.git
cd lighthouse-terminal
pip install -r requirements.txt
python main.py
```

## 使用方法

1. **连接设备**：选择串口和波特率（默认 115200），点击"连接"
2. **自动识别**：连接后自动发送 `id` 命令，识别为 Lighthouse 基站后进入轮询模式
3. **快捷按钮**：底部两行按钮覆盖所有常用命令
4. **终端 Tab**：手动输入任意命令，支持 Tab 补全和历史记录
5. **参数树 / 校准参数**：自动从 `param list` 提取并分组展示
6. **硬件溯源**：自动获取设备各组件序列号与版本信息
7. **硬件指示灯**：左侧面板实时反映 isl58303 / fpga 硬件状态
8. **Dump 曲线**：切换到"Dump 曲线"Tab，点击"开始采集"等待 20 秒生成趋势图

## 项目结构

```
lighthouse-terminal/
├── main.py                  # 入口文件
├── serial_manager.py        # 串口管理（扫描、连接、后台收发）
├── gui_app.py               # 主窗口布局与模块集成
├── terminal_panel.py        # 终端显示 + 命令输入 + Tab 补全
├── status_panel.py          # 设备状态面板
├── hardware_panel.py        # 硬件健康状态指示灯
├── param_tree_panel.py      # 参数树 Tab（Treeview 前缀分组）
├── fcal_viewer.py           # 出厂校准参数面板（Axis 0/1 对比）
├── genealogy_panel.py       # 硬件溯源面板
├── calibration_viewer.py    # Mode / PWM 校准图表（matplotlib）
├── dump_viewer.py           # Dump 相位误差曲线图（20s 采集）
├── backup_compare.py        # 参数备份 JSON / 对比差异
├── data_parser.py           # 命令输出解析器（17 个解析函数）
├── requirements.txt         # 依赖清单
└── backup/                  # FCAL 备份输出目录（自动创建）
```

## 命令参考

Lighthouse 基站支持的所有命令均可在"命令参考"弹窗中查看（菜单 → 工具 → 命令参考），涵盖：

- **设备信息与系统控制**：`id` `reboot` `shutdown` `isp`
- **状态与统计**：`uptime` `freq` `dump` `perf`
- **参数系统**：`param list/get/set/default/save/load`
- **配置模式**：`mode <0-16>`
- **转子/电机**：`motor` `auto` `pll` `pwmscan` `pwmcal` `pwmopt` `pwmgain`
- **激光**：`isl58303`
- **FPGA**：`fpga`
- **日志/履历**：`genealogy list` `log`
- **无线/DTM**：`dtm` `radio` `nonce`
- **工厂/测试**：`factory` `crash`

## 截图

> 连接基站后截图待补充

## License


---

**适用设备**：HTC Vive Lighthouse 定位基站（1.0 / 2.0）
