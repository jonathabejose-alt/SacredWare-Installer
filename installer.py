from __future__ import annotations

import json
import os
import sys
import subprocess
import traceback
from dataclasses import dataclass
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


# -----------------------------
# Visual crash hook for --noconsole / compiled builds
# -----------------------------

def visual_excepthook(exctype, value, tb) -> None:
    try:
        message = "".join(traceback.format_exception(exctype, value, tb))
    except Exception:
        message = f"Unhandled exception: {exctype}: {value}"

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    QMessageBox.critical(
        None,
        "SacredWare Installer - Fatal Error",
        message,
    )


sys.excepthook = visual_excepthook


# -----------------------------
# URLs
# -----------------------------

APP_REPO_API = "https://api.github.com/repos/jonathabejose-alt/injector/releases/latest"
INSTALLER_REPO_API = "https://api.github.com/repos/jonathabejose-alt/SacredWare-Installer/releases/latest"

# -----------------------------
# Styling
# -----------------------------

STYLE = """
QMainWindow, QWidget {
    background-color: #0d0d0d;
    color: #cccccc;
    font-family: 'Segoe UI', sans-serif;
}
QMainWindow {
    border-radius: 18px;
}
QWidget#titleBar {
    background-color: #0d0d0d;
    border-bottom: 1px solid #1a1a1a;
    border-radius: 18px 18px 0px 0px;
}
QWidget#titleBar QLabel:not(#sacredTitle) {
    font-size: 11px;
    color: #cccccc;
    background: transparent;
    padding-right: 8px;
}
QWidget#toolbar {
    background-color: #0d0d0d;
    border-bottom: 1px solid #1a1a1a;
    padding: 6px 10px;
    border-radius: 8px;
}
QFrame {
    border-radius: 6px;
}
QPushButton {
    background-color: #141414;
    color: #cccccc;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    outline: none;
}
QPushButton:hover {
    background-color: #1e1e1e;
    border-color: #444444;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #0d0d0d;
}
QPushButton:focus {
    outline: none;
}
QPushButton:disabled {
    background-color: #141414;
    border: 1px solid #2a2a2a;
    color: #555555;
    font-weight: 700;
    border-radius: 6px;
}
QPushButton:checked {
    background-color: #141414;
    border-color: #444444;
    color: #cccccc;
}
QLineEdit {
    background-color: #141414;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #cccccc;
    font-size: 12px;
}
QLineEdit:focus { border-color: #444444; }
QTableWidget {
    background-color: #141414;
    gridline-color: #0d0d0d;
    border: none;
    font-size: 12px;
    color: #cccccc;
    selection-background-color: #0d0d0d;
    selection-color: #cccccc;
}
QTableWidget::item { padding: 4px 10px; border-bottom: 1px solid #111111; }
QTableWidget::item:selected { background-color: #1a1a1a; color: #ffffff; }
QTableWidget::item:hover { background-color: #141414; }
QHeaderView::section {
    background-color: #0d0d0d;
    color: #2a2a2a;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2px;
    padding: 5px 10px;
    border: none;
    border-bottom: 1px solid #0f0f0f;
}
QHeaderView { border: none; background: #0d0d0d; }
QTableWidget QHeaderView::section { border-right: none; border-left: none; }
QTableCornerButton::section { background: #0d0d0d; border: none; }
QStatusBar {
    background-color: #0d0d0d;
    border-top: 1px solid #1a1a1a;
    color: #cccccc;
    font-size: 11px;
    padding: 2px 8px;
}
QScrollBar:vertical { background: #0d0d0d; width: 4px; border-radius: 2px; margin: 0; }
QScrollBar::handle:vertical { background: #2a2a2a; border-radius: 2px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #444444; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; border:none; background:none; }
QDialog { background-color: #0d0d0d; border-radius: 12px; }
QComboBox {
    background-color: #0d0d0d;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding:4px 10px; color: #cccccc;
}
QComboBox::drop-down { border:none; }
QComboBox QAbstractItemView {
    background-color: #0d0d0d;
    color: #cccccc;
    border: 1px solid #2a2a2a;
}
"""

_DLG_BTN_PRIMARY = """
    QPushButton {
        background-color: #161616;
        border: 1px solid #cccccc;
        border-radius: 8px;
        color: #ffffff;
        font-size: 12px;
        font-weight: 700;
        padding: 6px 18px;
        letter-spacing: 0.5px;
    }
    QPushButton:hover { background-color: #222222; border-color: #ffffff; color: #ffffff; }
    QPushButton:pressed { background-color: #1a1a1a; }
"""

_DLG_BTN = """
    QPushButton {
        background-color: #141414;
        color: #cccccc;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    QPushButton:hover { background-color: #1e1e1e; border-color: #444; color: #fff; }
    QPushButton:pressed { background-color: #282828; }
"""

_CHK_STYLE = """
QCheckBox { background: transparent; }
QCheckBox::indicator { width:18px; height:18px; border:1px solid #2a2a2a; border-radius:4px; background:#141414; }
QCheckBox::indicator:checked { background: #cccccc; border-color: #cccccc; image: none; }
QCheckBox QLabel { color: #cccccc; font-size: 12px; }
"""

_PROGRESS_STYLE = """
QProgressBar {
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    background-color: #141414;
    color: #cccccc;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #cccccc;
    width: 12px;
    margin: 1px;
    border-radius: 7px;
}
"""


# -----------------------------
# Update logic (GitHub Latest Release)
# -----------------------------

def _parse_github_release(payload: str, asset_name: str) -> tuple[str, str]:
    """Return (remote_version_tag, download_url) for a given asset name."""
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Unrecognized GitHub release JSON format")

    tag_name = data.get("tag_name")
    if not isinstance(tag_name, str) or not tag_name.strip():
        raise ValueError("Missing or invalid 'tag_name' in GitHub release JSON")

    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Missing or invalid 'assets' array in GitHub release JSON")

    download_url: str | None = None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if asset.get("name") == asset_name:
            url = asset.get("browser_download_url")
            if isinstance(url, str) and url.strip():
                download_url = url.strip()
                break

    if not download_url:
        raise ValueError(f"Could not find '{asset_name}' in GitHub release assets")

    return tag_name.strip(), download_url


class VersionCheckThread(QThread):
    status = pyqtSignal(str)
    result = pyqtSignal(bool, str, str, str)  # has_update, local, remote, download_url
    error = pyqtSignal(str)

    def __init__(self, api_url: str, local_version_file: Path, asset_name: str) -> None:
        super().__init__()
        self._api_url = api_url
        self._local_version_file = local_version_file
        self._asset_name = asset_name

    def run(self) -> None:
        import urllib.request

        try:
            self.status.emit("Checking for updates...")

            self._local_version_file.parent.mkdir(parents=True, exist_ok=True)

            local_version_string = "v0.0.0"
            if self._local_version_file.exists():
                local_version_string = (
                    self._local_version_file.read_text(encoding="utf-8").strip() or "v0.0.0"
                )

            req = urllib.request.Request(
                self._api_url,
                headers={"User-Agent": "SacredWareInstaller/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

            remote_tag, download_url = _parse_github_release(raw, self._asset_name)
            has_update = remote_tag.strip() != local_version_string.strip()
            self.result.emit(has_update, local_version_string, remote_tag.strip(), download_url)
        except Exception:
            self.error.emit("Version check failed:\n" + "".join(traceback.format_exception(*sys.exc_info())))
            self.result.emit(False, "v0.0.0", "v0.0.0", "")


class DownloadThread(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url: str, target_path: Path) -> None:
        super().__init__()
        self._url = url
        self._target_path = target_path

    def run(self) -> None:
        import urllib.request

        try:
            self._target_path.parent.mkdir(parents=True, exist_ok=True)

            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "SacredWareInstaller/1.0"},
                method="GET",
            )

            self.status.emit("Downloading...")
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = resp.headers.get("Content-Length")
                total_int = int(total) if total and str(total).isdigit() else 0

                tmp_path = self._target_path.with_suffix(self._target_path.suffix + ".part")
                downloaded = 0

                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_int > 0:
                            pct = int(downloaded * 100 / total_int)
                            pct = min(100, max(0, pct))
                            self.progress.emit(pct)

                tmp_path.replace(self._target_path)

            self.progress.emit(100)
            self.status.emit("Download complete")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, "Download failed:\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)))


# -----------------------------
# Installer UI
# -----------------------------


@dataclass
class UiState:
    phase: str = "checking_installer"  # checking_installer | checking_app | ready | done
    has_installer_update: bool = False
    has_app_update: bool = False
    installer_remote_tag: str = ""
    app_remote_tag: str = ""
    installer_download_url: str = ""
    app_download_url: str = ""


class InstallerWindow(QMainWindow):
    APP_EXE_DIR = Path(os.getenv("APPDATA")) / "SacredWare"
    APP_EXE_PATH = APP_EXE_DIR / "SacredWare.exe"
    APP_VERSION_FILE = APP_EXE_DIR / "launcher_version.txt"
    INSTALLER_VERSION_FILE = APP_EXE_DIR / "installer_version.txt"
    INSTALLER_PATH = Path(sys.executable)  # El propio .exe del installer

    def __init__(self) -> None:
        super().__init__()

        self._drag_offset = None

        self.setWindowTitle("SacredWare Installer")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(450, 280)
        self.setStyleSheet(STYLE)

        self._state = UiState()

        try:
            self.APP_EXE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        outer = QWidget(self)
        outer.setStyleSheet("background: #0d0d0d;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        title = QWidget()
        title.setObjectName("titleBar")
        title.setStyleSheet(
            "background:#0a0a0a; border-radius:18px 18px 0 0; border-bottom:1px solid #1a1a1a;"
        )
        title.setFixedHeight(44)
        title_layout = QHBoxLayout(title)
        title_layout.setContentsMargins(14, 0, 8, 0)
        title_layout.setSpacing(8)

        title_label = QLabel("Installer")
        title_label.setStyleSheet(
            "color:#888888; font-size:11px; font-weight:600; letter-spacing:2px; background:transparent;"
        )
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#555;font-size:11px;border-radius:6px;}"
            "QPushButton:hover{background:#cc2222;color:#fff;}"
        )
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        outer_layout.addWidget(title)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 20)
        content_layout.setSpacing(12)

        self.status_lbl = QLabel("Initializing...")
        self.status_lbl.setStyleSheet(
            "color:#888888; font-size:12px; font-weight:600; background:transparent;"
        )
        content_layout.addWidget(self.status_lbl)

        self.compare_lbl = QLabel("")
        self.compare_lbl.setStyleSheet(
            "color:#cccccc; font-size:12px; font-weight:600; background:transparent;"
        )
        content_layout.addWidget(self.compare_lbl)

        self.chk_shortcut = QCheckBox("Create desktop shortcut")
        self.chk_shortcut.setStyleSheet(_CHK_STYLE)
        self.chk_shortcut.setChecked(False)
        content_layout.addWidget(self.chk_shortcut)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet(_PROGRESS_STYLE)
        content_layout.addWidget(self.progress)

        btn_row = QHBoxLayout()

        self.action_btn = QPushButton("Install / Update")
        self.action_btn.setStyleSheet(_DLG_BTN_PRIMARY)
        self.action_btn.setEnabled(False)
        self.action_btn.clicked.connect(self._on_action_clicked)
        btn_row.addWidget(self.action_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(_DLG_BTN)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.connect(self.close)
        btn_row.addWidget(self.cancel_btn)

        content_layout.addLayout(btn_row)

        outer_layout.addWidget(content)
        self.setCentralWidget(outer)

    # -----------------------------
    # Frameless dragging
    # -----------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _show_fatal(self, message: str) -> None:
        QMessageBox.critical(None, "SacredWare Installer - Fatal Error", message)
        self.close()

    def _on_action_clicked(self) -> None:
        if self._state.phase == "installer_update_ready":
            self._download_and_apply_installer_update()
        elif self._state.phase == "app_update_ready":
            self._download_and_apply_app_update()

    def _download_and_apply_installer_update(self) -> None:
        url = self._state.installer_download_url
        if not url:
            return

        self.action_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.status_lbl.setText("Downloading new installer...")
        self.progress.setValue(0)

        new_installer_path = self.APP_EXE_DIR / "SacredWare_Installer_new.exe"

        self._downloader = DownloadThread(url, new_installer_path)
        self._downloader.status.connect(self._set_status)
        self._downloader.progress.connect(self.progress.setValue)
        self._downloader.finished.connect(self._on_installer_download_finished)
        self._downloader.start()

    def _on_installer_download_finished(self, success: bool, error: str) -> None:
        if not success:
            self._show_fatal(error)
            return

        self.progress.setValue(100)
        self.status_lbl.setText("Updating installer...")

        # Guardar versión nueva del installer
        try:
            self.INSTALLER_VERSION_FILE.write_text(self._state.installer_remote_tag, encoding="utf-8")
        except Exception:
            pass

        # Script .bat que reemplaza el installer viejo por el nuevo y lo ejecuta
        current_exe = str(self.INSTALLER_PATH)
        new_exe = str(self.APP_EXE_DIR / "SacredWare_Installer_new.exe")
        bat_path = str(self.APP_EXE_DIR / "update_installer.bat")

        bat_content = f'''@echo off
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}"
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del /f /q "%~f0"
'''

        try:
            Path(bat_path).write_text(bat_content, encoding="utf-8")
            subprocess.Popen(
                [bat_path],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            self.close()
            sys.exit(0)
        except Exception as e:
            self._show_fatal(f"Failed to apply installer update: {e}")

    def _download_and_apply_app_update(self) -> None:
        url = self._state.app_download_url
        if not url:
            return

        self.action_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.status_lbl.setText("Downloading SacredWare.exe...")
        self.progress.setValue(0)

        self._downloader = DownloadThread(url, self.APP_EXE_PATH)
        self._downloader.status.connect(self._set_status)
        self._downloader.progress.connect(self.progress.setValue)
        self._downloader.finished.connect(self._on_app_download_finished)
        self._downloader.start()

    def _on_app_download_finished(self, success: bool, error: str) -> None:
        self.action_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        if not success:
            self.status_lbl.setText("Download failed")
            self._show_fatal(error)
            return

        self.progress.setValue(100)
        self.status_lbl.setText("Installing...")

        try:
            if self.chk_shortcut.isChecked():
                self._create_desktop_shortcut()
        except Exception:
            pass

        try:
            self.APP_VERSION_FILE.write_text(self._state.app_remote_tag, encoding="utf-8")
        except Exception:
            pass

        try:
            if self.APP_EXE_PATH.exists():
                subprocess.Popen(
                    [str(self.APP_EXE_PATH)],
                    cwd=str(self.APP_EXE_DIR),
                    shell=True,
                )
                self.close()
                sys.exit(0)
        except Exception:
            pass

        self.close()

    def _set_status(self, s: str) -> None:
        self.status_lbl.setText(s)

    def _on_installer_version_result(
        self, has_update: bool, local: str, remote: str, url: str
    ) -> None:
        if has_update:
            self._state.phase = "installer_update_ready"
            self._state.has_installer_update = True
            self._state.installer_remote_tag = remote
            self._state.installer_download_url = url
            self.compare_lbl.setText(f"Installer: {local} → {remote}")
            self.status_lbl.setText("🔄 Installer update available!")
            self.action_btn.setText("Update Installer")
            self.action_btn.setEnabled(True)
            self.progress.setValue(100)
        else:
            self.status_lbl.setText("Installer is up to date. Checking app...")
            self.progress.setValue(50)
            self._check_app_version()

    def _on_app_version_result(
        self, has_update: bool, local: str, remote: str, url: str
    ) -> None:
        if not has_update:
            try:
                exe = self.APP_EXE_PATH
                if exe.exists():
                    subprocess.Popen([str(exe)], cwd=str(self.APP_EXE_DIR))
            finally:
                self.close()
            return

        self._state.phase = "app_update_ready"
        self._state.has_app_update = True
        self._state.app_remote_tag = remote
        self._state.app_download_url = url
        self.compare_lbl.setText(f"App: {local} → {remote}")
        self.status_lbl.setText("🔥 App update available!")
        self.action_btn.setText("Install / Update App")
        self.action_btn.setEnabled(True)
        self.progress.setValue(100)

    def _check_installer_version(self) -> None:
        self.progress.setValue(10)
        self.status_lbl.setText("Checking installer version...")

        self._thread = VersionCheckThread(
            api_url=INSTALLER_REPO_API,
            local_version_file=self.INSTALLER_VERSION_FILE,
            asset_name="SacredWare_Installer.exe",
        )
        self._thread.status.connect(self._set_status)
        self._thread.result.connect(self._on_installer_version_result)
        self._thread.error.connect(self._on_installer_check_failed)
        self._thread.start()

    def _on_installer_check_failed(self, error: str) -> None:
        # Si falla el check del installer, seguimos con el check de la app
        self.status_lbl.setText("Installer check failed. Checking app...")
        self.progress.setValue(50)
        self._check_app_version()

    def _check_app_version(self) -> None:
        self._thread = VersionCheckThread(
            api_url=APP_REPO_API,
            local_version_file=self.APP_VERSION_FILE,
            asset_name="SacredWare.exe",
        )
        self._thread.status.connect(self._set_status)
        self._thread.result.connect(self._on_app_version_result)
        self._thread.error.connect(self._show_fatal)
        self._thread.start()

    def start(self) -> None:
        self._check_installer_version()

    def _create_desktop_shortcut(self) -> None:
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "SacredWare.lnk"
        target = str(self.APP_EXE_PATH)

        if not Path(target).exists():
            return

        ps = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.WorkingDirectory = "{str(self.APP_EXE_DIR)}"
$Shortcut.Save()
'''.strip()

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    w = InstallerWindow()
    w.show()
    w.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
