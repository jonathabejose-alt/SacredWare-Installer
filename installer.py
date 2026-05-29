from __future__ import annotations

import json
import os
import sys
import subprocess
import traceback
import urllib.request
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QMessageBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


def visual_excepthook(exctype, value, tb):
    try:
        message = "".join(traceback.format_exception(exctype, value, tb))
    except:
        message = f"Error: {exctype}: {value}"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    QMessageBox.critical(None, "Error", message)


sys.excepthook = visual_excepthook

APP_API = "https://api.github.com/repos/jonathabejose-alt/injector/releases/latest"

STYLE = """
QMainWindow, QWidget { background-color: #0d0d0d; color: #cccccc; font-family: 'Segoe UI', sans-serif; }
QMainWindow { border-radius: 18px; }
QPushButton { background-color: #141414; color: #cccccc; border: 1px solid #2a2a2a; border-radius: 6px; padding: 5px 14px; font-size: 12px; }
QPushButton:hover { background-color: #1e1e1e; border-color: #444444; color: #ffffff; }
QPushButton:disabled { background-color: #141414; color: #555555; }
QCheckBox { background: transparent; color: #cccccc; }
QProgressBar { border: 1px solid #2a2a2a; border-radius: 8px; background-color: #141414; height: 18px; }
QProgressBar::chunk { background-color: #cccccc; border-radius: 7px; }
"""


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, path):
        super().__init__()
        self._url = url
        self._path = path

    def run(self):
        try:
            self.status.emit("Downloading SacredWare.exe...")
            self._path.parent.mkdir(parents=True, exist_ok=True)

            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "SacredWareInstaller"}
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                total = resp.headers.get("Content-Length")
                total = int(total) if total and total.isdigit() else 0
                downloaded = 0
                tmp = self._path.with_suffix(".part")

                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(256 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress.emit(int(downloaded * 100 / total))

                tmp.replace(self._path)

            self.progress.emit(100)
            self.status.emit("Download complete!")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SacredWare Installer")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 200)
        self.setStyleSheet(STYLE)

        self._exe_dir = Path(os.getenv("APPDATA")) / "SacredWare"
        self._exe_path = self._exe_dir / "SacredWare.exe"
        self._download_url = None
        self._version = None

        outer = QWidget(self)
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        title = QLabel("SacredWare Installer")
        title.setStyleSheet("color:#888; font-size:11px; font-weight:600; letter-spacing:2px;")
        layout.addWidget(title)

        self.status = QLabel("Checking for updates...")
        self.status.setStyleSheet("color:#ccc; font-size:12px;")
        layout.addWidget(self.status)

        self.chk = QCheckBox("Create desktop shortcut")
        layout.addWidget(self.chk)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        btn_row = QHBoxLayout()
        self.btn = QPushButton("Install / Update")
        self.btn.setStyleSheet("background:#161616; border:1px solid #ccc; border-radius:8px; color:#fff; font-weight:700; padding:8px 18px;")
        self.btn.clicked.connect(self._start_download)
        self.btn.setEnabled(False)
        btn_row.addWidget(self.btn)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.close)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

        self.setCentralWidget(outer)
        self._drag = None

        # Iniciar checkeo
        self._check_version()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def _check_version(self):
        try:
            req = urllib.request.Request(APP_API, headers={"User-Agent": "SacredWareInstaller"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            self._version = data["tag_name"]

            # Buscar el .exe
            for asset in data.get("assets", []):
                if asset["name"].endswith(".exe"):
                    self._download_url = asset["browser_download_url"]
                    break

            if not self._download_url:
                raise Exception("No .exe found in release")

            # Ver si ya está instalado
            version_file = self._exe_dir / "version.txt"
            current_version = ""
            if version_file.exists():
                current_version = version_file.read_text().strip()

            if current_version == self._version and self._exe_path.exists():
                self.status.setText(f"Up to date ({self._version})")
                self.btn.setText("Launch")
                self.btn.setEnabled(True)
            else:
                self.status.setText(f"Update available: {self._version}")
                self.btn.setText("Install / Update")
                self.btn.setEnabled(True)
                self.progress.setValue(30)

        except Exception as e:
            self.status.setText(f"Error: {e}")
            # Si falla el check pero el exe existe, dar opcion de launch
            if self._exe_path.exists():
                self.btn.setText("Launch anyway")
                self.btn.setEnabled(True)

    def _start_download(self):
        if self.btn.text() == "Launch" or self.btn.text() == "Launch anyway":
            self._launch()
            return

        if not self._download_url:
            return

        self.btn.setEnabled(False)
        self.progress.setValue(0)

        self._thread = DownloadThread(self._download_url, self._exe_path)
        self._thread.status.connect(self.status.setText)
        self._thread.progress.connect(self.progress.setValue)
        self._thread.finished.connect(self._on_done)
        self._thread.start()

    def _on_done(self, ok, msg):
        if not ok:
            QMessageBox.critical(self, "Error", msg)
            self.close()
            return

        # Guardar version
        try:
            (self._exe_dir / "version.txt").write_text(self._version or "")
        except:
            pass

        # Shortcut
        if self.chk.isChecked():
            try:
                desktop = Path.home() / "Desktop" / "SacredWare.lnk"
                ps = f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{desktop}');$s.TargetPath='{self._exe_path}';$s.WorkingDirectory='{self._exe_dir}';$s.Save()"
                subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
            except:
                pass

        self._launch()

    def _launch(self):
        try:
            if self._exe_path.exists():
                subprocess.Popen([str(self._exe_path)], cwd=str(self._exe_dir), shell=True)
        except:
            pass
        self.close()


def main():
    app = QApplication(sys.argv)
    w = InstallerWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
