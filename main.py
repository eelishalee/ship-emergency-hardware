"""
MDTS — Maritime Digital Triage System
PyQt6 · 1024×600  (7-inch rugged tablet)
"""
import sys, math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QDialog, QSizePolicy,
)
from PyQt6.QtCore  import Qt, QTimer, QDateTime, QPointF, QRectF
from PyQt6.QtGui   import (
    QFont, QColor, QPainter, QPen, QLinearGradient,
    QBrush, QPainterPath, QImage, QPixmap, QRadialGradient,
)

W, H = 1024, 600

# ── 팔레트 ─────────────────────────────────────────────────
BG      = "#04090f"   # 카메라 패널 내부색 통일
PANEL   = "#080f1c"
PANEL2  = "#0c1828"
BORD    = "#16293f"
BORD2   = "#0a1e30"
ACCENT  = "#0ea5e9"
ACCENT2 = "#38bdf8"
RED     = "#ef4444"
RED2    = "#dc2626"
GREEN   = "#22c55e"
YELLOW  = "#eab308"
ORANGE  = "#f97316"
PURPLE  = "#a855f7"
TEAL    = "#14b8a6"
TEXT    = "#e2e8f0"
DIM     = "#4a6080"
DIM2    = "#2a4060"

FONT    = "Malgun Gothic"


# ══════════════════════════════════════════════════════════
#  ECG 파형 위젯
# ══════════════════════════════════════════════════════════
class EcgWidget(QWidget):
    """Scrolling ECG waveform drawn with QPainter."""

    _CYCLE = []   # 공유 PQRST 샘플

    @classmethod
    def _build_cycle(cls, n=120):
        if cls._CYCLE:
            return
        pts = []
        for i in range(n):
            t = i / n
            if   t < 0.10: y = 0.0
            elif t < 0.16: y = 0.18 * math.sin((t - 0.10) / 0.06 * math.pi)
            elif t < 0.28: y = 0.0
            elif t < 0.31: y = -0.12 * (t - 0.28) / 0.03
            elif t < 0.34: y = -0.12 + 1.12 * (t - 0.31) / 0.03
            elif t < 0.38: y = 1.0  - 1.20 * (t - 0.34) / 0.04
            elif t < 0.42: y = -0.20 + 0.20 * (t - 0.38) / 0.04
            elif t < 0.55: y = 0.0
            elif t < 0.70: y = 0.30 * math.sin((t - 0.55) / 0.15 * math.pi)
            else:           y = 0.0
            pts.append(y)
        cls._CYCLE = pts

    def __init__(self, color=GREEN, bpm=72, parent=None):
        super().__init__(parent)
        self._build_cycle()
        self._color = QColor(color)
        self._bpm   = bpm
        self._phase = 0.0
        self.setMinimumHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def set_bpm(self, bpm):
        self._bpm = max(1, bpm)

    def set_color(self, color: str):
        self._color = QColor(color)

    def _tick(self):
        # phase advances proportional to BPM
        self._phase = (self._phase + self._bpm / 60 * 0.03) % 1.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h    = self.width(), self.height()
        margin  = 4
        dw      = w - 2 * margin
        dh      = h - 2 * margin
        n       = len(self._CYCLE)

        # glow pen (wide, dim)
        glow = QPen(QColor(self._color.red(), self._color.green(),
                           self._color.blue(), 55))
        glow.setWidth(4)
        p.setPen(glow)
        path_g = QPainterPath()
        first = True
        for i in range(dw):
            phase = (self._phase + i / dw) % 1.0
            idx   = int(phase * n) % n
            y_val = self._CYCLE[idx]
            x = margin + i
            y = margin + dh * 0.5 - y_val * dh * 0.44
            if first: path_g.moveTo(x, y); first = False
            else:      path_g.lineTo(x, y)
        p.drawPath(path_g)

        # main pen
        main_pen = QPen(self._color)
        main_pen.setWidth(2)
        p.setPen(main_pen)
        path = QPainterPath()
        first = True
        for i in range(dw):
            phase = (self._phase + i / dw) % 1.0
            idx   = int(phase * n) % n
            y_val = self._CYCLE[idx]
            x = margin + i
            y = margin + dh * 0.5 - y_val * dh * 0.44
            if first: path.moveTo(x, y); first = False
            else:      path.lineTo(x, y)
        p.drawPath(path)


# ══════════════════════════════════════════════════════════
#  바이탈 카드
# ══════════════════════════════════════════════════════════
class VitalCard(QFrame):
    THRESHOLDS = {
        "HR":  {"warn": (50, 110), "crit": (40, 130)},
        "SpO2":{"warn": (94, 100), "crit": (90, 100)},
        "RR":  {"warn": (12, 20),  "crit": (8,  24)},
        "TEMP":{"warn": (36.0, 37.5), "crit": (35.0, 38.5)},
    }

    def __init__(self, icon, name, key, unit, default, ecg_color=GREEN, decimals=0):
        super().__init__()
        self._key  = key
        self._unit = unit
        self._dec  = decimals
        self._val  = float(default)
        self._ecg_color = ecg_color

        self.setStyleSheet(
            f"background:{PANEL2}; border:1px solid {BORD}; border-radius:8px;"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 6)
        lay.setSpacing(2)

        # 아이콘 + 이름
        top = QHBoxLayout()
        top.setSpacing(4)
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont(FONT, 10))
        icon_lbl.setStyleSheet("background:transparent; color:" + DIM)
        name_lbl = QLabel(name)
        name_lbl.setFont(QFont(FONT, 9))
        name_lbl.setStyleSheet("background:transparent; color:" + DIM)
        top.addWidget(icon_lbl)
        top.addWidget(name_lbl)
        top.addStretch()
        lay.addLayout(top)

        # 수치
        self._num = QLabel(self._fmt())
        self._num.setFont(QFont(FONT, 22, QFont.Weight.Bold))
        self._num.setStyleSheet(f"background:transparent; color:{ecg_color};")
        self._num.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self._num)

        unit_lbl = QLabel(unit)
        unit_lbl.setFont(QFont(FONT, 8))
        unit_lbl.setStyleSheet("background:transparent; color:" + DIM)
        lay.addWidget(unit_lbl)

        # ECG
        self._ecg = EcgWidget(ecg_color)
        self._ecg.setFixedHeight(32)
        lay.addWidget(self._ecg)

    def _fmt(self):
        return f"{self._val:.{self._dec}f}"

    def _status_color(self):
        t = self.THRESHOLDS.get(self._key)
        if not t:
            return self._ecg_color
        lo_c, hi_c = t["crit"]
        lo_w, hi_w = t["warn"]
        if self._val < lo_c or self._val > hi_c:
            return RED
        if self._val < lo_w or self._val > hi_w:
            return YELLOW
        return GREEN

    def update_value(self, val: float):
        self._val = val
        color = self._status_color()
        self._num.setText(self._fmt())
        self._num.setStyleSheet(f"background:transparent; color:{color};")
        self._ecg.set_color(color)
        if self._key == "HR":
            self._ecg.set_bpm(int(val))


# ══════════════════════════════════════════════════════════
#  혈압 카드 (수동 입력)
# ══════════════════════════════════════════════════════════
class BpCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"background:{PANEL2}; border:1px solid {BORD}; border-radius:8px;"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 6)
        lay.setSpacing(2)

        top = QHBoxLayout()
        il = QLabel("🩺")
        il.setFont(QFont(FONT, 10))
        il.setStyleSheet("background:transparent; color:" + DIM)
        nl = QLabel("혈압")
        nl.setFont(QFont(FONT, 9))
        nl.setStyleSheet("background:transparent; color:" + DIM)
        top.addWidget(il); top.addWidget(nl); top.addStretch()
        lay.addLayout(top)

        self._val = QLabel("--/--")
        self._val.setFont(QFont(FONT, 20, QFont.Weight.Bold))
        self._val.setStyleSheet(f"background:transparent; color:{PURPLE};")
        lay.addWidget(self._val)

        ul = QLabel("mmHg")
        ul.setFont(QFont(FONT, 8))
        ul.setStyleSheet("background:transparent; color:" + DIM)
        lay.addWidget(ul)

        btn = QPushButton("⌨  입력")
        btn.setFixedHeight(28)
        btn.setFont(QFont(FONT, 9))
        btn.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{PURPLE};
                          border:1px solid {PURPLE}; border-radius:5px;}}
            QPushButton:pressed {{background:rgba(168,85,247,.15);}}
        """)
        btn.clicked.connect(self._open)
        lay.addWidget(btn)

    def _open(self):
        dlg = BpDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            bp = dlg.result_bp()
            self._val.setText(bp)
            # 간단 경고 판정
            try:
                sys_v, dia_v = [int(x) for x in bp.split("/")]
                if sys_v > 180 or sys_v < 80 or dia_v > 110 or dia_v < 50:
                    color = RED
                elif sys_v > 140 or dia_v > 90:
                    color = YELLOW
                else:
                    color = PURPLE
                self._val.setStyleSheet(f"background:transparent; color:{color};")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════
#  혈압 키패드 다이얼로그
# ══════════════════════════════════════════════════════════
class BpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("혈압 입력")
        self.setFixedSize(300, 400)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._sys = ""; self._dia = ""; self._mode = "sys"

        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        self._title = QLabel("수축기 혈압 (Systolic)")
        self._title.setFont(QFont(FONT, 11, QFont.Weight.Bold))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet(f"color:{ACCENT};")
        lay.addWidget(self._title)

        self._disp = QLabel("___")
        self._disp.setFont(QFont(FONT, 32, QFont.Weight.Bold))
        self._disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._disp.setStyleSheet(f"color:{TEXT};")
        lay.addWidget(self._disp)

        grid = QGridLayout(); grid.setSpacing(6)
        for i, (t, v) in enumerate([
            ("7",7),("8",8),("9",9),
            ("4",4),("5",5),("6",6),
            ("1",1),("2",2),("3",3),
            ("⌫",-1),("0",0),("OK",-2),
        ]):
            b = QPushButton(t)
            b.setFixedHeight(48)
            b.setFont(QFont(FONT, 14, QFont.Weight.Bold))
            c = RED if t == "⌫" else (GREEN if t == "OK" else ACCENT)
            b.setStyleSheet(f"""
                QPushButton {{background:{PANEL}; color:{c};
                    border:1px solid {BORD}; border-radius:6px;}}
                QPushButton:pressed {{background:{PANEL2};}}
            """)
            b.clicked.connect(lambda _, vv=v: self._key(vv))
            grid.addWidget(b, i//3, i%3)
        lay.addLayout(grid)

    def _key(self, v):
        if v == -1:
            if self._mode == "sys": self._sys = self._sys[:-1]
            else: self._dia = self._dia[:-1]
        elif v == -2:
            if self._mode == "sys" and self._sys:
                self._mode = "dia"
                self._title.setText("이완기 혈압 (Diastolic)")
                self._title.setStyleSheet(f"color:{ORANGE};")
            elif self._mode == "dia" and self._dia:
                self.accept(); return
        else:
            if self._mode == "sys" and len(self._sys) < 3:
                self._sys += str(v)
            elif self._mode == "dia" and len(self._dia) < 3:
                self._dia += str(v)
        cur = self._sys if self._mode == "sys" else self._dia
        self._disp.setText(cur or "___")

    def result_bp(self):
        return f"{self._sys}/{self._dia}" if self._sys and self._dia else "--/--"


# ══════════════════════════════════════════════════════════
#  센서 컨트롤 + 바이탈 패널
# ══════════════════════════════════════════════════════════
class VitalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._running = False
        self.setStyleSheet("background:transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(5)

        # Start / Stop 버튼 행
        ctrl = QHBoxLayout(); ctrl.setSpacing(6)
        self._start_btn = self._ctrl_btn("▶  START", GREEN)
        self._stop_btn  = self._ctrl_btn("■  STOP",  RED)
        self._stop_btn.setEnabled(False)

        self._led = QLabel("●")
        self._led.setFont(QFont(FONT, 14))
        self._led.setFixedWidth(22)
        self._led.setStyleSheet(f"color:{DIM2}; background:transparent;")

        self._sens_label = QLabel("센서 대기")
        self._sens_label.setFont(QFont(FONT, 9))
        self._sens_label.setStyleSheet(f"color:{DIM}; background:transparent;")

        self._start_btn.clicked.connect(self._start)
        self._stop_btn.clicked.connect(self._stop)

        ctrl.addWidget(self._led)
        ctrl.addWidget(self._sens_label)
        ctrl.addStretch()
        ctrl.addWidget(self._start_btn)
        ctrl.addWidget(self._stop_btn)
        root.addLayout(ctrl)

        # 바이탈 카드 5개
        self._hr   = VitalCard("♥", "심박수",   "HR",   "bpm",  72,   RED,    0)
        self._spo2 = VitalCard("◉", "산소포화도","SpO2", "%",    98,   TEAL,   0)
        self._rr   = VitalCard("~", "호흡수",   "RR",   "/min", 16,   ACCENT, 0)
        self._temp = VitalCard("🌡", "체온",     "TEMP", "°C",   36.5, ORANGE, 1)
        self._bp   = BpCard()

        cards = QHBoxLayout(); cards.setSpacing(5)
        for c in [self._hr, self._spo2, self._rr, self._temp, self._bp]:
            cards.addWidget(c)
        root.addLayout(cards)

        # 시뮬 타이머 (실제 센서 연동 시 교체)
        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self._simulate)

    def _ctrl_btn(self, text, color):
        b = QPushButton(text)
        b.setFixedHeight(32)
        b.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{color};
                border:1px solid {color}; border-radius:6px; padding:0 10px;}}
            QPushButton:pressed {{background:rgba(255,255,255,.07);}}
            QPushButton:disabled {{color:{DIM2}; border-color:{DIM2};}}
        """)
        return b

    def _start(self):
        self._running = True
        self._led.setStyleSheet(f"color:{GREEN}; background:transparent;")
        self._sens_label.setText("센서 측정 중")
        self._sens_label.setStyleSheet(f"color:{GREEN}; background:transparent;")
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._sim_timer.start(2000)

    def _stop(self):
        self._running = False
        self._led.setStyleSheet(f"color:{DIM2}; background:transparent;")
        self._sens_label.setText("센서 대기")
        self._sens_label.setStyleSheet(f"color:{DIM}; background:transparent;")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._sim_timer.stop()

    def _simulate(self):
        import random
        self._hr.update_value(  60 + random.randint(0, 60))
        self._spo2.update_value(93 + random.randint(0, 7))
        self._rr.update_value(  12 + random.randint(0, 10))
        self._temp.update_value(35.5 + random.uniform(0, 3.5))

    def update_vital(self, key: str, val: float):
        """외부 센서 콜백 — key: 'HR'|'SpO2'|'RR'|'TEMP'"""
        mapping = {"HR": self._hr, "SpO2": self._spo2,
                   "RR": self._rr, "TEMP": self._temp}
        if key in mapping:
            mapping[key].update_value(val)


# ══════════════════════════════════════════════════════════
#  카메라 패널
# ══════════════════════════════════════════════════════════
class CameraPanel(QFrame):
    def __init__(self, index=0):
        super().__init__()
        self._idx = index; self._cap = None
        self.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORD}; border-radius:8px;"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(5)

        hdr = QHBoxLayout()
        tl = QLabel("📷  환자 카메라")
        tl.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        tl.setStyleSheet(f"background:transparent; color:{TEXT};")
        self._status = QLabel("대기")
        self._status.setFont(QFont(FONT, 8))
        self._status.setStyleSheet(f"background:transparent; color:{DIM};")
        hdr.addWidget(tl); hdr.addStretch(); hdr.addWidget(self._status)
        lay.addLayout(hdr)

        self._view = QLabel()
        self._view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._view.setStyleSheet(
            f"background:{BG}; border:1px solid {BORD2}; border-radius:6px; color:{DIM};"
        )
        self._view.setText("카메라 미연결")
        self._view.setFont(QFont(FONT, 10))
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self._view, stretch=1)

        btns = QHBoxLayout(); btns.setSpacing(5)
        on  = self._mk_btn("▶ ON",  GREEN)
        off = self._mk_btn("■ OFF", RED)
        off.setEnabled(False)
        self._cam_off_btn = off
        on.clicked.connect(lambda: self._start(on, off))
        off.clicked.connect(lambda: self._stop(on, off))
        btns.addWidget(on); btns.addWidget(off)
        lay.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._grab)

    def _mk_btn(self, t, c):
        b = QPushButton(t)
        b.setFixedHeight(28); b.setFont(QFont(FONT, 9))
        b.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{c};
                border:1px solid {c}; border-radius:5px;}}
            QPushButton:pressed {{background:rgba(255,255,255,.07);}}
            QPushButton:disabled {{color:{DIM2}; border-color:{DIM2};}}
        """)
        return b

    def _start(self, on_btn, off_btn):
        try:
            import cv2
            self._cap = cv2.VideoCapture(self._idx)
            if not self._cap.isOpened():
                self._view.setText("카메라를 열 수 없습니다")
                return
            self._status.setText("● LIVE")
            self._status.setStyleSheet(f"background:transparent; color:{GREEN};")
            on_btn.setEnabled(False); off_btn.setEnabled(True)
            self._timer.start(33)
        except ImportError:
            self._view.setText("opencv-python 필요\npip install opencv-python")

    def _stop(self, on_btn, off_btn):
        self._timer.stop()
        if self._cap: self._cap.release(); self._cap = None
        self._status.setText("대기")
        self._status.setStyleSheet(f"background:transparent; color:{DIM};")
        on_btn.setEnabled(True); off_btn.setEnabled(False)
        self._view.setText("카메라 미연결")

    def _grab(self):
        if not self._cap: return
        import cv2
        ret, frame = self._cap.read()
        if not ret: return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._view.width(), self._view.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._view.setPixmap(pix)


# ══════════════════════════════════════════════════════════
#  AVPU 글로우 버튼 위젯
# ══════════════════════════════════════════════════════════
class AvpuButton(QWidget):
    """Custom painted AVPU button with glow effect."""

    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self._hovered  = False
        self._pressed  = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        # 글로우 펄스 타이머
        self._pulse = 0.0
        self._pulse_dir = 1
        t = QTimer(self)
        t.timeout.connect(self._animate)
        t.start(40)

    def _animate(self):
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0: self._pulse_dir = -1
        if self._pulse <= 0.0: self._pulse_dir =  1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = 12

        # 글로우
        alpha = int(30 + 40 * self._pulse) if not self._pressed else 80
        glow_color = QColor(14, 165, 233, alpha)
        for i in range(6, 0, -1):
            gp = QPen(glow_color)
            gp.setWidth(i * 2)
            p.setPen(gp)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(i, i, w - i*2, h - i*2, r, r)

        # 배경 그라디언트
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor("#0a2040") if not self._pressed else QColor("#0e2c55"))
        grad.setColorAt(1, QColor("#051525") if not self._pressed else QColor("#081e38"))
        p.setPen(QPen(QColor(ACCENT), 2))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(3, 3, w - 6, h - 6, r, r)

        # 텍스트
        p.setPen(QPen(QColor(ACCENT2 if not self._pressed else ACCENT)))
        p.setFont(QFont(FONT, 13, QFont.Weight.Bold))
        p.drawText(QRectF(3, 3, w - 6, (h - 6) * 0.38),
                   Qt.AlignmentFlag.AlignCenter, "🧠  AVPU")
        p.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        p.drawText(QRectF(3, (h - 6) * 0.4, w - 6, (h - 6) * 0.35),
                   Qt.AlignmentFlag.AlignCenter, "의식 수준 확인")

        # A V P U 뱃지 (하단)
        badge_w = (w - 24) / 4
        badge_h = 22
        badge_y = h - badge_h - 8
        for i, (letter, color) in enumerate([
            ("A", GREEN), ("V", YELLOW), ("P", ORANGE), ("U", RED)
        ]):
            bx = 8 + i * (badge_w + 4)
            p.setPen(QPen(QColor(color)))
            p.setBrush(QColor(0, 0, 0, 80))
            p.drawRoundedRect(QRectF(bx, badge_y, badge_w, badge_h), 4, 4)
            p.setFont(QFont(FONT, 8, QFont.Weight.Bold))
            p.drawText(QRectF(bx, badge_y, badge_w, badge_h),
                       Qt.AlignmentFlag.AlignCenter, letter)

    def mousePressEvent(self, _):   self._pressed = True;  self.update()
    def mouseReleaseEvent(self, e):
        self._pressed = False; self.update()
        if self.rect().contains(e.position().toPoint()):
            self._on_click()
    def enterEvent(self, _): self._hovered = True;  self.update()
    def leaveEvent(self, _): self._hovered = False; self.update()


# ══════════════════════════════════════════════════════════
#  메인 화면
# ══════════════════════════════════════════════════════════
class MainScreen(QWidget):
    def __init__(self, nav):
        super().__init__()
        self._nav = nav
        self.setStyleSheet(f"background:{BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(5)

        root.addWidget(self._header())

        # 상단: 바이탈 전체 행
        self._vitals = VitalPanel()
        root.addWidget(self._vitals)

        # 중단: [카메라 | AVPU 버튼 | 응급 버튼 격자]
        mid = QHBoxLayout(); mid.setSpacing(5)
        self._cam = CameraPanel()
        mid.addWidget(self._cam, stretch=4)
        mid.addWidget(self._avpu_block(), stretch=3)
        mid.addWidget(self._emergency_block(), stretch=5)
        root.addLayout(mid, stretch=1)

        root.addWidget(self._footer())

    # ── 헤더 ──────────────────────────────────────────────
    def _header(self):
        f = QFrame()
        f.setFixedHeight(48)
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORD}; border-radius:8px;"
        )
        lay = QHBoxLayout(f)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(8)

        # 로고 이미지
        import os
        logo = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
        logo_pix = QPixmap(logo_path)
        if not logo_pix.isNull():
            logo_pix = logo_pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(logo_pix)
        else:
            logo.setText("⚓")
            logo.setFont(QFont(FONT, 18, QFont.Weight.Bold))
        logo.setFixedWidth(40)
        logo.setStyleSheet("background:transparent;")

        tl = QLabel("MDTS")
        tl.setFont(QFont(FONT, 15, QFont.Weight.Bold))
        tl.setStyleSheet(f"color:{TEXT}; background:transparent; letter-spacing:3px;")
        sub = QLabel("Maritime Digital Triage System  ·  비의료인용")
        sub.setFont(QFont(FONT, 8))
        sub.setStyleSheet(f"color:{DIM}; background:transparent;")

        col = QVBoxLayout(); col.setSpacing(0)
        col.addWidget(tl); col.addWidget(sub)

        lay.addWidget(logo)
        lay.addLayout(col)
        lay.addStretch()

        # 시계
        self._clk = QLabel()
        self._clk.setFont(QFont(FONT, 11))
        self._clk.setStyleSheet(f"color:{ACCENT}; background:transparent;")
        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000); self._tick()
        lay.addWidget(self._clk)
        lay.addSpacing(8)

        # SOS
        sos = QPushButton("  🆘  SOS  ")
        sos.setFixedHeight(34)
        sos.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        sos.setStyleSheet(f"""
            QPushButton {{background:{RED2}; color:white;
                          border:none; border-radius:6px; letter-spacing:1px;}}
            QPushButton:pressed {{background:#b91c1c;}}
        """)
        sos.clicked.connect(lambda: self._nav(3))
        lay.addWidget(sos)
        return f

    def _tick(self):
        self._clk.setText(
            QDateTime.currentDateTime().toString("yyyy-MM-dd  HH:mm:ss")
        )

    # ── AVPU 블록 ──────────────────────────────────────────
    def _avpu_block(self):
        f = QFrame()
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORD}; border-radius:8px;"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        hint = QLabel("환자 평가 시작")
        hint.setFont(QFont(FONT, 8))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color:{DIM}; background:transparent;")
        lay.addWidget(hint)

        btn = AvpuButton(lambda: self._nav(1))
        lay.addWidget(btn, stretch=1)
        return f

    # ── 응급 버튼 격자 ────────────────────────────────────
    def _emergency_block(self):
        f = QFrame()
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORD}; border-radius:8px;"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(5)

        ttl = QLabel("응급 처치 선택")
        ttl.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setStyleSheet(f"color:{DIM}; background:transparent;")
        lay.addWidget(ttl)

        grid = QGridLayout(); grid.setSpacing(5)
        items = [
            ("💔", "심폐소생술", RED,    2),
            ("🩸", "출혈 처치",  ORANGE, 4),
            ("🔥", "화상 처치",  YELLOW, 4),
            ("🦴", "골절/탈구",  TEAL,   4),
            ("🌊", "익수/저체온",BLUE,   4) if False else
            ("🌊", "익수/저체온",ACCENT, 4),
            ("😮", "기도 폐쇄",  PURPLE, 4),
        ]
        BLUE_ = ACCENT  # alias
        items = [
            ("💔", "심폐소생술", RED,    2),
            ("🩸", "출혈 처치",  ORANGE, 4),
            ("🔥", "화상 처치",  YELLOW, 4),
            ("🦴", "골절/탈구",  TEAL,   4),
            ("🌊", "익수/저체온",ACCENT, 4),
            ("😮", "기도 폐쇄",  PURPLE, 4),
        ]
        for i, (ico, name, color, page) in enumerate(items):
            b = QPushButton(f"{ico}  {name}")
            b.setFixedHeight(52)
            b.setFont(QFont(FONT, 10, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:{PANEL2};
                    color:{color};
                    border:1px solid {color};
                    border-radius:7px;
                    text-align:left; padding-left:10px;
                }}
                QPushButton:pressed {{
                    background:rgba(255,255,255,.06);
                    border-width:2px;
                }}
            """)
            b.clicked.connect(lambda _, p=page: self._nav(p))
            grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        return f

    # ── 푸터 ──────────────────────────────────────────────
    def _footer(self):
        f = QFrame()
        f.setFixedHeight(24)
        f.setStyleSheet(f"background:{PANEL}; border:1px solid {BORD}; border-radius:5px;")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(12, 0, 12, 0)
        w = QLabel("⚠  이 가이드는 전문 의료를 대체하지 않습니다 — 가능한 빨리 의료진에게 연락하십시오")
        w.setFont(QFont(FONT, 8))
        w.setStyleSheet(f"color:{YELLOW}; background:transparent;")
        lay.addWidget(w)
        lay.addStretch()
        r = QLabel("Maritime Medic v2  ·  1024×600")
        r.setFont(QFont(FONT, 8))
        r.setStyleSheet(f"color:{DIM}; background:transparent;")
        lay.addWidget(r)
        return f


# ══════════════════════════════════════════════════════════
#  AVPU 화면
# ══════════════════════════════════════════════════════════
class AvpuScreen(QWidget):
    STEPS = [
        ("A","Alert — 의식 명료",      GREEN,  [
            "눈을 뜨고 있는가?",
            "말을 걸면 즉시 대답하는가?",
            "시간·장소·자신의 이름을 아는가?",
            "자발적으로 움직이는가?",
        ], "모두 해당 → A(정상). 하나라도 아니면 V로 이동"),
        ("V","Voice — 음성 반응",      YELLOW, [
            "크게 이름을 부르거나 '눈 떠 보세요!' 말하기",
            "눈을 뜨는가? / 손을 움직이는가?",
            "간단한 명령에 반응하는가? (손 꽉 쥐어 보세요)",
        ], "반응 있으면 → V. 없으면 P 확인"),
        ("P","Pain — 통증 반응",       ORANGE, [
            "흉골 중앙을 손가락 관절로 강하게 문지르기",
            "눈썹 위 눈두덩이를 강하게 누르기",
            "눈꺼풀이 떨리거나 손발을 움츠리는가?",
        ], "반응 있으면 → P. 전혀 없으면 U (무반응)"),
        ("U","Unresponsive — 무반응",  RED,    [
            "A·V·P 모두 반응 없음",
            "즉시 호흡·맥박 확인",
            "AED 위치 확인 및 구조 요청",
            "CPR 또는 회복 자세 즉시 시작",
        ], "→ CPR 화면으로 이동 또는 SOS 요청"),
    ]

    def __init__(self, nav):
        super().__init__()
        self._nav  = nav
        self._step = 0
        self.setStyleSheet(f"background:{BG};")
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 8, 10, 8)
        self._root.setSpacing(6)
        self._root.addWidget(self._top_bar())
        self._card = QFrame()
        self._root.addWidget(self._card, stretch=1)
        self._btm = QHBoxLayout()
        self._root.addLayout(self._btm)
        self._refresh()

    def _top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background:{PANEL}; border:1px solid {BORD}; border-radius:8px;")
        lay = QHBoxLayout(bar); lay.setContentsMargins(10, 0, 10, 0)
        b = self._nav_btn("← 홈", ACCENT, h=32, w=68)
        b.clicked.connect(lambda: self._nav(0))
        lay.addWidget(b); lay.addStretch()
        t = QLabel("AVPU  의식 수준 평가")
        t.setFont(QFont(FONT, 13, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{TEXT}; background:transparent;")
        lay.addWidget(t); lay.addStretch()
        self._dots = []
        for s in self.STEPS:
            d = QLabel("●")
            d.setFont(QFont(FONT, 14))
            d.setStyleSheet(f"color:{DIM2}; background:transparent;")
            self._dots.append((d, s[2]))
            lay.addWidget(d)
        return bar

    def _refresh(self):
        for i, (d, c) in enumerate(self._dots):
            d.setStyleSheet(
                f"color:{c}; background:transparent;" if i == self._step
                else f"color:{DIM2}; background:transparent;"
            )
        lo = self._card.layout()
        if lo:
            while lo.count():
                item = lo.takeAt(0)
                if item.widget(): item.widget().setParent(None)
            QWidget().setLayout(lo)

        letter, title, color, checks, note = self.STEPS[self._step]
        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(22, 16, 22, 16)
        cl.setSpacing(10)
        self._card.setStyleSheet(
            f"background:{PANEL}; border:2px solid {color}; border-radius:12px;"
        )

        top = QHBoxLayout(); top.setSpacing(14)
        big = QLabel(letter)
        big.setFont(QFont(FONT, 58, QFont.Weight.Bold))
        big.setStyleSheet(f"color:{color}; background:transparent;")
        big.setFixedWidth(72)
        info = QVBoxLayout(); info.setSpacing(2)
        t1 = QLabel(title)
        t1.setFont(QFont(FONT, 17, QFont.Weight.Bold))
        t1.setStyleSheet(f"color:{color}; background:transparent;")
        t2 = QLabel(f"단계 {self._step+1} / {len(self.STEPS)}")
        t2.setFont(QFont(FONT, 10))
        t2.setStyleSheet(f"color:{DIM}; background:transparent;")
        info.addWidget(t1); info.addWidget(t2)
        top.addWidget(big); top.addLayout(info)
        cl.addLayout(top)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{color};")
        cl.addWidget(sep)

        for chk in checks:
            row = QHBoxLayout(); row.setSpacing(8)
            bul = QLabel("▶")
            bul.setFont(QFont(FONT, 10))
            bul.setStyleSheet(f"color:{color}; background:transparent;")
            bul.setFixedWidth(16)
            txt = QLabel(chk)
            txt.setFont(QFont(FONT, 12))
            txt.setStyleSheet(f"color:{TEXT}; background:transparent;")
            row.addWidget(bul); row.addWidget(txt)
            cl.addLayout(row)

        cl.addStretch()
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color:{BORD};")
        cl.addWidget(sep2)
        nt = QLabel(note)
        nt.setFont(QFont(FONT, 11))
        nt.setStyleSheet(f"color:{YELLOW}; background:transparent;")
        cl.addWidget(nt)

        while self._btm.count():
            item = self._btm.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        if self._step > 0:
            pb = self._nav_btn("◀  이전", DIM, h=44)
            pb.clicked.connect(self._prev)
            self._btm.addWidget(pb)
        self._btm.addStretch()

        rb = self._nav_btn(f'✔  "{letter}" 기록', color, h=44)
        rb.clicked.connect(lambda: self._nav(0))
        self._btm.addWidget(rb)

        if self._step < len(self.STEPS) - 1:
            nb = self._nav_btn("다음 ▶", ACCENT, h=44)
            nb.clicked.connect(self._next)
            self._btm.addWidget(nb)
        else:
            cb = self._nav_btn("CPR 화면 →", RED, h=44)
            cb.clicked.connect(lambda: self._nav(2))
            self._btm.addWidget(cb)

    def _nav_btn(self, text, color, h=44, w=None):
        b = QPushButton(text)
        if w: b.setFixedWidth(w)
        b.setFixedHeight(h)
        b.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{color};
                border:1px solid {color}; border-radius:8px; padding:0 16px;}}
            QPushButton:pressed {{background:rgba(255,255,255,.07);}}
        """)
        return b

    def _next(self):
        if self._step < len(self.STEPS)-1: self._step += 1; self._refresh()
    def _prev(self):
        if self._step > 0: self._step -= 1; self._refresh()
    def reset(self): self._step = 0; self._refresh()


# ══════════════════════════════════════════════════════════
#  CPR 화면
# ══════════════════════════════════════════════════════════
class CprScreen(QWidget):
    GUIDE = [
        ("1","안전·반응 확인",   ["주변 위험 제거","어깨 두드리며 '괜찮으세요?' 외침","반응 없으면 도움 + AED 요청"],  ACCENT),
        ("2","기도 확보",        ["단단한 바닥에 눕힘","머리 젖히고 턱 들어 올리기","10초 이내 호흡 확인"],            TEAL),
        ("3","가슴 압박 30회",   ["흉골 중앙에 양손 깍지","5~6 cm 깊이 수직 압박","100~120회/분 속도","30회→인공호흡 2회"], ORANGE),
        ("4","인공호흡 2회",     ["머리 젖히기 유지 — 코 막고 1초 불기","가슴 올라오는지 확인","2회→압박 반복","AED 즉시 사용"], RED),
    ]

    def __init__(self, nav):
        super().__init__()
        self._nav = nav; self._count = 0
        self.setStyleSheet(f"background:{BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8); root.setSpacing(6)
        root.addWidget(self._top_bar())
        body = QHBoxLayout(); body.setSpacing(8)
        body.addWidget(self._counter(), stretch=3)
        body.addWidget(self._guide(),   stretch=7)
        root.addLayout(body)

    def _top_bar(self):
        bar = QFrame(); bar.setFixedHeight(44)
        bar.setStyleSheet(f"background:{PANEL}; border:1px solid {BORD}; border-radius:8px;")
        lay = QHBoxLayout(bar); lay.setContentsMargins(10, 0, 10, 0)
        b = QPushButton("← 홈"); b.setFixedWidth(68); b.setFixedHeight(32)
        b.setFont(QFont(FONT, 9))
        b.setStyleSheet(f"QPushButton{{background:transparent; color:{ACCENT}; border:1px solid {ACCENT}; border-radius:6px;}} QPushButton:pressed{{background:rgba(14,165,233,.15);}}")
        b.clicked.connect(lambda: self._nav(0))
        lay.addWidget(b); lay.addStretch()
        t = QLabel("💔  심폐소생술 (CPR) 가이드")
        t.setFont(QFont(FONT, 13, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{RED}; background:transparent;")
        lay.addWidget(t); lay.addStretch()
        s = QPushButton("🆘 SOS"); s.setFixedSize(78, 32)
        s.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        s.setStyleSheet(f"QPushButton{{background:{RED2}; color:white; border:none; border-radius:6px;}} QPushButton:pressed{{background:#b91c1c;}}")
        s.clicked.connect(lambda: self._nav(3))
        lay.addWidget(s); return bar

    def _counter(self):
        f = QFrame(); f.setStyleSheet(f"background:{PANEL}; border:1px solid {BORD}; border-radius:10px;")
        lay = QVBoxLayout(f); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)
        tl = QLabel("압박 카운터"); tl.setFont(QFont(FONT, 10))
        tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.setStyleSheet(f"color:{DIM}; background:transparent;")
        lay.addWidget(tl)
        self._cnt = QLabel("0"); self._cnt.setFont(QFont(FONT, 52, QFont.Weight.Bold))
        self._cnt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cnt.setStyleSheet(f"color:{RED}; background:transparent;")
        lay.addWidget(self._cnt)
        sub = QLabel("/ 30회"); sub.setFont(QFont(FONT, 11))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{DIM}; background:transparent;")
        lay.addWidget(sub)
        press = QPushButton("압박!"); press.setFixedHeight(68)
        press.setFont(QFont(FONT, 16, QFont.Weight.Bold))
        press.setStyleSheet(f"QPushButton{{background:#2d0000; color:{RED}; border:2px solid {RED}; border-radius:9px;}} QPushButton:pressed{{background:#4a0000;}}")
        press.clicked.connect(self._press); lay.addWidget(press)
        rst = QPushButton("초기화"); rst.setFixedHeight(30); rst.setFont(QFont(FONT, 9))
        rst.setStyleSheet(f"QPushButton{{background:transparent; color:{DIM}; border:1px solid {BORD}; border-radius:5px;}} QPushButton:pressed{{background:rgba(255,255,255,.05);}}")
        rst.clicked.connect(self._reset); lay.addWidget(rst)
        self._hint = QLabel("100~120회/분 유지"); self._hint.setFont(QFont(FONT, 9))
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet(f"color:{YELLOW}; background:transparent;")
        lay.addWidget(self._hint); lay.addStretch(); return f

    def _guide(self):
        f = QFrame(); f.setStyleSheet(f"background:{PANEL}; border:1px solid {BORD}; border-radius:10px;")
        lay = QVBoxLayout(f); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)
        tl = QLabel("단계별 가이드"); tl.setFont(QFont(FONT, 11, QFont.Weight.Bold))
        tl.setStyleSheet(f"color:{DIM}; background:transparent;"); lay.addWidget(tl)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(f"color:{BORD};"); lay.addWidget(sep)
        for num, title, checks, color in self.GUIDE:
            sf = QFrame(); sf.setStyleSheet(f"background:{PANEL2}; border:1px solid {color}; border-radius:6px;")
            sl = QVBoxLayout(sf); sl.setContentsMargins(10, 7, 10, 7); sl.setSpacing(3)
            h = QHBoxLayout()
            h.addWidget(self._lbl(f"STEP {num}", 9, color, True))
            h.addWidget(self._lbl(title, 10, TEXT, True))
            sl.addLayout(h)
            for chk in checks:
                r = QHBoxLayout()
                r.addWidget(self._lbl("•", 9, color))
                r.addWidget(self._lbl(chk, 10, DIM))
                sl.addLayout(r)
            lay.addWidget(sf)
        lay.addStretch(); return f

    def _lbl(self, t, sz, c, bold=False):
        w = QLabel(t); w.setFont(QFont(FONT, sz, QFont.Weight.Bold if bold else QFont.Weight.Normal))
        w.setStyleSheet(f"color:{c}; background:transparent;"); return w

    def _press(self):
        self._count = min(self._count + 1, 30)
        self._cnt.setText(str(self._count))
        if self._count >= 30:
            self._cnt.setStyleSheet(f"color:{GREEN}; background:transparent;")
            self._hint.setText("→ 인공호흡 2회 실시!")
        else:
            self._cnt.setStyleSheet(f"color:{RED}; background:transparent;")

    def _reset(self):
        self._count = 0
        self._cnt.setText("0")
        self._cnt.setStyleSheet(f"color:{RED}; background:transparent;")
        self._hint.setText("100~120회/분 유지")


# ══════════════════════════════════════════════════════════
#  SOS 화면
# ══════════════════════════════════════════════════════════
class SosScreen(QWidget):
    def __init__(self, nav):
        super().__init__()
        self._nav = nav
        self.setStyleSheet(f"background:{BG};")
        root = QVBoxLayout(self); root.setContentsMargins(20, 16, 20, 16); root.setSpacing(12)

        bk = QPushButton("← 홈으로 돌아가기"); bk.setFixedHeight(40)
        bk.setFont(QFont(FONT, 10))
        bk.setStyleSheet(f"QPushButton{{background:transparent; color:{ACCENT}; border:1px solid {ACCENT}; border-radius:7px;}} QPushButton:pressed{{background:rgba(14,165,233,.12);}}")
        bk.clicked.connect(lambda: self._nav(0)); root.addWidget(bk)

        t = QLabel("🆘  구조 요청 / 비상 연락"); t.setFont(QFont(FONT, 18, QFont.Weight.Bold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter); t.setStyleSheet(f"color:{RED}; background:transparent;")
        root.addWidget(t)

        for role, contact in [
            ("선박 선장 / 당직 사관",      "선내 인터폰  #01"),
            ("무선 통신실 (Radio Room)",   "채널 16  (조난 주파수)"),
            ("해양경찰 구조대",            "☎  122"),
            ("국제 조난 신호",             "MAYDAY × 3"),
        ]:
            card = QFrame(); card.setFixedHeight(60)
            card.setStyleSheet(f"background:{PANEL}; border:1px solid {RED2}; border-radius:10px;")
            cl = QHBoxLayout(card); cl.setContentsMargins(18, 0, 18, 0)
            rl = QLabel(role); rl.setFont(QFont(FONT, 12)); rl.setStyleSheet(f"color:{TEXT}; background:transparent;")
            vl = QLabel(contact); vl.setFont(QFont(FONT, 13, QFont.Weight.Bold))
            vl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            vl.setStyleSheet(f"color:{RED}; background:transparent;")
            cl.addWidget(rl); cl.addStretch(); cl.addWidget(vl)
            root.addWidget(card)

        root.addStretch()
        note = QLabel("MAYDAY 교신: MAYDAY × 3 → 선박명 → 위치 → 인명 상황 → 필요 지원")
        note.setFont(QFont(FONT, 11)); note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"color:{YELLOW}; background:transparent;")
        root.addWidget(note)


# ══════════════════════════════════════════════════════════
#  메인 윈도우
# ══════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MDTS — Maritime Digital Triage System")
        self.setFixedSize(W, H)
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._screens = [
            MainScreen(self._go),   # 0
            AvpuScreen(self._go),   # 1
            CprScreen(self._go),    # 2
            SosScreen(self._go),    # 3
        ]
        for s in self._screens:
            self._stack.addWidget(s)

    def _go(self, idx: int):
        if idx == 1: self._screens[1].reset()
        self._stack.setCurrentIndex(idx)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
