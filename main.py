"""
MDTS — Maritime Digital Triage System
PyQt6 · 1024×600  |  Neon-Blue Rugged UI
"""
import sys, math, os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QDialog, QSizePolicy,
)
from PyQt6.QtCore  import Qt, QTimer, QDateTime, QRectF, QPointF, QSize
from PyQt6.QtGui   import (
    QFont, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient,
    QPainterPath, QImage, QPixmap,
)

W, H = 1024, 600
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Malgun Gothic"

# ── 팔레트 ────────────────────────────────────────────────
BG        = "#030810"
PANEL     = "#06101e"
PANEL2    = "#081428"
GRID_CLR  = "#0c1e36"
NEON      = "#0af"          # 전기 시안
NEON2     = "#06f"          # 딥 블루
NEON_DIM  = "#0369a1"
RED       = "#ff3b3b"
RED2      = "#cc1414"
GREEN     = "#00ff88"
YELLOW    = "#ffe033"
ORANGE    = "#ff8c00"
PURPLE    = "#c87bff"
TEAL      = "#00e5c8"
TEXT      = "#e8f4ff"
DIM       = "#3a6080"
DIM2      = "#1a3050"


# ══════════════════════════════════════════════════════════
#  격자 배경 위젯 (모든 화면 공통 배경)
# ══════════════════════════════════════════════════════════
class GridBg(QWidget):
    """Dark bg + subtle neon grid mesh."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BG))

        # grid
        pen = QPen(QColor(GRID_CLR)); pen.setWidth(1)
        p.setPen(pen)
        step = 38
        for x in range(0, self.width(), step):
            p.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            p.drawLine(0, y, self.width(), y)

        # blue radial glow top-left
        rg = QRadialGradient(QPointF(0, 0), 400)
        rg.setColorAt(0, QColor(0, 100, 255, 35))
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg))

        # blue radial glow bottom-right
        rg2 = QRadialGradient(QPointF(self.width(), self.height()), 380)
        rg2.setColorAt(0, QColor(0, 170, 255, 28))
        rg2.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg2))


# ══════════════════════════════════════════════════════════
#  글로우 카드 (네온 테두리 + 안쪽 글로우)
# ══════════════════════════════════════════════════════════
class GlowCard(QFrame):
    def __init__(self, color=NEON, radius=10, parent=None):
        super().__init__(parent)
        self._color  = QColor(color)
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")

    def set_color(self, c: str):
        self._color = QColor(c); self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, r = self.width(), self.height(), self._radius

        # 다층 글로우
        for i in range(5, 0, -1):
            alpha = int(18 + i * 6)
            gpen = QPen(QColor(self._color.red(),
                               self._color.green(),
                               self._color.blue(), alpha))
            gpen.setWidth(i * 2)
            p.setPen(gpen); p.setBrush(Qt.BrushStyle.NoBrush)
            m = i
            p.drawRoundedRect(m, m, w - m*2, h - m*2, r, r)

        # 패널 배경
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(PANEL2))
        grad.setColorAt(1, QColor(PANEL))
        p.setPen(QPen(self._color, 1.5))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(4, 4, w - 8, h - 8, r, r)


# ══════════════════════════════════════════════════════════
#  ECG 파형 위젯
# ══════════════════════════════════════════════════════════
class EcgWidget(QWidget):
    _CYCLE: list = []

    @classmethod
    def _build(cls, n=120):
        if cls._CYCLE: return
        pts = []
        for i in range(n):
            t = i / n
            if   t < .10: y = 0
            elif t < .16: y =  .18 * math.sin((t-.10)/.06 * math.pi)
            elif t < .28: y = 0
            elif t < .31: y = -.12 * (t-.28)/.03
            elif t < .34: y = -.12 + 1.12*(t-.31)/.03
            elif t < .38: y = 1.0  - 1.20*(t-.34)/.04
            elif t < .42: y = -.20 + .20*(t-.38)/.04
            elif t < .55: y = 0
            elif t < .70: y =  .30 * math.sin((t-.55)/.15 * math.pi)
            else:          y = 0
            pts.append(y)
        cls._CYCLE = pts

    def __init__(self, color=GREEN, bpm=72, parent=None):
        super().__init__(parent)
        self._build()
        self._color = QColor(color)
        self._bpm   = bpm
        self._phase = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(30)

    def set_bpm(self, v): self._bpm = max(1, v)
    def set_color(self, c): self._color = QColor(c)

    def _tick(self):
        self._phase = (self._phase + self._bpm/60*0.03) % 1.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, mg = self.width(), self.height(), 3
        n = len(self._CYCLE)

        def _pts():
            out = []
            for i in range(w - mg*2):
                ph = (self._phase + i/(w-mg*2)) % 1.0
                y_v = self._CYCLE[int(ph*n) % n]
                out.append((mg+i, mg + (h-mg*2)*(.5 - y_v*.45)))
            return out

        pts = _pts()
        c = self._color

        # glow layer
        gpen = QPen(QColor(c.red(), c.green(), c.blue(), 50)); gpen.setWidth(5)
        p.setPen(gpen)
        path = QPainterPath()
        path.moveTo(*pts[0])
        for x, y in pts[1:]: path.lineTo(x, y)
        p.drawPath(path)

        # main line
        mpen = QPen(c); mpen.setWidth(2); p.setPen(mpen)
        path2 = QPainterPath()
        path2.moveTo(*pts[0])
        for x, y in pts[1:]: path2.lineTo(x, y)
        p.drawPath(path2)


# ══════════════════════════════════════════════════════════
#  바이탈 카드
# ══════════════════════════════════════════════════════════
class VitalCard(GlowCard):
    THRESH = {
        "HR":  {"warn":(50,110), "crit":(40,130)},
        "SpO2":{"warn":(94,100), "crit":(90,100)},
        "RR":  {"warn":(12,20),  "crit":(8,24)},
        "TEMP":{"warn":(36.0,37.5),"crit":(35.0,38.5)},
    }

    def __init__(self, icon, name, key, unit, default, ecg_color=GREEN, dec=0):
        super().__init__(color=ecg_color)
        self._key=key; self._unit=unit; self._dec=dec
        self._val=float(default); self._base_color=ecg_color

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 8); lay.setSpacing(2)

        top = QHBoxLayout(); top.setSpacing(4)
        self._icon_l = QLabel(icon)
        self._icon_l.setFont(QFont(FONT, 9))
        self._icon_l.setStyleSheet(f"background:transparent; color:{DIM}")
        nl = QLabel(name)
        nl.setFont(QFont(FONT, 8))
        nl.setStyleSheet(f"background:transparent; color:{DIM}")
        top.addWidget(self._icon_l); top.addWidget(nl); top.addStretch()
        lay.addLayout(top)

        self._num = QLabel(self._fmt())
        self._num.setFont(QFont(FONT, 22, QFont.Weight.Bold))
        self._num.setStyleSheet(f"background:transparent; color:{ecg_color};")
        lay.addWidget(self._num)

        ul = QLabel(unit)
        ul.setFont(QFont(FONT, 8))
        ul.setStyleSheet(f"background:transparent; color:{DIM}")
        lay.addWidget(ul)

        self._ecg = EcgWidget(ecg_color)
        self._ecg.setFixedHeight(30)
        lay.addWidget(self._ecg)

    def _fmt(self): return f"{self._val:.{self._dec}f}"

    def _color_for(self):
        t = self.THRESH.get(self._key)
        if not t: return self._base_color
        lc,hc = t["crit"]; lw,hw = t["warn"]
        if self._val < lc or self._val > hc: return RED
        if self._val < lw or self._val > hw: return YELLOW
        return GREEN

    def update_value(self, val: float):
        self._val = val
        c = self._color_for()
        self._num.setText(self._fmt())
        self._num.setStyleSheet(f"background:transparent; color:{c};")
        self._ecg.set_color(c)
        self.set_color(c)
        if self._key == "HR": self._ecg.set_bpm(int(val))


# ══════════════════════════════════════════════════════════
#  혈압 카드
# ══════════════════════════════════════════════════════════
class BpCard(GlowCard):
    def __init__(self):
        super().__init__(color=PURPLE)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 8); lay.setSpacing(2)

        top = QHBoxLayout()
        il = QLabel("🩺"); il.setFont(QFont(FONT, 9)); il.setStyleSheet(f"background:transparent; color:{DIM}")
        nl = QLabel("혈압"); nl.setFont(QFont(FONT, 8)); nl.setStyleSheet(f"background:transparent; color:{DIM}")
        top.addWidget(il); top.addWidget(nl); top.addStretch()
        lay.addLayout(top)

        self._val = QLabel("--/--")
        self._val.setFont(QFont(FONT, 20, QFont.Weight.Bold))
        self._val.setStyleSheet(f"background:transparent; color:{PURPLE};")
        lay.addWidget(self._val)

        ul = QLabel("mmHg"); ul.setFont(QFont(FONT, 8)); ul.setStyleSheet(f"background:transparent; color:{DIM}")
        lay.addWidget(ul)

        btn = QPushButton("⌨  입력"); btn.setFixedHeight(26)
        btn.setFont(QFont(FONT, 8))
        btn.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{PURPLE};
                border:1px solid {PURPLE}; border-radius:4px;}}
            QPushButton:pressed {{background:rgba(200,123,255,.15);}}
        """)
        btn.clicked.connect(self._open); lay.addWidget(btn)

    def _open(self):
        dlg = BpDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            bp = dlg.result_bp()
            self._val.setText(bp)
            try:
                s,d = [int(x) for x in bp.split("/")]
                c = RED if (s>180 or s<80 or d>110 or d<50) else (YELLOW if (s>140 or d>90) else PURPLE)
            except: c = PURPLE
            self._val.setStyleSheet(f"background:transparent; color:{c};")
            self.set_color(c)


# ══════════════════════════════════════════════════════════
#  혈압 키패드 다이얼로그
# ══════════════════════════════════════════════════════════
class BpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("혈압 입력"); self.setFixedSize(300, 400)
        self.setStyleSheet(f"background:{PANEL}; color:{TEXT};")
        self._sys=""; self._dia=""; self._mode="sys"
        lay = QVBoxLayout(self); lay.setSpacing(8)

        self._title = QLabel("수축기 혈압")
        self._title.setFont(QFont(FONT, 12, QFont.Weight.Bold))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet(f"color:{NEON};")
        lay.addWidget(self._title)

        self._disp = QLabel("___")
        self._disp.setFont(QFont(FONT, 32, QFont.Weight.Bold))
        self._disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._disp.setStyleSheet(f"color:{TEXT};")
        lay.addWidget(self._disp)

        grid = QGridLayout(); grid.setSpacing(6)
        for i,(t,v) in enumerate([
            ("7",7),("8",8),("9",9),
            ("4",4),("5",5),("6",6),
            ("1",1),("2",2),("3",3),
            ("⌫",-1),("0",0),("OK",-2),
        ]):
            b = QPushButton(t); b.setFixedHeight(48)
            b.setFont(QFont(FONT, 14, QFont.Weight.Bold))
            c = RED if t=="⌫" else (GREEN if t=="OK" else NEON)
            b.setStyleSheet(f"""
                QPushButton {{background:{PANEL2}; color:{c};
                    border:1px solid {c}; border-radius:6px;}}
                QPushButton:pressed {{background:#0a1f3a;}}
            """)
            b.clicked.connect(lambda _,vv=v: self._key(vv))
            grid.addWidget(b, i//3, i%3)
        lay.addLayout(grid)

    def _key(self, v):
        if v==-1:
            if self._mode=="sys": self._sys=self._sys[:-1]
            else: self._dia=self._dia[:-1]
        elif v==-2:
            if self._mode=="sys" and self._sys:
                self._mode="dia"
                self._title.setText("이완기 혈압")
                self._title.setStyleSheet(f"color:{ORANGE};")
            elif self._mode=="dia" and self._dia:
                self.accept(); return
        else:
            if self._mode=="sys" and len(self._sys)<3: self._sys+=str(v)
            elif self._mode=="dia" and len(self._dia)<3: self._dia+=str(v)
        cur = self._sys if self._mode=="sys" else self._dia
        self._disp.setText(cur or "___")

    def result_bp(self):
        return f"{self._sys}/{self._dia}" if self._sys and self._dia else "--/--"


# ══════════════════════════════════════════════════════════
#  바이탈 패널
# ══════════════════════════════════════════════════════════
class VitalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._running = False
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(5)

        # Start / Stop
        ctrl = QHBoxLayout(); ctrl.setSpacing(8)
        self._led = QLabel("●"); self._led.setFont(QFont(FONT, 13))
        self._led.setFixedWidth(18)
        self._led.setStyleSheet(f"color:{DIM2}; background:transparent;")
        self._stat = QLabel("센서 대기")
        self._stat.setFont(QFont(FONT, 9))
        self._stat.setStyleSheet(f"color:{DIM}; background:transparent;")
        self._s_btn = self._cbtn("▶  START", GREEN)
        self._e_btn = self._cbtn("■  STOP",  RED)
        self._e_btn.setEnabled(False)
        self._s_btn.clicked.connect(self._start)
        self._e_btn.clicked.connect(self._stop)
        ctrl.addWidget(self._led); ctrl.addWidget(self._stat); ctrl.addStretch()
        ctrl.addWidget(self._s_btn); ctrl.addWidget(self._e_btn)
        root.addLayout(ctrl)

        # 카드 5종
        self._hr   = VitalCard("♥","심박수",  "HR",   "bpm", 72,   RED,    0)
        self._spo2 = VitalCard("◉","산소포화도","SpO2","%",   98,   TEAL,   0)
        self._rr   = VitalCard("~","호흡수",  "RR",   "/min",16,   NEON,   0)
        self._temp = VitalCard("🌡","체온",    "TEMP", "°C",  36.5, ORANGE, 1)
        self._bp   = BpCard()

        cards = QHBoxLayout(); cards.setSpacing(5)
        for c in [self._hr, self._spo2, self._rr, self._temp, self._bp]:
            cards.addWidget(c)
        root.addLayout(cards)

        self._sim = QTimer(self); self._sim.timeout.connect(self._simulate)

    def _cbtn(self, t, c):
        b = QPushButton(t); b.setFixedHeight(30)
        b.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{c};
                border:1px solid {c}; border-radius:5px; padding:0 10px;}}
            QPushButton:pressed {{background:rgba(255,255,255,.07);}}
            QPushButton:disabled {{color:{DIM2}; border-color:{DIM2};}}
        """)
        return b

    def _start(self):
        self._running=True
        self._led.setStyleSheet(f"color:{GREEN}; background:transparent;")
        self._stat.setText("측정 중"); self._stat.setStyleSheet(f"color:{GREEN}; background:transparent;")
        self._s_btn.setEnabled(False); self._e_btn.setEnabled(True)
        self._sim.start(2000)

    def _stop(self):
        self._running=False
        self._led.setStyleSheet(f"color:{DIM2}; background:transparent;")
        self._stat.setText("센서 대기"); self._stat.setStyleSheet(f"color:{DIM}; background:transparent;")
        self._s_btn.setEnabled(True); self._e_btn.setEnabled(False)
        self._sim.stop()

    def _simulate(self):
        import random
        self._hr.update_value(  60+random.randint(0,70))
        self._spo2.update_value(92+random.randint(0,8))
        self._rr.update_value(  12+random.randint(0,10))
        self._temp.update_value(35.0+random.uniform(0,4.0))

    def update_vital(self, key, val):
        {"HR":self._hr,"SpO2":self._spo2,"RR":self._rr,"TEMP":self._temp}.get(key, type("",(),{"update_value":lambda s,v:None})()).update_value(val)


# ══════════════════════════════════════════════════════════
#  카메라 패널
# ══════════════════════════════════════════════════════════
class CameraPanel(GlowCard):
    def __init__(self, index=0):
        super().__init__(color=NEON)
        self._idx=index; self._cap=None
        lay = QVBoxLayout(self); lay.setContentsMargins(10,10,10,8); lay.setSpacing(5)

        hdr = QHBoxLayout()
        tl = QLabel("📷  환자 카메라")
        tl.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        tl.setStyleSheet(f"background:transparent; color:{TEXT}")
        self._cstat = QLabel("대기"); self._cstat.setFont(QFont(FONT, 8))
        self._cstat.setStyleSheet(f"background:transparent; color:{DIM}")
        hdr.addWidget(tl); hdr.addStretch(); hdr.addWidget(self._cstat)
        lay.addLayout(hdr)

        self._view = QLabel()
        self._view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._view.setStyleSheet(f"background:{BG}; border-radius:5px; color:{DIM};")
        self._view.setText("카메라 미연결")
        self._view.setFont(QFont(FONT, 10))
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self._view, stretch=1)

        btns = QHBoxLayout(); btns.setSpacing(6)
        self._on  = self._mbtn("▶ ON",  GREEN)
        self._off = self._mbtn("■ OFF", RED); self._off.setEnabled(False)
        self._on.clicked.connect(self._start)
        self._off.clicked.connect(self._stop_cam)
        btns.addWidget(self._on); btns.addWidget(self._off)
        lay.addLayout(btns)

        self._timer = QTimer(self); self._timer.timeout.connect(self._grab)

    def _mbtn(self, t, c):
        b = QPushButton(t); b.setFixedHeight(26); b.setFont(QFont(FONT, 8))
        b.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{c}; border:1px solid {c}; border-radius:4px;}}
            QPushButton:pressed {{background:rgba(255,255,255,.07);}}
            QPushButton:disabled {{color:{DIM2}; border-color:{DIM2};}}
        """)
        return b

    def _start(self):
        try:
            import cv2
            self._cap = cv2.VideoCapture(self._idx)
            if not self._cap.isOpened():
                self._view.setText("카메라를 열 수 없습니다"); return
            self._cstat.setText("● LIVE")
            self._cstat.setStyleSheet(f"background:transparent; color:{GREEN};")
            self._on.setEnabled(False); self._off.setEnabled(True)
            self.set_color(GREEN); self._timer.start(33)
        except ImportError:
            self._view.setText("pip install opencv-python")

    def _stop_cam(self):
        self._timer.stop()
        if self._cap: self._cap.release(); self._cap=None
        self._cstat.setText("대기"); self._cstat.setStyleSheet(f"background:transparent; color:{DIM};")
        self._on.setEnabled(True); self._off.setEnabled(False)
        self.set_color(NEON); self._view.setText("카메라 미연결")

    def _grab(self):
        if not self._cap: return
        import cv2
        ret, frame = self._cap.read()
        if not ret: return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h,w,ch = frame.shape
        img = QImage(frame.data, w, h, ch*w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._view.width(), self._view.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self._view.setPixmap(pix)


# ══════════════════════════════════════════════════════════
#  AVPU 글로우 버튼
# ══════════════════════════════════════════════════════════
#  AVPU 글라스 카드 버튼  (Car-HMI 스타일)
# ══════════════════════════════════════════════════════════
class AvpuButton(QWidget):
    """
    글라스모피즘 카드 버튼.
    - 상단 라이트 하이라이트 → 유리 광택
    - 블루~시안 그라디언트 배경
    - 아이콘 크게 (중앙 상단) + 텍스트 하단
    - A V P U 뱃지 pill 형태
    """
    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self._pressed  = False
        self._hover    = False
        self._pulse    = 0.0; self._pdir = 1
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        t = QTimer(self); t.timeout.connect(self._anim); t.start(40)

    def _anim(self):
        self._pulse += 0.03 * self._pdir
        if self._pulse >= 1: self._pdir = -1
        if self._pulse <= 0: self._pdir =  1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, r = self.width(), self.height(), 18

        scale = 0.96 if self._pressed else 1.0
        ox = w * (1 - scale) / 2; oy = h * (1 - scale) / 2
        rw = w * scale;            rh = h * scale

        # ── 외부 소프트 글로우 ──────────────────────────
        glow_a = int(40 + 30 * self._pulse) if not self._pressed else 20
        for i in range(5, 0, -1):
            a = max(0, glow_a - i * 7)
            gp = QPen(QColor(30, 160, 255, a)); gp.setWidth(i * 2)
            p.setPen(gp); p.setBrush(Qt.BrushStyle.NoBrush)
            m = ox + i
            p.drawRoundedRect(QRectF(m, oy+i, rw-i*2, rh-i*2), r, r)

        # ── 배경 그라디언트 (블루~딥블루) ──────────────
        bg = QLinearGradient(ox, oy, ox, oy + rh)
        if self._pressed:
            bg.setColorAt(0, QColor(0, 100, 210))
            bg.setColorAt(1, QColor(0,  50, 140))
        else:
            bg.setColorAt(0, QColor(10, 130, 255))
            bg.setColorAt(1, QColor(0,  60, 180))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(ox, oy, rw, rh), r, r)

        # ── 상단 유리 광택 (흰색 반투명 호) ─────────────
        glass = QLinearGradient(ox, oy, ox, oy + rh * 0.45)
        glass.setColorAt(0,   QColor(255, 255, 255, 70))
        glass.setColorAt(0.5, QColor(255, 255, 255, 18))
        glass.setColorAt(1,   QColor(255, 255, 255, 0))
        p.setBrush(QBrush(glass))
        pp = QPainterPath()
        pp.addRoundedRect(QRectF(ox, oy, rw, rh * 0.5), r, r)
        p.drawPath(pp)

        # ── 테두리 (옅은 흰) ─────────────────────────────
        p.setPen(QPen(QColor(255, 255, 255, 55), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(ox+1, oy+1, rw-2, rh-2), r, r)

        # ── 아이콘 ───────────────────────────────────────
        p.setPen(QPen(QColor(255, 255, 255, 230)))
        p.setFont(QFont(FONT, 22))
        p.drawText(QRectF(ox, oy + 4, rw, rh * 0.40),
                   Qt.AlignmentFlag.AlignCenter, "🧠")

        # ── 주 텍스트 ────────────────────────────────────
        p.setFont(QFont(FONT, 12, QFont.Weight.Bold))
        p.setPen(QPen(QColor(255, 255, 255)))
        p.drawText(QRectF(ox, oy + rh * 0.44, rw, rh * 0.20),
                   Qt.AlignmentFlag.AlignCenter, "AVPU")
        p.setFont(QFont(FONT, 8))
        p.setPen(QPen(QColor(200, 230, 255)))
        p.drawText(QRectF(ox, oy + rh * 0.60, rw, rh * 0.14),
                   Qt.AlignmentFlag.AlignCenter, "의식 수준 확인")

        # ── A V P U 뱃지 ────────────────────────────────
        bw = (rw - 24) / 4; bh = 20; by = oy + rh - bh - 10
        for i, (lt, lc) in enumerate([
            ("A", QColor(0,230,120)),
            ("V", QColor(255,220,0)),
            ("P", QColor(255,140,0)),
            ("U", QColor(255,60,60)),
        ]):
            bx = ox + 6 + i * (bw + 4)
            pill = QColor(lc); pill.setAlpha(55)
            p.setBrush(QBrush(pill))
            p.setPen(QPen(lc, 1))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), bh/2, bh/2)
            p.setFont(QFont(FONT, 8, QFont.Weight.Bold))
            p.setPen(QPen(lc))
            p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, lt)

    def mousePressEvent(self, _):   self._pressed = True;  self.update()
    def mouseReleaseEvent(self, e):
        self._pressed = False; self.update()
        if self.rect().contains(e.position().toPoint()): self._on_click()
    def enterEvent(self, _): self._hover = True;  self.update()
    def leaveEvent(self, _): self._hover = False; self.update()


# ══════════════════════════════════════════════════════════
#  응급 시나리오 버튼  (Car-HMI 글라스 카드)
# ══════════════════════════════════════════════════════════
class EmergBtn(QWidget):
    """
    글라스 카드 스타일:
    - 색상별 그라디언트 배경 (진→연)
    - 상단 유리 광택
    - 아이콘 좌측 원형 배지 + 텍스트 우측
    - 눌리면 살짝 스케일 다운
    """
    # 색상별 그라디언트 쌍 (top, bottom)
    _GRADS = {
        "#ff3b3b": ("#c0001a", "#7a0010"),   # RED  - CPR
        "#ff8c00": ("#c05800", "#7a3000"),   # ORANGE - 출혈
        "#ffe033": ("#9a8000", "#5a4a00"),   # YELLOW - 화상
        "#00e5c8": ("#007a6a", "#003d35"),   # TEAL  - 골절
        "#0af":    ("#006aaa", "#003366"),   # NEON  - 익수
        "#c87bff": ("#6a00cc", "#3a0077"),   # PURPLE- 기도
    }

    def __init__(self, icon, name, color, on_click, parent=None):
        super().__init__(parent)
        self._icon     = icon
        self._name     = name
        self._color    = QColor(color)
        self._pressed  = False
        self._on_click = on_click
        grad = self._GRADS.get(color, ("#0a3060", "#041830"))
        self._g_top = QColor(grad[0])
        self._g_bot = QColor(grad[1])
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, r = self.width(), self.height(), 14

        scale = 0.95 if self._pressed else 1.0
        ox = w*(1-scale)/2; oy = h*(1-scale)/2
        rw = w*scale;        rh = h*scale

        # ── 소프트 글로우 ─────────────────────────────────
        c = self._color
        for i in range(4, 0, -1):
            a = (15 + i*10) if not self._pressed else 5
            gp = QPen(QColor(c.red(), c.green(), c.blue(), a)); gp.setWidth(i*2)
            p.setPen(gp); p.setBrush(Qt.BrushStyle.NoBrush)
            m = ox+i
            p.drawRoundedRect(QRectF(m, oy+i, rw-i*2, rh-i*2), r, r)

        # ── 그라디언트 배경 ───────────────────────────────
        bg = QLinearGradient(ox, oy, ox+rw*0.6, oy+rh)
        t_ = self._g_top if not self._pressed else self._g_bot
        b_ = self._g_bot
        bg.setColorAt(0, t_); bg.setColorAt(1, b_)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(ox, oy, rw, rh), r, r)

        # ── 유리 광택 ─────────────────────────────────────
        glass = QLinearGradient(ox, oy, ox, oy+rh*0.5)
        glass.setColorAt(0,   QColor(255,255,255, 45))
        glass.setColorAt(0.6, QColor(255,255,255,  8))
        glass.setColorAt(1,   QColor(255,255,255,  0))
        p.setBrush(QBrush(glass))
        gp2 = QPainterPath()
        gp2.addRoundedRect(QRectF(ox, oy, rw, rh*0.55), r, r)
        p.drawPath(gp2)

        # ── 테두리 ───────────────────────────────────────
        p.setPen(QPen(QColor(255,255,255, 40), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(ox+1, oy+1, rw-2, rh-2), r, r)

        # ── 좌측 원형 아이콘 배지 ─────────────────────────
        cr = rh * 0.30
        cx = ox + cr + 10; cy = oy + rh/2
        badge_bg = QColor(255, 255, 255, 35)
        p.setBrush(QBrush(badge_bg))
        p.setPen(QPen(QColor(255,255,255,60), 1))
        p.drawEllipse(QRectF(cx-cr, cy-cr, cr*2, cr*2))
        p.setFont(QFont(FONT, int(cr * 0.85)))
        p.setPen(QPen(QColor(255,255,255,240)))
        p.drawText(QRectF(cx-cr, cy-cr, cr*2, cr*2), Qt.AlignmentFlag.AlignCenter, self._icon)

        # ── 텍스트 ───────────────────────────────────────
        tx = cx + cr + 10; tw = rw - (tx - ox) - 8
        p.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        p.setPen(QPen(QColor(255,255,255,240)))
        p.drawText(QRectF(tx, oy, tw, rh), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._name)

    def mousePressEvent(self, _): self._pressed=True; self.update()
    def mouseReleaseEvent(self, e):
        self._pressed=False; self.update()
        if self.rect().contains(e.position().toPoint()): self._on_click()


# ══════════════════════════════════════════════════════════
#  메인 화면
# ══════════════════════════════════════════════════════════
class MainScreen(QWidget):
    def __init__(self, nav):
        super().__init__()
        self._nav = nav

        # 격자 배경
        self._bg = GridBg(self)
        self._bg.setGeometry(0, 0, W, H)

        root = QVBoxLayout(self); root.setContentsMargins(8,6,8,6); root.setSpacing(5)
        root.addWidget(self._header())
        root.addWidget(self._vitals_row())

        mid = QHBoxLayout(); mid.setSpacing(5)
        mid.addWidget(self._camera_block(), stretch=4)
        mid.addWidget(self._avpu_block(),   stretch=3)
        mid.addWidget(self._emerg_block(),  stretch=5)
        root.addLayout(mid, stretch=1)
        root.addWidget(self._footer())

    def resizeEvent(self, e):
        self._bg.setGeometry(0, 0, self.width(), self.height())

    # ── 헤더 ──────────────────────────────────────────────
    def _header(self):
        f = QWidget(); f.setFixedHeight(50)
        f.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(f); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)

        # 로고
        logo_lbl = QLabel()
        logo_path = os.path.join(HERE, "logo.png")
        pix = QPixmap(logo_path)
        if not pix.isNull():
            pix = pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("⚓"); logo_lbl.setFont(QFont(FONT, 18, QFont.Weight.Bold))
        logo_lbl.setFixedWidth(42); logo_lbl.setStyleSheet("background:transparent; color:#fff;")

        # 구분선
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(36); sep.setStyleSheet(f"color:{NEON2};")

        title_col = QVBoxLayout(); title_col.setSpacing(1)
        tl = QLabel("MDTS"); tl.setFont(QFont(FONT, 16, QFont.Weight.Bold))
        tl.setStyleSheet(f"background:transparent; color:{NEON}; letter-spacing:4px;")
        sub = QLabel("Maritime Digital Triage System  ·  비의료인용")
        sub.setFont(QFont(FONT, 8)); sub.setStyleSheet(f"background:transparent; color:{DIM};")
        title_col.addWidget(tl); title_col.addWidget(sub)

        lay.addWidget(logo_lbl); lay.addWidget(sep); lay.addLayout(title_col); lay.addStretch()

        # 시계
        self._clk = QLabel(); self._clk.setFont(QFont(FONT, 11))
        self._clk.setStyleSheet(f"background:transparent; color:{NEON};")
        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000); self._tick()
        lay.addWidget(self._clk); lay.addSpacing(10)

        # SOS
        sos = self._sos_btn()
        lay.addWidget(sos)
        return f

    def _tick(self):
        self._clk.setText(QDateTime.currentDateTime().toString("yyyy-MM-dd  HH:mm:ss"))

    def _sos_btn(self):
        btn = QPushButton("  🆘  SOS  "); btn.setFixedHeight(36)
        btn.setFont(QFont(FONT, 10, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{background:{RED2}; color:white;
                border:1px solid {RED}; border-radius:6px; letter-spacing:2px;}}
            QPushButton:pressed {{background:#991010;}}
        """)
        btn.clicked.connect(lambda: self._nav(3)); return btn

    # ── 바이탈 행 ──────────────────────────────────────────
    def _vitals_row(self):
        self._vital_panel = VitalPanel()
        return self._vital_panel

    # ── 카메라 ────────────────────────────────────────────
    def _camera_block(self):
        self._cam = CameraPanel(); return self._cam

    # ── AVPU 블록 ─────────────────────────────────────────
    def _avpu_block(self):
        wrap = QWidget(); wrap.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(wrap); lay.setContentsMargins(0,0,0,0); lay.setSpacing(3)
        hint = QLabel("▼ 탭하여 평가 시작"); hint.setFont(QFont(FONT, 8))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"background:transparent; color:{DIM};")
        btn = AvpuButton(lambda: self._nav(1))
        lay.addWidget(hint); lay.addWidget(btn, stretch=1)
        return wrap

    # ── 응급 버튼 그리드 ──────────────────────────────────
    def _emerg_block(self):
        wrap = GlowCard(color=NEON_DIM)
        lay = QVBoxLayout(wrap); lay.setContentsMargins(10,8,10,8); lay.setSpacing(5)
        ttl = QLabel("응급 처치"); ttl.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setStyleSheet(f"background:transparent; color:{DIM};")
        lay.addWidget(ttl)

        grid = QGridLayout(); grid.setSpacing(5)
        items = [
            ("💔","심폐소생술",  RED,    2),
            ("🩸","출혈 처치",   ORANGE, 4),
            ("🔥","화상 처치",   YELLOW, 4),
            ("🦴","골절/탈구",   TEAL,   4),
            ("🌊","익수/저체온", NEON,   4),
            ("😮","기도 폐쇄",   PURPLE, 4),
        ]
        for i,(ico,name,c,pg) in enumerate(items):
            b = EmergBtn(ico, name, c, lambda _, p=pg: self._nav(p))
            b.setFixedHeight(50); grid.addWidget(b, i//2, i%2)
        lay.addLayout(grid)
        return wrap

    # ── 푸터 ──────────────────────────────────────────────
    def _footer(self):
        f = QWidget(); f.setFixedHeight(22); f.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(f); lay.setContentsMargins(4,0,4,0)
        w = QLabel("⚠  이 가이드는 전문 의료를 대체하지 않습니다 — 가능한 빨리 의료진에게 연락하십시오")
        w.setFont(QFont(FONT, 8)); w.setStyleSheet(f"background:transparent; color:{YELLOW};")
        r = QLabel("MDTS v2  ·  1024×600")
        r.setFont(QFont(FONT, 8))
        r.setAlignment(Qt.AlignmentFlag.AlignRight)
        r.setStyleSheet(f"background:transparent; color:{DIM};")
        lay.addWidget(w); lay.addStretch(); lay.addWidget(r); return f


# ══════════════════════════════════════════════════════════
#  AVPU 화면
# ══════════════════════════════════════════════════════════
class AvpuScreen(QWidget):
    STEPS=[
        ("A","Alert — 의식 명료",     GREEN,  ["눈을 뜨고 있는가?","말을 걸면 즉시 대답하는가?","시간·장소·자신의 이름을 아는가?","자발적으로 움직이는가?"],"모두 해당 → A(정상). 하나라도 아니면 V로 이동"),
        ("V","Voice — 음성 반응",     YELLOW, ["크게 이름을 부르거나 '눈 떠 보세요!' 말하기","눈을 뜨는가? / 손을 움직이는가?","간단한 명령에 반응하는가?"],"반응 있으면 → V. 없으면 P 확인"),
        ("P","Pain — 통증 반응",      ORANGE, ["흉골 중앙을 손가락 관절로 강하게 문지르기","눈썹 위 눈두덩이를 강하게 누르기","눈꺼풀이 떨리거나 손발을 움츠리는가?"],"반응 있으면 → P. 없으면 U"),
        ("U","Unresponsive — 무반응", RED,    ["A·V·P 모두 반응 없음","즉시 호흡·맥박 확인","AED 위치 확인 및 구조 요청","CPR 또는 회복 자세 즉시 시작"],"→ CPR 화면으로 이동 또는 SOS 요청"),
    ]
    def __init__(self, nav):
        super().__init__()
        self._nav=nav; self._step=0
        self._bg=GridBg(self); self._bg.setGeometry(0,0,W,H)
        self._root=QVBoxLayout(self); self._root.setContentsMargins(10,8,10,8); self._root.setSpacing(6)
        self._root.addWidget(self._topbar())
        self._card=GlowCard(color=GREEN); self._root.addWidget(self._card,stretch=1)
        self._btm=QHBoxLayout(); self._root.addLayout(self._btm)
        self._refresh()

    def resizeEvent(self,e): self._bg.setGeometry(0,0,self.width(),self.height())

    def _topbar(self):
        bar=QWidget(); bar.setFixedHeight(42); bar.setStyleSheet("background:transparent;")
        lay=QHBoxLayout(bar); lay.setContentsMargins(0,0,0,0)
        b=self._nb("← 홈",NEON,h=34,w=70); b.clicked.connect(lambda:self._nav(0))
        lay.addWidget(b); lay.addStretch()
        t=QLabel("AVPU  의식 수준 평가"); t.setFont(QFont(FONT,13,QFont.Weight.Bold))
        t.setStyleSheet(f"background:transparent; color:{TEXT};"); lay.addWidget(t); lay.addStretch()
        self._dots=[]
        for s in self.STEPS:
            d=QLabel("●"); d.setFont(QFont(FONT,14)); d.setStyleSheet(f"color:{DIM2}; background:transparent;")
            self._dots.append((d,s[2])); lay.addWidget(d)
        return bar

    def _refresh(self):
        for i,(d,c) in enumerate(self._dots):
            d.setStyleSheet(f"color:{c}; background:transparent;" if i==self._step else f"color:{DIM2}; background:transparent;")
        lo=self._card.layout()
        if lo:
            while lo.count():
                item=lo.takeAt(0)
                if item.widget(): item.widget().setParent(None)
            QWidget().setLayout(lo)
        lt,title,color,checks,note=self.STEPS[self._step]
        self._card.set_color(color)
        cl=QVBoxLayout(self._card); cl.setContentsMargins(22,16,22,16); cl.setSpacing(10)
        top=QHBoxLayout(); top.setSpacing(14)
        big=QLabel(lt); big.setFont(QFont(FONT,56,QFont.Weight.Bold))
        big.setStyleSheet(f"background:transparent; color:{color};"); big.setFixedWidth(70)
        info=QVBoxLayout()
        t1=QLabel(title); t1.setFont(QFont(FONT,16,QFont.Weight.Bold)); t1.setStyleSheet(f"background:transparent; color:{color};")
        t2=QLabel(f"단계 {self._step+1} / {len(self.STEPS)}"); t2.setFont(QFont(FONT,9)); t2.setStyleSheet(f"background:transparent; color:{DIM};")
        info.addWidget(t1); info.addWidget(t2); top.addWidget(big); top.addLayout(info); cl.addLayout(top)
        sep=QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(f"color:{color};"); cl.addWidget(sep)
        for chk in checks:
            row=QHBoxLayout(); row.setSpacing(8)
            bul=QLabel("▶"); bul.setFont(QFont(FONT,10)); bul.setStyleSheet(f"background:transparent; color:{color};"); bul.setFixedWidth(16)
            txt=QLabel(chk); txt.setFont(QFont(FONT,12)); txt.setStyleSheet(f"background:transparent; color:{TEXT};")
            row.addWidget(bul); row.addWidget(txt); cl.addLayout(row)
        cl.addStretch()
        sep2=QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet(f"color:{DIM2};"); cl.addWidget(sep2)
        nt=QLabel(note); nt.setFont(QFont(FONT,11)); nt.setStyleSheet(f"background:transparent; color:{YELLOW};"); cl.addWidget(nt)
        while self._btm.count():
            item=self._btm.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        if self._step>0:
            pb=self._nb("◀  이전",DIM,h=44); pb.clicked.connect(self._prev); self._btm.addWidget(pb)
        self._btm.addStretch()
        rb=self._nb(f'✔  "{lt}" 기록',color,h=44); rb.clicked.connect(lambda:self._nav(0)); self._btm.addWidget(rb)
        if self._step<len(self.STEPS)-1:
            nb=self._nb("다음 ▶",NEON,h=44); nb.clicked.connect(self._next); self._btm.addWidget(nb)
        else:
            cb=self._nb("CPR →",RED,h=44); cb.clicked.connect(lambda:self._nav(2)); self._btm.addWidget(cb)

    def _nb(self,t,c,h=44,w=None):
        b=QPushButton(t)
        if w: b.setFixedWidth(w)
        b.setFixedHeight(h); b.setFont(QFont(FONT,10,QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"QPushButton{{background:transparent;color:{c};border:1px solid {c};border-radius:7px;padding:0 14px;}} QPushButton:pressed{{background:rgba(255,255,255,.07);}}")
        return b
    def _next(self):
        if self._step<len(self.STEPS)-1: self._step+=1; self._refresh()
    def _prev(self):
        if self._step>0: self._step-=1; self._refresh()
    def reset(self): self._step=0; self._refresh()


# ══════════════════════════════════════════════════════════
#  CPR 화면
# ══════════════════════════════════════════════════════════
class CprScreen(QWidget):
    GUIDE=[
        ("1","안전·반응 확인",  ["주변 위험 제거","어깨 두드리며 '괜찮으세요?' 외침","반응 없으면 도움+AED 요청"],NEON),
        ("2","기도 확보",       ["단단한 바닥에 눕힘","머리 젖히고 턱 들어올리기","10초 이내 호흡 확인"],TEAL),
        ("3","가슴 압박 30회",  ["흉골 중앙에 양손 깍지","5~6cm 깊이 수직 압박","100~120회/분","30회→인공호흡 2회"],ORANGE),
        ("4","인공호흡 2회",    ["머리 젖히기+코 막고 1초 불기","가슴 올라오는지 확인","2회→압박 반복","AED 즉시 사용"],RED),
    ]
    def __init__(self, nav):
        super().__init__()
        self._nav=nav; self._count=0
        self._bg=GridBg(self); self._bg.setGeometry(0,0,W,H)
        root=QVBoxLayout(self); root.setContentsMargins(8,8,8,8); root.setSpacing(6)
        root.addWidget(self._topbar())
        body=QHBoxLayout(); body.setSpacing(8)
        body.addWidget(self._counter(),stretch=3)
        body.addWidget(self._guide_panel(),stretch=7)
        root.addLayout(body)

    def resizeEvent(self,e): self._bg.setGeometry(0,0,self.width(),self.height())

    def _topbar(self):
        bar=QWidget(); bar.setFixedHeight(42); bar.setStyleSheet("background:transparent;")
        lay=QHBoxLayout(bar); lay.setContentsMargins(0,0,0,0)
        b=QPushButton("← 홈"); b.setFixedSize(70,32); b.setFont(QFont(FONT,9))
        b.setStyleSheet(f"QPushButton{{background:transparent;color:{NEON};border:1px solid {NEON};border-radius:5px;}} QPushButton:pressed{{background:rgba(0,170,255,.12);}}")
        b.clicked.connect(lambda:self._nav(0)); lay.addWidget(b); lay.addStretch()
        t=QLabel("💔  심폐소생술 (CPR) 가이드"); t.setFont(QFont(FONT,13,QFont.Weight.Bold))
        t.setStyleSheet(f"background:transparent; color:{RED};"); lay.addWidget(t); lay.addStretch()
        s=QPushButton("🆘 SOS"); s.setFixedSize(76,32); s.setFont(QFont(FONT,10,QFont.Weight.Bold))
        s.setStyleSheet(f"QPushButton{{background:{RED2};color:white;border:none;border-radius:5px;}} QPushButton:pressed{{background:#991010;}}")
        s.clicked.connect(lambda:self._nav(3)); lay.addWidget(s); return bar

    def _counter(self):
        f=GlowCard(color=RED); lay=QVBoxLayout(f); lay.setContentsMargins(12,12,12,12); lay.setSpacing(8)
        tl=QLabel("압박 카운터"); tl.setFont(QFont(FONT,10)); tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.setStyleSheet(f"background:transparent; color:{DIM};"); lay.addWidget(tl)
        self._cnt=QLabel("0"); self._cnt.setFont(QFont(FONT,52,QFont.Weight.Bold))
        self._cnt.setAlignment(Qt.AlignmentFlag.AlignCenter); self._cnt.setStyleSheet(f"background:transparent; color:{RED};"); lay.addWidget(self._cnt)
        sub=QLabel("/ 30회"); sub.setFont(QFont(FONT,11)); sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"background:transparent; color:{DIM};"); lay.addWidget(sub)
        press=QPushButton("압박!"); press.setFixedHeight(68); press.setFont(QFont(FONT,16,QFont.Weight.Bold))
        press.setStyleSheet(f"QPushButton{{background:#1a0000;color:{RED};border:2px solid {RED};border-radius:8px;}} QPushButton:pressed{{background:#330000;}}")
        press.clicked.connect(self._press); lay.addWidget(press)
        rst=QPushButton("초기화"); rst.setFixedHeight(28); rst.setFont(QFont(FONT,9))
        rst.setStyleSheet(f"QPushButton{{background:transparent;color:{DIM};border:1px solid {DIM2};border-radius:4px;}} QPushButton:pressed{{background:rgba(255,255,255,.05);}}")
        rst.clicked.connect(self._reset); lay.addWidget(rst)
        self._hint=QLabel("100~120회/분 유지"); self._hint.setFont(QFont(FONT,9))
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter); self._hint.setStyleSheet(f"background:transparent; color:{YELLOW};"); lay.addWidget(self._hint)
        lay.addStretch(); return f

    def _guide_panel(self):
        f=GlowCard(color=NEON_DIM); lay=QVBoxLayout(f); lay.setContentsMargins(14,12,14,12); lay.setSpacing(7)
        tl=QLabel("단계별 가이드"); tl.setFont(QFont(FONT,11,QFont.Weight.Bold)); tl.setStyleSheet(f"background:transparent; color:{DIM};"); lay.addWidget(tl)
        sep=QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(f"color:{DIM2};"); lay.addWidget(sep)
        for num,title,checks,color in self.GUIDE:
            sf=GlowCard(color=color)
            sl=QVBoxLayout(sf); sl.setContentsMargins(10,7,10,7); sl.setSpacing(3)
            h=QHBoxLayout()
            for t,s,c in [(f"STEP {num}",9,color),(title,10,TEXT)]:
                lb=QLabel(t); lb.setFont(QFont(FONT,s,QFont.Weight.Bold if c==color else QFont.Weight.Normal))
                lb.setStyleSheet(f"background:transparent; color:{c};"); h.addWidget(lb)
            sl.addLayout(h)
            for chk in checks:
                r=QHBoxLayout(); r.setSpacing(6)
                bl=QLabel("•"); bl.setFont(QFont(FONT,9)); bl.setStyleSheet(f"background:transparent; color:{color};")
                tx=QLabel(chk); tx.setFont(QFont(FONT,10)); tx.setStyleSheet(f"background:transparent; color:{DIM};")
                r.addWidget(bl); r.addWidget(tx); sl.addLayout(r)
            lay.addWidget(sf)
        lay.addStretch(); return f

    def _press(self):
        self._count=min(self._count+1,30); self._cnt.setText(str(self._count))
        if self._count>=30:
            self._cnt.setStyleSheet(f"background:transparent; color:{GREEN};"); self._hint.setText("→ 인공호흡 2회 실시!")
        else: self._cnt.setStyleSheet(f"background:transparent; color:{RED};")

    def _reset(self):
        self._count=0; self._cnt.setText("0"); self._cnt.setStyleSheet(f"background:transparent; color:{RED};"); self._hint.setText("100~120회/분 유지")


# ══════════════════════════════════════════════════════════
#  SOS 화면
# ══════════════════════════════════════════════════════════
class SosScreen(QWidget):
    def __init__(self, nav):
        super().__init__()
        self._nav=nav
        self._bg=GridBg(self); self._bg.setGeometry(0,0,W,H)
        root=QVBoxLayout(self); root.setContentsMargins(20,16,20,16); root.setSpacing(12)
        bk=QPushButton("← 홈으로"); bk.setFixedHeight(40); bk.setFont(QFont(FONT,10))
        bk.setStyleSheet(f"QPushButton{{background:transparent;color:{NEON};border:1px solid {NEON};border-radius:7px;}} QPushButton:pressed{{background:rgba(0,170,255,.12);}}")
        bk.clicked.connect(lambda:self._nav(0)); root.addWidget(bk)
        t=QLabel("🆘  구조 요청 / 비상 연락"); t.setFont(QFont(FONT,18,QFont.Weight.Bold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter); t.setStyleSheet(f"background:transparent; color:{RED};"); root.addWidget(t)
        for role,contact in [
            ("선박 선장 / 당직 사관","선내 인터폰  #01"),
            ("무선 통신실 (Radio Room)","채널 16  (조난 주파수)"),
            ("해양경찰 구조대","☎  122"),
            ("국제 조난 신호","MAYDAY × 3"),
        ]:
            card=GlowCard(color=RED); card.setFixedHeight(58)
            cl=QHBoxLayout(card); cl.setContentsMargins(18,0,18,0)
            rl=QLabel(role); rl.setFont(QFont(FONT,12)); rl.setStyleSheet(f"background:transparent; color:{TEXT};")
            vl=QLabel(contact); vl.setFont(QFont(FONT,13,QFont.Weight.Bold))
            vl.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
            vl.setStyleSheet(f"background:transparent; color:{RED};")
            cl.addWidget(rl); cl.addStretch(); cl.addWidget(vl); root.addWidget(card)
        root.addStretch()
        nt=QLabel("MAYDAY 교신: MAYDAY × 3 → 선박명 → 위치 → 인명 상황 → 필요 지원")
        nt.setFont(QFont(FONT,11)); nt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nt.setStyleSheet(f"background:transparent; color:{YELLOW};"); root.addWidget(nt)

    def resizeEvent(self,e): self._bg.setGeometry(0,0,self.width(),self.height())


# ══════════════════════════════════════════════════════════
#  메인 윈도우
# ══════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MDTS — Maritime Digital Triage System")
        self.setFixedSize(W, H)
        self._stack=QStackedWidget(); self.setCentralWidget(self._stack)
        self._screens=[MainScreen(self._go),AvpuScreen(self._go),CprScreen(self._go),SosScreen(self._go)]
        for s in self._screens: self._stack.addWidget(s)

    def _go(self, idx):
        if idx==1: self._screens[1].reset()
        self._stack.setCurrentIndex(idx)


def main():
    app=QApplication(sys.argv); app.setStyle("Fusion")
    w=MainWindow(); w.show(); sys.exit(app.exec())

if __name__=="__main__":
    main()
