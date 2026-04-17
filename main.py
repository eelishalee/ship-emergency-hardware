import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QFont


# 7인치 디스플레이 해상도 설정 (1024x600 또는 800x480 중 선택)
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
# SCREEN_WIDTH = 800
# SCREEN_HEIGHT = 480


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("7inch PyQt6 App")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        # 중앙 위젯 설정
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background-color: #1e1e2e;")

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 상단 헤더
        header = self._make_header()
        root_layout.addWidget(header)

        # 본문 (좌·우 패널)
        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._make_left_panel(), stretch=1)
        body.addWidget(self._make_right_panel(), stretch=1)
        root_layout.addLayout(body, stretch=1)

        # 하단 상태바
        footer = self._make_footer()
        root_layout.addWidget(footer)

        # 시계 업데이트 타이머
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_clock)
        self._timer.start(1000)
        self._update_clock()

    # ── 헤더 ──────────────────────────────────────────────
    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(56)
        frame.setStyleSheet(
            "background-color: #313244; border-radius: 8px;"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("PyQt6 · 7-inch Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #cdd6f4;")

        self._clock_label = QLabel()
        self._clock_label.setFont(QFont("Arial", 14))
        self._clock_label.setStyleSheet("color: #a6e3a1;")
        self._clock_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self._clock_label)
        return frame

    # ── 좌측 패널 ─────────────────────────────────────────
    def _make_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #313244; border-radius: 8px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("정보 패널")
        header.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        for i, (label, value) in enumerate([
            ("상태", "정상"),
            ("온도", "36.7 °C"),
            ("습도", "45 %"),
            ("배터리", "87 %"),
        ]):
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setFont(QFont("Arial", 11))
            lbl.setStyleSheet("color: #a6adc8;")
            val = QLabel(value)
            val.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            val.setStyleSheet("color: #cdd6f4;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl)
            row.addWidget(val)
            layout.addLayout(row)

        layout.addStretch()
        return frame

    # ── 우측 패널 ─────────────────────────────────────────
    def _make_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #313244; border-radius: 8px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("컨트롤 패널")
        header.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        self._status_label = QLabel("대기 중")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setFont(QFont("Arial", 11))
        self._status_label.setStyleSheet("color: #a6e3a1; padding: 6px;")
        layout.addWidget(self._status_label)

        for text, color, action in [
            ("시작", "#a6e3a1", lambda: self._set_status("실행 중", "#a6e3a1")),
            ("정지", "#f38ba8", lambda: self._set_status("정지됨", "#f38ba8")),
            ("초기화", "#fab387", lambda: self._set_status("대기 중", "#94e2d5")),
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(44)
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #45475a;
                    color: {color};
                    border: 1px solid {color};
                    border-radius: 6px;
                }}
                QPushButton:pressed {{
                    background-color: #585b70;
                }}
            """)
            btn.clicked.connect(action)
            layout.addWidget(btn)

        layout.addStretch()
        return frame

    # ── 하단 상태바 ───────────────────────────────────────
    def _make_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(32)
        frame.setStyleSheet(
            "background-color: #313244; border-radius: 6px;"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 0, 12, 0)

        msg = QLabel("시스템 준비 완료  |  해상도: "
                     f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
        msg.setFont(QFont("Arial", 10))
        msg.setStyleSheet("color: #6c7086;")
        layout.addWidget(msg)
        return frame

    # ── 헬퍼 ──────────────────────────────────────────────
    def _update_clock(self):
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd  HH:mm:ss")
        self._clock_label.setText(now)

    def _set_status(self, text: str, color: str):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; padding: 6px;")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
