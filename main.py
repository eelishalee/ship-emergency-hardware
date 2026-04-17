"""
선박 응급처치 가이드 — PyQt6 · 1024×600
화면 목록
  0: 메인 (바이탈 + 카메라 + 응급 메뉴)
  1: AVPU 의식 평가
  2: CPR 가이드
  3: SOS 화면
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QDialog, QDialogButtonBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QSize
from PyQt6.QtGui import QFont, QImage, QPixmap

SCREEN_W, SCREEN_H = 1024, 600

# ── 색상 팔레트 ────────────────────────────────────────────
BG      = "#0d1117"
PANEL   = "#161b22"
BORDER  = "#30363d"
TEXT    = "#e6edf3"
DIM     = "#8b949e"
RED     = "#f85149"
ORANGE  = "#fb8f44"
YELLOW  = "#e3b341"
GREEN   = "#3fb950"
BLUE    = "#58a6ff"
PURPLE  = "#bc8cff"
TEAL    = "#39d3bb"


# ── 헬퍼 ──────────────────────────────────────────────────
def lbl(text, size=11, bold=False, color=TEXT,
        align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
    w = QLabel(text)
    w.setFont(QFont("Malgun Gothic", size,
                    QFont.Weight.Bold if bold else QFont.Weight.Normal))
    w.setStyleSheet(f"color:{color}; background:transparent;")
    w.setAlignment(align)
    w.setWordWrap(True)
    return w


def hline():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{BORDER};")
    return f


def icon_btn(text, color, h=44, w=None):
    btn = QPushButton(text)
    if w:
        btn.setFixedWidth(w)
    btn.setFixedHeight(h)
    btn.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {color};
            border: 1px solid {color};
            border-radius: 7px;
        }}
        QPushButton:pressed {{ background: rgba(255,255,255,.08); }}
    """)
    return btn


# ══════════════════════════════════════════════════════════
#  혈압 키패드 다이얼로그
# ══════════════════════════════════════════════════════════
class BpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("혈압 입력")
        self.setFixedSize(320, 420)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._sys = ""
        self._dia = ""
        self._mode = "sys"   # sys → dia

        root = QVBoxLayout(self)
        root.setSpacing(10)

        self._display = lbl("수축기 입력", 13, bold=True, color=BLUE,
                            align=Qt.AlignmentFlag.AlignCenter)
        self._value   = lbl("___", 28, bold=True, color=TEXT,
                            align=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._display)
        root.addWidget(self._value)
        root.addWidget(hline())

        # 숫자 키패드
        grid = QGridLayout()
        grid.setSpacing(6)
        keys = [("7",7),("8",8),("9",9),
                ("4",4),("5",5),("6",6),
                ("1",1),("2",2),("3",3),
                ("⌫",-1),("0",0),("확인",-2)]
        for i, (txt, val) in enumerate(keys):
            btn = QPushButton(txt)
            btn.setFixedHeight(52)
            btn.setFont(QFont("Malgun Gothic", 14, QFont.Weight.Bold))
            c = RED if txt == "⌫" else (GREEN if txt == "확인" else BLUE)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{PANEL}; color:{c};
                    border:1px solid {BORDER}; border-radius:7px;
                }}
                QPushButton:pressed {{background:#1f2937;}}
            """)
            btn.clicked.connect(lambda _, v=val: self._key(v))
            grid.addWidget(btn, i // 3, i % 3)
        root.addLayout(grid)

    def _key(self, v):
        if v == -1:                           # 지우기
            if self._mode == "sys":
                self._sys = self._sys[:-1]
            else:
                self._dia = self._dia[:-1]
        elif v == -2:                         # 확인
            if self._mode == "sys" and self._sys:
                self._mode = "dia"
                self._display.setText("이완기 입력")
                self._display.setStyleSheet(f"color:{ORANGE}; background:transparent;")
            elif self._mode == "dia" and self._dia:
                self.accept()
                return
        else:
            if self._mode == "sys" and len(self._sys) < 3:
                self._sys += str(v)
            elif self._mode == "dia" and len(self._dia) < 3:
                self._dia += str(v)
        self._refresh()

    def _refresh(self):
        cur = self._sys if self._mode == "sys" else self._dia
        self._value.setText(cur or "___")

    def result_bp(self):
        return f"{self._sys}/{self._dia}" if self._sys and self._dia else "--/--"


# ══════════════════════════════════════════════════════════
#  바이탈 패널 (좌측 상단)
# ══════════════════════════════════════════════════════════
class VitalPanel(QFrame):
    """센서 Start/Stop + 바이탈 5종 + 혈압 키패드"""

    VITALS = [
        ("체온",     "°C",  "36.5",  ORANGE),
        ("산소포화도", "%",  "98",    TEAL),
        ("호흡수",   "/min","16",    BLUE),
        ("심박수",   "bpm", "72",    RED),
    ]

    def __init__(self):
        super().__init__()
        self._running = False
        self._tick_n  = 0
        self.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # 헤더 + Start/Stop
        hdr = QHBoxLayout()
        hdr.addWidget(lbl("바이탈 모니터", 11, bold=True, color=TEXT))
        hdr.addStretch()
        self._status_dot = lbl("●", 14, color=BORDER)
        hdr.addWidget(self._status_dot)
        root.addLayout(hdr)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._start_btn = icon_btn("▶  START", GREEN, h=36)
        self._stop_btn  = icon_btn("■  STOP",  RED,   h=36)
        self._stop_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start)
        self._stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        root.addLayout(btn_row)

        root.addWidget(hline())

        # 바이탈 4종
        self._val_labels = {}
        for name, unit, default, color in self.VITALS:
            row = QHBoxLayout()
            row.addWidget(lbl(name, 10, color=DIM))
            row.addStretch()
            v = lbl(f"{default} {unit}", 13, bold=True, color=color,
                    align=Qt.AlignmentFlag.AlignRight)
            self._val_labels[name] = (v, unit, color)
            row.addWidget(v)
            root.addLayout(row)

        root.addWidget(hline())

        # 혈압 (수동 입력)
        bp_row = QHBoxLayout()
        bp_row.addWidget(lbl("혈압", 10, color=DIM))
        bp_row.addStretch()
        self._bp_label = lbl("--/-- mmHg", 13, bold=True, color=PURPLE,
                             align=Qt.AlignmentFlag.AlignRight)
        bp_row.addWidget(self._bp_label)
        root.addLayout(bp_row)

        bp_btn = icon_btn("⌨  혈압 입력", PURPLE, h=34)
        bp_btn.clicked.connect(self._open_bp)
        root.addWidget(bp_btn)

        # 시뮬 타이머
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._simulate)

    # ── 센서 제어 ──────────────────────────────────────────
    def _start(self):
        self._running = True
        self._status_dot.setStyleSheet(f"color:{GREEN}; background:transparent;")
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._timer.start(2000)   # 2초마다 시뮬 갱신 (실제론 센서 콜백으로 교체)

    def _stop(self):
        self._running = False
        self._status_dot.setStyleSheet(f"color:{BORDER}; background:transparent;")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._timer.stop()

    # ── 시뮬 업데이트 (실제 센서 연동 시 이 부분을 교체) ──
    def _simulate(self):
        import random
        updates = {
            "체온":     (36.0 + random.uniform(0, 2.5),  "°C",  1, ORANGE),
            "산소포화도": (94  + random.randint(0, 6),      "%",   0, TEAL),
            "호흡수":   (12  + random.randint(0, 8),      "/min",0, BLUE),
            "심박수":   (60  + random.randint(0, 40),     "bpm", 0, RED),
        }
        for name, (val, unit, dec, color) in updates.items():
            txt = f"{val:.{dec}f} {unit}"
            lw, _, _ = self._val_labels[name]
            lw.setText(txt)

    def update_vital(self, name: str, value: str):
        """외부 센서 콜백에서 호출 — e.g. update_vital('심박수', '88 bpm')"""
        if name in self._val_labels:
            lw, unit, color = self._val_labels[name]
            lw.setText(value)

    # ── 혈압 다이얼로그 ────────────────────────────────────
    def _open_bp(self):
        dlg = BpDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._bp_label.setText(f"{dlg.result_bp()} mmHg")


# ══════════════════════════════════════════════════════════
#  카메라 패널 (우측 상단)
# ══════════════════════════════════════════════════════════
class CameraPanel(QFrame):
    """
    OpenCV 카메라 피드를 표시.
    카메라 미연결 시 대기 화면 표시.
    실제 연동: camera_index 파라미터로 cv2.VideoCapture(index) 사용.
    """

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self._cap   = None
        self._index = camera_index
        self._active = False

        self.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # 헤더
        hdr = QHBoxLayout()
        hdr.addWidget(lbl("📷  환자 카메라", 11, bold=True, color=TEXT))
        hdr.addStretch()
        self._cam_status = lbl("대기", 9, color=DIM)
        hdr.addWidget(self._cam_status)
        root.addLayout(hdr)

        # 영상 표시 영역
        self._view = QLabel()
        self._view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._view.setStyleSheet(f"background:#0a0a0a; border-radius:6px; color:{DIM};")
        self._view.setMinimumHeight(120)
        self._view.setText("카메라 미연결\n( START 후 표시 )")
        self._view.setFont(QFont("Malgun Gothic", 10))
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self._view, stretch=1)

        # 버튼
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._cam_start = icon_btn("▶  카메라 ON",  GREEN, h=34)
        self._cam_stop  = icon_btn("■  카메라 OFF", RED,   h=34)
        self._cam_stop.setEnabled(False)
        self._cam_start.clicked.connect(self._start_cam)
        self._cam_stop.clicked.connect(self._stop_cam)
        btn_row.addWidget(self._cam_start)
        btn_row.addWidget(self._cam_stop)
        root.addLayout(btn_row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._grab_frame)

    def _start_cam(self):
        try:
            import cv2
            self._cap = cv2.VideoCapture(self._index)
            if not self._cap.isOpened():
                self._view.setText("카메라를 열 수 없습니다")
                return
            self._active = True
            self._cam_status.setText("● LIVE")
            self._cam_status.setStyleSheet(f"color:{GREEN}; background:transparent;")
            self._cam_start.setEnabled(False)
            self._cam_stop.setEnabled(True)
            self._timer.start(33)   # ~30 fps
        except ImportError:
            self._view.setText("opencv-python 미설치\npip install opencv-python")

    def _stop_cam(self):
        self._timer.stop()
        if self._cap:
            self._cap.release()
            self._cap = None
        self._active = False
        self._cam_status.setText("대기")
        self._cam_status.setStyleSheet(f"color:{DIM}; background:transparent;")
        self._cam_start.setEnabled(True)
        self._cam_stop.setEnabled(False)
        self._view.setText("카메라 미연결\n( 카메라 ON 버튼으로 시작 )")

    def _grab_frame(self):
        if not self._cap:
            return
        import cv2
        ret, frame = self._cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._view.width(), self._view.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._view.setPixmap(pix)

    def closeEvent(self, e):
        self._stop_cam()
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════
#  메인 화면
# ══════════════════════════════════════════════════════════
class MainScreen(QWidget):
    def __init__(self, nav):
        super().__init__()
        self._nav = nav
        self.setStyleSheet(f"background:{BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(self._header())

        # 중단: [바이탈 | 카메라] 상단 절반 / [AVPU | 응급버튼 6개] 하단 절반
        top_half = QHBoxLayout()
        top_half.setSpacing(6)
        self._vital = VitalPanel()
        top_half.addWidget(self._vital, stretch=1)
        self._camera = CameraPanel(camera_index=0)
        top_half.addWidget(self._camera, stretch=1)
        root.addLayout(top_half, stretch=5)

        bot_half = QHBoxLayout()
        bot_half.setSpacing(6)
        bot_half.addWidget(self._avpu_btn_panel(), stretch=5)
        bot_half.addWidget(self._emergency_grid(),  stretch=5)
        root.addLayout(bot_half, stretch=4)

        root.addWidget(self._footer())

    # ── 헤더 ──────────────────────────────────────────────
    def _header(self):
        f = QFrame()
        f.setFixedHeight(50)
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:8px;"
        )
        lay = QHBoxLayout(f)
        lay.setContentsMargins(14, 0, 10, 0)

        lay.addWidget(lbl("⚓", 18, color=BLUE))
        lay.addSpacing(6)

        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(lbl("선박 응급처치 가이드", 13, bold=True))
        col.addWidget(lbl("비의료인용 · Ship First Aid", 9, color=DIM))
        lay.addLayout(col)
        lay.addStretch()

        self._clock = lbl("", 12, color=GREEN,
                          align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._clock.setFixedWidth(190)
        timer = QTimer(self)
        timer.timeout.connect(
            lambda: self._clock.setText(
                QDateTime.currentDateTime().toString("yyyy-MM-dd  HH:mm:ss")
            )
        )
        timer.start(1000)
        timer.timeout.emit()
        lay.addWidget(self._clock)
        lay.addSpacing(8)

        sos = QPushButton("🆘  SOS")
        sos.setFixedSize(90, 36)
        sos.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        sos.setStyleSheet(f"""
            QPushButton {{background:{RED}; color:white;
                          border:none; border-radius:7px;}}
            QPushButton:pressed {{background:#c0392b;}}
        """)
        sos.clicked.connect(lambda: self._nav(3))
        lay.addWidget(sos)
        return f

    # ── AVPU 대형 버튼 ────────────────────────────────────
    def _avpu_btn_panel(self):
        f = QFrame()
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        lay.addWidget(lbl("환자 평가 시작", 10, color=DIM,
                          align=Qt.AlignmentFlag.AlignCenter))

        btn = QPushButton("🧠  AVPU\n의식 수준 확인")
        btn.setFont(QFont("Malgun Gothic", 17, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a3a5c, stop:1 #0d2137);
                color:{BLUE}; border:2px solid {BLUE}; border-radius:10px;
            }}
            QPushButton:pressed {{background:#1c4a7a; border-color:#79c0ff;}}
        """)
        btn.clicked.connect(lambda: self._nav(1))
        lay.addWidget(btn, stretch=1)

        # A V P U 요약
        row = QHBoxLayout()
        row.setSpacing(4)
        for letter, desc, color in [
            ("A","Alert",GREEN), ("V","Voice",YELLOW),
            ("P","Pain",ORANGE), ("U","Unresp.",RED),
        ]:
            cell = QFrame()
            cell.setStyleSheet(
                f"background:{BG}; border:1px solid {color}; border-radius:5px;"
            )
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(4,4,4,4)
            cl.setSpacing(1)
            cl.addWidget(lbl(letter, 11, bold=True, color=color,
                             align=Qt.AlignmentFlag.AlignCenter))
            cl.addWidget(lbl(desc, 8, color=DIM,
                             align=Qt.AlignmentFlag.AlignCenter))
            row.addWidget(cell)
        lay.addLayout(row)
        return f

    # ── 응급 상황 6개 버튼 ─────────────────────────────────
    def _emergency_grid(self):
        f = QFrame()
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        lay.addWidget(lbl("응급 상황", 10, bold=True, color=DIM,
                          align=Qt.AlignmentFlag.AlignCenter))

        grid = QGridLayout()
        grid.setSpacing(6)
        scenarios = [
            ("💔 심폐소생술",    RED,    2),
            ("🩸 출혈 처치",     ORANGE, 4),
            ("🔥 화상 처치",     YELLOW, 4),
            ("🦴 골절 / 탈구",   TEAL,   4),
            ("🌊 익수 / 저체온", BLUE,   4),
            ("😮 기도 폐쇄",     PURPLE, 4),
        ]
        for i, (text, color, page) in enumerate(scenarios):
            btn = icon_btn(text, color, h=52)
            btn.clicked.connect(lambda _, p=page: self._nav(p))
            grid.addWidget(btn, i // 2, i % 2)
        lay.addLayout(grid)
        return f

    # ── 푸터 ──────────────────────────────────────────────
    def _footer(self):
        f = QFrame()
        f.setFixedHeight(26)
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:6px;"
        )
        lay = QHBoxLayout(f)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.addWidget(lbl(
            "⚠  이 가이드는 전문 의료를 대체하지 않습니다 — 가능한 빨리 의료진에게 연락하십시오",
            8, color=YELLOW
        ))
        lay.addStretch()
        lay.addWidget(lbl("1024×600", 8, color=DIM,
                          align=Qt.AlignmentFlag.AlignRight))
        return f


# ══════════════════════════════════════════════════════════
#  AVPU 화면
# ══════════════════════════════════════════════════════════
class AvpuScreen(QWidget):
    STEPS = [
        ("A","Alert — 의식 명료", GREEN, [
            "눈을 뜨고 있는가?",
            "말을 걸면 즉시 대답하는가?",
            "시간·장소·자신의 이름을 아는가?",
            "자발적으로 움직이는가?",
        ], "모두 해당 → 의식 명료(A). 하나라도 아니면 V 확인"),
        ("V","Voice — 음성 반응", YELLOW, [
            "크게 이름을 부르거나 '눈 떠 보세요!' 라고 말해보기",
            "눈을 뜨는가? / 손을 움직이는가?",
            "간단한 명령에 반응하는가? ('손 꽉 쥐어 보세요')",
        ], "반응 있으면 → V. 없으면 P 확인"),
        ("P","Pain — 통증 반응", ORANGE, [
            "흉골 중앙을 손가락 관절로 강하게 문지르기",
            "눈썹 위 눈두덩이를 강하게 누르기",
            "통증에 눈꺼풀이 떨리거나 손발을 움츠리는가?",
        ], "통증 반응 있으면 → P. 전혀 없으면 U"),
        ("U","Unresponsive — 무반응", RED, [
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
        self._root.setContentsMargins(10, 10, 10, 10)
        self._root.setSpacing(8)
        self._root.addWidget(self._top_bar())

        self._card = QFrame()
        self._root.addWidget(self._card, stretch=1)

        self._btm = QHBoxLayout()
        self._root.addLayout(self._btm)
        self._refresh()

    def _top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(46)
        bar.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:8px;"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)

        back = icon_btn("← 홈", BLUE, h=34, w=72)
        back.clicked.connect(lambda: self._nav(0))
        lay.addWidget(back)
        lay.addStretch()
        lay.addWidget(lbl("AVPU 의식 수준 평가", 13, bold=True,
                          align=Qt.AlignmentFlag.AlignCenter))
        lay.addStretch()

        self._dots = []
        for s in self.STEPS:
            d = lbl("●", 14, color=BORDER)
            self._dots.append((d, s[2]))
            lay.addWidget(d)
        return bar

    def _refresh(self):
        # 점
        for i, (d, color) in enumerate(self._dots):
            d.setStyleSheet(
                f"color:{color}; background:transparent;" if i == self._step
                else f"color:{BORDER}; background:transparent;"
            )
        # 카드 재빌드
        old = self._card.layout()
        if old:
            while old.count():
                item = old.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old)

        s = self.STEPS[self._step]
        letter, title, color, checks, note = s
        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(24, 18, 24, 18)
        cl.setSpacing(12)
        self._card.setStyleSheet(
            f"background:{PANEL}; border:2px solid {color}; border-radius:12px;"
        )

        top = QHBoxLayout()
        top.addWidget(lbl(letter, 60, bold=True, color=color))
        info = QVBoxLayout()
        info.addWidget(lbl(title, 17, bold=True, color=color))
        info.addWidget(lbl(f"단계 {self._step+1} / {len(self.STEPS)}", 10, color=DIM))
        top.addLayout(info)
        cl.addLayout(top)
        cl.addWidget(hline())

        for chk in checks:
            row = QHBoxLayout()
            row.addWidget(lbl("▶", 10, color=color))
            row.addWidget(lbl(chk, 12))
            cl.addLayout(row)

        cl.addStretch()
        cl.addWidget(hline())
        cl.addWidget(lbl(note, 11, color=YELLOW))

        # 하단 버튼
        while self._btm.count():
            item = self._btm.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._step > 0:
            p = icon_btn("◀ 이전", BORDER, h=46)
            p.clicked.connect(self._prev)
            self._btm.addWidget(p)
        self._btm.addStretch()

        rec = icon_btn(f'✔  "{letter}" 로 기록', color, h=46)
        rec.clicked.connect(lambda: self._nav(0))
        self._btm.addWidget(rec)

        if self._step < len(self.STEPS) - 1:
            n = icon_btn("다음 단계 ▶", BLUE, h=46)
            n.clicked.connect(self._next)
            self._btm.addWidget(n)
        else:
            cpr = icon_btn("CPR 화면 →", RED, h=46)
            cpr.clicked.connect(lambda: self._nav(2))
            self._btm.addWidget(cpr)

    def _next(self):
        if self._step < len(self.STEPS)-1:
            self._step += 1; self._refresh()

    def _prev(self):
        if self._step > 0:
            self._step -= 1; self._refresh()

    def reset(self):
        self._step = 0; self._refresh()


# ══════════════════════════════════════════════════════════
#  CPR 화면
# ══════════════════════════════════════════════════════════
class CprScreen(QWidget):
    GUIDE = [
        ("1","안전·반응 확인",
         ["주변 위험 요소 제거","어깨 두드리며 '괜찮으세요?' 외친다",
          "반응 없으면 도움 요청 + AED 준비"], BLUE),
        ("2","기도 확보",
         ["단단한 바닥에 눕힌다","머리 뒤로 젖히고 턱 들어 올리기",
          "10초 이내 호흡 유무 확인"], TEAL),
        ("3","가슴 압박 30회",
         ["양손 깍지 — 흉골 중앙에 위치","5~6 cm 깊이 수직 압박",
          "100~120회/분 속도","30회 후 인공호흡 2회"], ORANGE),
        ("4","인공호흡 2회",
         ["머리 젖히기 유지 — 코 막고 입에 공기 불어넣기",
          "1초 동안 가슴이 올라오는지 확인","2회 → 압박 30회 반복",
          "AED 도착 시 즉시 사용"], RED),
    ]

    def __init__(self, nav):
        super().__init__()
        self._nav   = nav
        self._count = 0
        self.setStyleSheet(f"background:{BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        root.addWidget(self._top_bar())

        body = QHBoxLayout()
        body.setSpacing(8)
        body.addWidget(self._counter_panel(), stretch=3)
        body.addWidget(self._guide_panel(),   stretch=7)
        root.addLayout(body)

    def _top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(46)
        bar.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:8px;"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)

        back = icon_btn("← 홈", BLUE, h=34, w=72)
        back.clicked.connect(lambda: self._nav(0))
        lay.addWidget(back)
        lay.addStretch()
        lay.addWidget(lbl("💔  심폐소생술 (CPR) 가이드", 13, bold=True, color=RED,
                          align=Qt.AlignmentFlag.AlignCenter))
        lay.addStretch()

        sos = QPushButton("🆘 SOS")
        sos.setFixedSize(80, 34)
        sos.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        sos.setStyleSheet(
            f"QPushButton{{background:{RED};color:white;border:none;border-radius:6px;}}"
            f"QPushButton:pressed{{background:#c0392b;}}"
        )
        sos.clicked.connect(lambda: self._nav(3))
        lay.addWidget(sos)
        return bar

    def _counter_panel(self):
        f = QFrame()
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(lbl("압박 카운터", 10, color=DIM,
                          align=Qt.AlignmentFlag.AlignCenter))
        self._cnt_lbl = lbl("0", 56, bold=True, color=RED,
                            align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._cnt_lbl)
        lay.addWidget(lbl("/ 30회", 11, color=DIM,
                          align=Qt.AlignmentFlag.AlignCenter))

        press = QPushButton("압박!")
        press.setFixedHeight(70)
        press.setFont(QFont("Malgun Gothic", 16, QFont.Weight.Bold))
        press.setStyleSheet(f"""
            QPushButton{{background:#3a0000;color:{RED};
                         border:2px solid {RED};border-radius:9px;}}
            QPushButton:pressed{{background:#5a0000;}}
        """)
        press.clicked.connect(self._press)
        lay.addWidget(press)

        rst = icon_btn("초기화", DIM, h=34)
        rst.clicked.connect(self._reset)
        lay.addWidget(rst)

        self._hint = lbl("100~120회/분 유지", 9, color=YELLOW,
                         align=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._hint)
        lay.addStretch()
        return f

    def _guide_panel(self):
        f = QFrame()
        f.setStyleSheet(
            f"background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        lay.addWidget(lbl("단계별 가이드", 11, bold=True, color=DIM))
        lay.addWidget(hline())

        for num, title, checks, color in self.GUIDE:
            sf = QFrame()
            sf.setStyleSheet(
                f"background:{BG}; border:1px solid {color}; border-radius:6px;"
            )
            sl = QVBoxLayout(sf)
            sl.setContentsMargins(10, 7, 10, 7)
            sl.setSpacing(3)
            h = QHBoxLayout()
            h.addWidget(lbl(f"STEP {num}", 9, bold=True, color=color))
            h.addWidget(lbl(title, 10, bold=True))
            sl.addLayout(h)
            for chk in checks:
                r = QHBoxLayout()
                r.addWidget(lbl("•", 9, color=color))
                r.addWidget(lbl(chk, 10, color=DIM))
                sl.addLayout(r)
            lay.addWidget(sf)
        lay.addStretch()
        return f

    def _press(self):
        self._count = min(self._count + 1, 30)
        self._cnt_lbl.setText(str(self._count))
        if self._count >= 30:
            self._cnt_lbl.setStyleSheet(f"color:{GREEN}; background:transparent;")
            self._hint.setText("→ 인공호흡 2회 실시!")
        else:
            self._cnt_lbl.setStyleSheet(f"color:{RED}; background:transparent;")

    def _reset(self):
        self._count = 0
        self._cnt_lbl.setText("0")
        self._cnt_lbl.setStyleSheet(f"color:{RED}; background:transparent;")
        self._hint.setText("100~120회/분 유지")


# ══════════════════════════════════════════════════════════
#  SOS 화면
# ══════════════════════════════════════════════════════════
class SosScreen(QWidget):
    def __init__(self, nav):
        super().__init__()
        self._nav = nav
        self.setStyleSheet(f"background:{BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        back = icon_btn("← 홈으로", BLUE, h=42)
        back.clicked.connect(lambda: self._nav(0))
        root.addWidget(back)

        root.addWidget(lbl("🆘  구조 요청 / 비상 연락", 18, bold=True, color=RED,
                           align=Qt.AlignmentFlag.AlignCenter))

        for role, contact in [
            ("선박 선장 / 당직 사관", "선내 인터폰 #01"),
            ("무선 통신실 (Radio Room)", "채널 16 (조난 주파수)"),
            ("해양경찰 구조대", "☎  122"),
            ("국제 조난 신호", "MAYDAY × 3"),
        ]:
            card = QFrame()
            card.setFixedHeight(62)
            card.setStyleSheet(
                f"background:{PANEL}; border:1px solid {RED}; border-radius:10px;"
            )
            cl = QHBoxLayout(card)
            cl.setContentsMargins(18, 0, 18, 0)
            cl.addWidget(lbl(role, 12))
            cl.addStretch()
            cl.addWidget(lbl(contact, 14, bold=True, color=RED,
                             align=Qt.AlignmentFlag.AlignRight))
            root.addWidget(card)

        root.addStretch()
        root.addWidget(lbl(
            "MAYDAY 교신: MAYDAY × 3 → 선박명 → 위치 → 인명 상황 → 필요 지원",
            11, color=YELLOW, align=Qt.AlignmentFlag.AlignCenter
        ))


# ══════════════════════════════════════════════════════════
#  메인 윈도우
# ══════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("선박 응급처치 가이드")
        self.setFixedSize(SCREEN_W, SCREEN_H)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._screens = [
            MainScreen(self._go),   # 0 메인
            AvpuScreen(self._go),   # 1 AVPU
            CprScreen(self._go),    # 2 CPR
            SosScreen(self._go),    # 3 SOS
        ]
        for s in self._screens:
            self._stack.addWidget(s)

    def _go(self, index: int):
        if index == 1:
            self._screens[1].reset()
        self._stack.setCurrentIndex(index)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
