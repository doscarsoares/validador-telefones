#!/usr/bin/env python3
"""
Validador de Telefones — Instalador Grafico
PyQt5 | Adobe Photoshop-style UI
"""

import sys
import os
import platform
import subprocess
import shutil
import time
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QProgressBar, QLineEdit, QPushButton, QFileDialog,
    QStackedWidget, QFrame, QSizePolicy, QSpacerItem, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon, QFontDatabase


# ============================================================
#  BUNDLE PATH
# ============================================================
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
#  CONSTANTS
# ============================================================
APP_NAME = "Validador de Telefones"
APP_VERSION = "2.1"
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 500

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    DEFAULT_INSTALL_DIR = str(Path.home() / "ValidadorTelefones")
else:
    DEFAULT_INSTALL_DIR = str(Path.home() / "ValidadorTelefones")

COLOR_DARK_HEADER = "#1a1a1a"
COLOR_HEADER_TEXT = "#ffffff"
COLOR_SUBTEXT = "#888888"
COLOR_BG = "#ffffff"
COLOR_BLUE = "#2680EB"
COLOR_BLUE_HOVER = "#1473CE"
COLOR_BORDER = "#e0e0e0"
COLOR_PROGRESS_BG = "#e8e8e8"
COLOR_BODY_TEXT = "#333333"
COLOR_LIGHT_BG = "#f8f8f8"


# ============================================================
#  FONT HELPER
# ============================================================
def get_font(size, bold=False, family=None):
    families = ["Montserrat", "Helvetica Neue", "Segoe UI", "Arial", "sans-serif"]
    if family:
        families.insert(0, family)
    f = QFont()
    for fam in families:
        f.setFamily(fam)
        break
    f.setPointSize(size)
    f.setBold(bold)
    return f


# ============================================================
#  STYLED MESSAGE BOX
# ============================================================
MSGBOX_STYLESHEET = (
    "QMessageBox { background-color: #ffffff; }"
    "QMessageBox QLabel { color: #333333; font-family: Montserrat, Helvetica Neue, sans-serif; font-size: 13px; }"
)

STYLE_BTN_POSITIVE = (
    "background-color: #2680EB; color: white; border: none; border-radius: 4px; "
    "padding: 8px 20px; font-family: Montserrat, Helvetica Neue, sans-serif; font-size: 11px; "
    "font-weight: bold; min-width: 140px;"
)

STYLE_BTN_NEGATIVE = (
    "background-color: #e0e0e0; color: #333333; border: none; border-radius: 4px; "
    "padding: 8px 20px; font-family: Montserrat, Helvetica Neue, sans-serif; font-size: 11px; "
    "font-weight: bold; min-width: 140px;"
)


def styled_msgbox(parent, title, text, buttons=None, icon_type="info"):
    """Create a QMessageBox styled to match the installer theme.
    buttons: list of (text, role) — first button is positive (blue), rest are negative (gray).
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStyleSheet(MSGBOX_STYLESHEET)

    icon_map = {
        "info": QMessageBox.Information,
        "warning": QMessageBox.Warning,
        "critical": QMessageBox.Critical,
        "question": QMessageBox.Question,
    }
    msg.setIcon(icon_map.get(icon_type, QMessageBox.Information))

    if buttons:
        added = []
        for i, (btn_text, btn_role) in enumerate(buttons):
            btn = msg.addButton(btn_text, btn_role)
            # Primeiro botão = positivo (azul), resto = negativo (cinza)
            if i == 0:
                btn.setStyleSheet(STYLE_BTN_POSITIVE)
            else:
                btn.setStyleSheet(STYLE_BTN_NEGATIVE)
            added.append(btn)
        msg.exec_()
        return msg, added
    else:
        msg.exec_()
        return msg, []


# ============================================================
#  INSTALLER THREAD
# ============================================================
class InstallerThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, install_dir, reinstall_mode=False):
        super().__init__()
        self.install_dir = install_dir
        self.reinstall_mode = reinstall_mode

    # PATH expandido pra encontrar brew, adb, ffmpeg etc.
    _EXTRA_PATH = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    def _run_cmd(self, cmd, shell=False, check=False):
        try:
            env = os.environ.copy()
            env["PATH"] = self._EXTRA_PATH + ":" + env.get("PATH", "")
            result = subprocess.run(
                cmd,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,
                env=env
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_cmd(self, cmd):
        """Verifica se um comando existe no sistema."""
        # Checar com PATH expandido
        for p in self._EXTRA_PATH.split(":"):
            if os.path.exists(os.path.join(p, cmd)):
                return True
        return shutil.which(cmd) is not None

    def _check_pip_pkg(self, pip_exe, pkg):
        """Verifica se um pacote pip já está instalado."""
        result = subprocess.run(
            [pip_exe, "show", pkg],
            capture_output=True, timeout=10
        )
        return result.returncode == 0

    def run(self):
        try:
            install_path = Path(self.install_dir)

            # Reinstall: kill any running instance first, then delete files
            if self.reinstall_mode:
                self.progress.emit(1, "Encerrando programa em execução...")
                if IS_WINDOWS:
                    subprocess.run(
                        ["taskkill", "/f", "/im", "python.exe"],
                        capture_output=True
                    )
                else:
                    subprocess.run(
                        ["pkill", "-f", "app_gui.py"],
                        capture_output=True
                    )
                    subprocess.run(
                        ["killall", "python3"],
                        capture_output=True
                    )
                time.sleep(2)

                self.progress.emit(2, "Apagando instalação anterior...")
                if install_path.exists():
                    for item in install_path.iterdir():
                        if item.name == "venv":
                            continue  # Keep venv to speed up reinstall
                        try:
                            if item.is_dir():
                                shutil.rmtree(str(item), ignore_errors=True)
                            else:
                                item.unlink()
                        except Exception:
                            pass
                self.progress.emit(5, "Instalação anterior apagada.")

            # Step 1: Pastas (0-5%)
            self.progress.emit(2, "Preparando...")
            for folder in ["audios", "resultados", "planilhas"]:
                (install_path / folder).mkdir(parents=True, exist_ok=True)
            self.progress.emit(5, "")

            # Step 2: Copiar arquivos (5-15%)
            self.progress.emit(7, "Copiando arquivos...")
            for item in os.listdir(BUNDLE_DIR):
                src = os.path.join(BUNDLE_DIR, item)
                dst = str(install_path / item)
                try:
                    if os.path.isdir(src):
                        if not os.path.exists(dst):
                            shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                except Exception:
                    pass
            self.progress.emit(15, "")

            # Step 3: Dependências do sistema — só instala o que falta (15-30%)
            self.progress.emit(17, "Verificando sistema...")
            if IS_LINUX:
                missing = []
                for cmd, pkg in [("python3","python3"), ("adb","adb"), ("ffmpeg","ffmpeg")]:
                    if not self._check_cmd(cmd):
                        missing.append(pkg)
                # Sempre incluir esses pois não têm comando pra checar
                for pkg in ["python3-venv", "python3-pip", "python3-tk", "portaudio19-dev"]:
                    missing.append(pkg)
                if missing:
                    self._run_cmd(["sudo", "apt-get", "install", "-y"] + missing)
            elif IS_MAC:
                # Encontrar brew
                brew_cmd = None
                for bp in ["/usr/local/bin/brew", "/opt/homebrew/bin/brew"]:
                    if os.path.exists(bp):
                        brew_cmd = bp
                        break

                # Se não tem Homebrew, instalar
                if not brew_cmd:
                    self.progress.emit(22, "Instalando Homebrew...")
                    self._run_cmd(
                        '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                        shell=True
                    )
                    # Checar de novo
                    for bp in ["/usr/local/bin/brew", "/opt/homebrew/bin/brew"]:
                        if os.path.exists(bp):
                            brew_cmd = bp
                            break

                if brew_cmd:
                    for pkg, cmd in [("ffmpeg","ffmpeg"), ("portaudio",""), ("android-platform-tools","adb")]:
                        if cmd and self._check_cmd(cmd):
                            continue
                        if not cmd:
                            try:
                                r = subprocess.run(
                                    [brew_cmd, "list", pkg],
                                    capture_output=True, timeout=30
                                )
                                if r.returncode == 0:
                                    continue
                            except Exception:
                                pass
                        self._run_cmd([brew_cmd, "install", pkg])
            self.progress.emit(30, "")

            # Step 4: Venv — só cria se não existir (30-40%)
            self.progress.emit(32, "Verificando ambiente...")
            venv_path = install_path / "venv"
            if IS_WINDOWS:
                pip_exe = str(venv_path / "Scripts" / "pip")
                python_exe = str(venv_path / "Scripts" / "python")
            else:
                pip_exe = str(venv_path / "bin" / "pip")
                python_exe = str(venv_path / "bin" / "python3")

            if not os.path.exists(pip_exe):
                # Procurar Python 3.11+ no sistema (versões antigas causam crash)
                system_python = None
                # Se Mac e tem brew, garantir que Python 3.11+ está instalado
                if IS_MAC and brew_cmd:
                    has_python = False
                    for pv in ["python3.11", "python3.12", "python3.13"]:
                        if self._check_cmd(pv):
                            has_python = True
                            break
                    if not has_python:
                        self._run_cmd([brew_cmd, "install", "python@3.11"])

                # Checar caminhos explícitos primeiro (Mac Framework)
                explicit_paths = [
                    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11",
                    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12",
                    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13",
                    "/usr/local/bin/python3.11",
                    "/usr/local/bin/python3.12",
                    "/opt/homebrew/bin/python3.11",
                    "/opt/homebrew/bin/python3.12",
                    "/opt/homebrew/bin/python3",
                ]
                for p in explicit_paths:
                    if os.path.exists(p):
                        system_python = p
                        break
                if not system_python:
                    system_python = (
                        shutil.which("python3.11") or
                        shutil.which("python3.12") or
                        shutil.which("python3") or
                        "python3"
                    )
                self._run_cmd([system_python, "-m", "venv", str(venv_path)])
            self.progress.emit(40, "")

            # Step 5: Pacotes pip — só instala o que falta (40-60%)
            self.progress.emit(42, "Verificando pacotes...")
            pkgs_base = ["customtkinter", "openpyxl", "certifi", "Pillow"]
            if IS_MAC:
                pkgs_base.append("pyobjc-framework-Cocoa")
            missing_pkgs = [p for p in pkgs_base if not self._check_pip_pkg(pip_exe, p)]
            if missing_pkgs:
                self._run_cmd([pip_exe, "install", "--quiet"] + missing_pkgs)
            # PyAudio pode falhar — tentar separado
            if not self._check_pip_pkg(pip_exe, "pyaudio"):
                self._run_cmd([pip_exe, "install", "--quiet", "pyaudio"])
            self.progress.emit(55, "")

            # Step 6: Whisper — só instala se não tiver (55-75%)
            self.progress.emit(57, "Verificando Whisper...")
            if not self._check_pip_pkg(pip_exe, "openai-whisper"):
                self._run_cmd([pip_exe, "install", "--quiet", "--prefer-binary", "numba"])
                self._run_cmd([pip_exe, "install", "--quiet", "openai-whisper"])
            self.progress.emit(75, "")

            # Step 7: Modelo Whisper — só baixa se não tiver (75-85%)
            self.progress.emit(77, "Verificando modelo de voz...")
            whisper_cache = Path.home() / ".cache" / "whisper" / "small.pt"
            if not whisper_cache.exists():
                self._run_cmd([
                    python_exe, "-c",
                    "import whisper; whisper.load_model('small')"
                ])
            self.progress.emit(85, "")

            # Step 8: Install Montserrat font (82-88%)
            self.progress.emit(83, "Instalando fontes...")
            try:
                import urllib.request
                font_url = (
                    "https://github.com/JulietaUla/Montserrat/raw/master/"
                    "fonts/ttf/Montserrat-Regular.ttf"
                )
                if IS_LINUX:
                    font_dir = Path.home() / ".local" / "share" / "fonts"
                elif IS_MAC:
                    font_dir = Path.home() / "Library" / "Fonts"
                else:
                    font_dir = Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"
                font_dir.mkdir(parents=True, exist_ok=True)
                font_dest = font_dir / "Montserrat-Regular.ttf"
                if not font_dest.exists():
                    urllib.request.urlretrieve(font_url, str(font_dest))
            except Exception:
                pass
            self.progress.emit(88, "Fontes instaladas.")

            # Step 9: Create launcher script (88-92%)
            self.progress.emit(89, "Criando lancador...")
            if not IS_WINDOWS:
                launcher = install_path / "executar.sh"
                extra_path = ""
                if IS_MAC:
                    extra_path = (
                        "export PATH=$PATH:/opt/homebrew/bin"
                        ":/usr/local/bin:$HOME/Library/Android/sdk/platform-tools\n"
                    )
                elif IS_LINUX:
                    extra_path = (
                        "export PATH=$PATH:/usr/local/bin"
                        ":$HOME/Android/Sdk/platform-tools\n"
                    )
                launcher_content = (
                    "#!/bin/bash\n"
                    + extra_path
                    + f'cd "{install_path}"\n'
                    + f'"{python_exe}" app_gui.py\n'
                )
                launcher.write_text(launcher_content)
                launcher.chmod(0o755)
            self.progress.emit(92, "Lancador criado.")

            # Step 10: Desktop shortcut (92-97%)
            self.progress.emit(93, "Criando atalho...")
            desktop = Path.home() / "Desktop"
            icon_src = install_path / "Icone_validador.png"

            # Limpar ícones antigos com nomes diferentes
            for old_name in [
                "Validador de Telefones.app",
                "ValidadorTelefones.app",
                "Validador de Telefones.desktop",
                "ValidadorTelefones.desktop",
            ]:
                old_path = desktop / old_name
                if old_path.exists():
                    shutil.rmtree(str(old_path), ignore_errors=True)

            if IS_LINUX:
                desktop_file = desktop / "ValidadorTelefones.desktop"
                desktop_file.write_text(
                    "[Desktop Entry]\n"
                    f"Name={APP_NAME}\n"
                    "Type=Application\n"
                    f"Exec=bash {install_path}/executar.sh\n"
                    f"Icon={icon_src}\n"
                    "Terminal=false\n"
                    "Categories=Utility;\n"
                )
                desktop_file.chmod(0o755)
            elif IS_MAC:
                app_dir = desktop / "Validador de Telefones.app"
                contents = app_dir / "Contents" / "MacOS"
                resources = app_dir / "Contents" / "Resources"
                contents.mkdir(parents=True, exist_ok=True)
                resources.mkdir(parents=True, exist_ok=True)

                # Copiar ícone .icns pro Resources do .app
                icns_src = install_path / "Icone_validador.icns"
                icns_dst = resources / "Icone_validador.icns"
                if icns_src.exists():
                    shutil.copy2(str(icns_src), str(icns_dst))
                else:
                    # Se não tiver .icns, gerar a partir do .png usando sips
                    png_src = install_path / "Icone_validador.png"
                    if png_src.exists():
                        iconset = Path("/tmp/ValidadorIcon.iconset")
                        iconset.mkdir(parents=True, exist_ok=True)
                        for size in [16, 32, 128, 256, 512]:
                            subprocess.run([
                                "sips", "-z", str(size), str(size),
                                str(png_src), "--out",
                                str(iconset / f"icon_{size}x{size}.png")
                            ], capture_output=True)
                        if (iconset / "icon_32x32.png").exists():
                            shutil.copy2(
                                str(iconset / "icon_32x32.png"),
                                str(iconset / "icon_16x16@2x.png")
                            )
                        if (iconset / "icon_256x256.png").exists():
                            shutil.copy2(
                                str(iconset / "icon_256x256.png"),
                                str(iconset / "icon_128x128@2x.png")
                            )
                        if (iconset / "icon_512x512.png").exists():
                            shutil.copy2(
                                str(iconset / "icon_512x512.png"),
                                str(iconset / "icon_256x256@2x.png")
                            )
                        subprocess.run([
                            "iconutil", "-c", "icns", str(iconset),
                            "-o", str(icns_dst)
                        ], capture_output=True)
                        shutil.rmtree(str(iconset), ignore_errors=True)

                exec_file = contents / "ValidadorTelefones"
                exec_file.write_text(
                    "#!/bin/bash\n"
                    "export PATH=\"/usr/local/bin:/usr/bin:/opt/homebrew/bin"
                    ":$HOME/Library/Android/sdk/platform-tools:$PATH\"\n"
                    f'cd "{install_path}"\n'
                    f'"{install_path}/venv/bin/python3" app_gui.py\n'
                )
                exec_file.chmod(0o755)
                plist = app_dir / "Contents" / "Info.plist"
                plist.write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
                    ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>\n'
                    '<key>CFBundleName</key><string>Validador de Telefones</string>\n'
                    '<key>CFBundleExecutable</key><string>ValidadorTelefones</string>\n'
                    '<key>CFBundleIconFile</key><string>Icone_validador</string>\n'
                    '<key>CFBundlePackageType</key><string>APPL</string>\n'
                    '<key>CFBundleIdentifier</key><string>com.validador.telefones</string>\n'
                    '<key>NSHighResolutionCapable</key><true/>\n'
                    '<key>LSBackgroundOnly</key><false/>\n'
                    '</dict></plist>\n'
                )
            self.progress.emit(97, "Atalho criado.")

            # Step 11: Save .version (97-100%)
            self.progress.emit(98, "Finalizando...")
            (install_path / ".version").write_text(APP_VERSION)
            self.progress.emit(100, "Concluido.")

            self.finished.emit(True, "")

        except Exception as exc:
            self.finished.emit(False, str(exc))


# ============================================================
#  STYLED COMPONENTS
# ============================================================
class DarkHeader(QFrame):
    """Dark top bar — shows step title + subtitle."""

    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet(f"background-color: {COLOR_DARK_HEADER}; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(0)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setAlignment(Qt.AlignVCenter)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(get_font(11, bold=True))
        self.title_lbl.setStyleSheet(f"color: {COLOR_HEADER_TEXT}; background: transparent;")

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setFont(get_font(9))
        self.sub_lbl.setStyleSheet(f"color: {COLOR_SUBTEXT}; background: transparent;")

        col.addStretch()
        col.addWidget(self.title_lbl)
        col.addWidget(self.sub_lbl)
        col.addStretch()

        layout.addLayout(col)
        layout.addStretch()

    def set_texts(self, title, subtitle):
        self.title_lbl.setText(title)
        self.sub_lbl.setText(subtitle)


class BlueButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(get_font(11, bold=True))
        self.setFixedSize(160, 40)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, hovered):
        bg = COLOR_BLUE_HOVER if hovered else COLOR_BLUE
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {bg};"
            f"  color: #ffffff;"
            f"  border: none;"
            f"  border-radius: 4px;"
            f"  font-size: 11pt;"
            f"  font-weight: bold;"
            f"}}"
        )

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)


# ============================================================
#  PAGE 1 — WELCOME
# ============================================================
class WelcomePage(QWidget):
    def __init__(self, on_continue):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Content area
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLOR_BG};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 48, 40, 48)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignCenter)

        # Logo
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(BUNDLE_DIR, "Icone_validador.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(
                120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("")
            logo_lbl.setFixedSize(120, 120)
        logo_lbl.setStyleSheet("background: transparent;")
        cl.addWidget(logo_lbl)

        cl.addSpacing(28)

        # App name
        name_lbl = QLabel(APP_NAME)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setFont(get_font(26, bold=True))
        name_lbl.setStyleSheet(f"color: {COLOR_BODY_TEXT}; background: transparent;")
        cl.addWidget(name_lbl)

        cl.addSpacing(10)

        # Version
        ver_lbl = QLabel(f"Vers\u00e3o {APP_VERSION}")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setFont(get_font(13))
        ver_lbl.setStyleSheet(f"color: {COLOR_SUBTEXT}; background: transparent;")
        cl.addWidget(ver_lbl)

        cl.addSpacing(20)

        # Disclaimer
        disclaimer = QLabel(
            "Este software foi desenvolvido para fins estritamente acad\u00eamicos "
            "e de uso interno, sem qualquer finalidade econ\u00f4mica ou comercial. "
            "A utiliza\u00e7\u00e3o inadequada deste programa \u00e9 de exclusiva "
            "responsabilidade do usu\u00e1rio. Respeite a legisla\u00e7\u00e3o vigente "
            "e a privacidade de terceiros."
        )
        disclaimer.setAlignment(Qt.AlignCenter)
        disclaimer.setWordWrap(True)
        disclaimer.setFont(get_font(9))
        disclaimer.setStyleSheet(f"color: #999999; background: transparent; padding: 0 20px;")
        cl.addWidget(disclaimer)

        cl.addStretch()

        # Continue button
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn = BlueButton("Continuar")
        btn.clicked.connect(on_continue)
        btn_row.addWidget(btn)
        cl.addLayout(btn_row)

        layout.addWidget(content, stretch=1)


# ============================================================
#  PAGE 2 — CONFIGURATION
# ============================================================
class ConfigPage(QWidget):
    def __init__(self, on_install, on_back):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = DarkHeader("Instala\u00e7\u00e3o", "OP\u00c7\u00d5ES")
        layout.addWidget(self.header)

        # Content
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLOR_BG};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 40, 40, 40)
        cl.setSpacing(0)

        # Label
        loc_lbl = QLabel("Local de instala\u00e7\u00e3o:")
        loc_lbl.setFont(get_font(13, bold=True))
        loc_lbl.setStyleSheet(f"color: {COLOR_BODY_TEXT}; background: transparent;")
        cl.addWidget(loc_lbl)

        cl.addSpacing(10)

        # Path row
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self.path_edit = QLineEdit(DEFAULT_INSTALL_DIR)
        self.path_edit.setFont(get_font(12))
        self.path_edit.setFixedHeight(36)
        self.path_edit.setStyleSheet(
            f"QLineEdit {{"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  border-radius: 3px;"
            f"  padding: 0 10px;"
            f"  color: {COLOR_BODY_TEXT};"
            f"  background-color: #ffffff;"
            f"  font-size: 12pt;"
            f"}}"
        )

        browse_btn = QPushButton("Procurar...")
        browse_btn.setFont(get_font(11))
        browse_btn.setFixedHeight(36)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(
            f"QPushButton {{"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  border-radius: 3px;"
            f"  padding: 0 14px;"
            f"  color: {COLOR_BODY_TEXT};"
            f"  background-color: {COLOR_LIGHT_BG};"
            f"  font-size: 11pt;"
            f"}}"
            f"QPushButton:hover {{ background-color: #e8e8e8; }}"
        )
        browse_btn.clicked.connect(self._browse)

        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse_btn)
        cl.addLayout(path_row)

        cl.addStretch()

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        back_btn = QPushButton("Voltar")
        back_btn.setFont(get_font(11))
        back_btn.setFixedSize(120, 40)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(
            f"QPushButton {{"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  border-radius: 4px;"
            f"  color: {COLOR_BODY_TEXT};"
            f"  background-color: {COLOR_LIGHT_BG};"
            f"  font-size: 11pt;"
            f"}}"
            f"QPushButton:hover {{ background-color: #e0e0e0; }}"
        )
        back_btn.clicked.connect(on_back)

        install_btn = BlueButton("Instalar")
        install_btn.clicked.connect(lambda: on_install(self.path_edit.text().strip()))

        btn_row.addWidget(back_btn)
        btn_row.addWidget(install_btn)
        cl.addLayout(btn_row)

        layout.addWidget(content, stretch=1)

    def _browse(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "Escolha a pasta de instala\u00e7\u00e3o", self.path_edit.text()
        )
        if chosen:
            self.path_edit.setText(chosen)


# ============================================================
#  PAGE 3 — INSTALLING
# ============================================================
class InstallingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        self._start_time = None
        self._current_pct = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top progress bar (thin, blue)
        self.top_bar = QProgressBar()
        self.top_bar.setRange(0, 100)
        self.top_bar.setValue(0)
        self.top_bar.setFixedHeight(4)
        self.top_bar.setTextVisible(False)
        self.top_bar.setStyleSheet(
            f"QProgressBar {{"
            f"  border: none;"
            f"  background-color: {COLOR_PROGRESS_BG};"
            f"}}"
            f"QProgressBar::chunk {{"
            f"  background-color: {COLOR_BLUE};"
            f"}}"
        )
        layout.addWidget(self.top_bar)

        # Header
        self.header = DarkHeader("Instalando (0%)", "CALCULANDO TEMPO RESTANTE")
        layout.addWidget(self.header)

        # Content
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLOR_BG};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 48, 40, 48)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignCenter)

        # Logo
        self.logo_lbl = QLabel()
        self.logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(BUNDLE_DIR, "Icone_validador.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(
                100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.logo_lbl.setPixmap(pix)
        else:
            self.logo_lbl.setFixedSize(100, 100)
        self.logo_lbl.setStyleSheet("background: transparent;")
        cl.addWidget(self.logo_lbl)

        cl.addSpacing(24)

        name_lbl = QLabel(APP_NAME)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setFont(get_font(22, bold=True))
        name_lbl.setStyleSheet(f"color: {COLOR_BODY_TEXT}; background: transparent;")
        cl.addWidget(name_lbl)

        cl.addSpacing(8)

        ver_lbl = QLabel(f"Vers\u00e3o {APP_VERSION}")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setFont(get_font(13))
        ver_lbl.setStyleSheet(f"color: {COLOR_SUBTEXT}; background: transparent;")
        cl.addWidget(ver_lbl)

        cl.addStretch()

        layout.addWidget(content, stretch=1)

    def start_timer(self):
        self._start_time = time.time()

    def update_progress(self, pct, _msg):
        self._current_pct = pct
        self.top_bar.setValue(pct)
        time_str = self._estimate_time(pct)
        self.header.set_texts(f"Instalando ({pct}%)", time_str)

    def _estimate_time(self, pct):
        if self._start_time is None or pct <= 0:
            return "CALCULANDO TEMPO RESTANTE"
        elapsed = time.time() - self._start_time
        if pct >= 100:
            return "CONCLU\u00cdDO"
        estimated_total = elapsed / (pct / 100.0)
        remaining = estimated_total - elapsed
        if remaining < 60:
            secs = max(1, int(remaining))
            return f"< {secs} SEGUNDO{'S' if secs != 1 else ''} RESTANTE"
        mins = int(remaining / 60)
        if mins == 1:
            return "< 1 MINUTO RESTANTE"
        return f"< {mins} MINUTOS RESTANTES"


# ============================================================
#  PAGE 4 — COMPLETE
# ============================================================
class CompletePage(QWidget):
    def __init__(self, on_open, on_close):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        content = QWidget()
        content.setStyleSheet(f"background-color: {COLOR_BG};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(60, 60, 60, 60)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignCenter)

        # Logo
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(BUNDLE_DIR, "Icone_validador.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(
                100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setFixedSize(100, 100)
        logo_lbl.setStyleSheet("background: transparent;")
        cl.addWidget(logo_lbl)

        cl.addSpacing(28)

        done_lbl = QLabel("Instala\u00e7\u00e3o conclu\u00edda")
        done_lbl.setAlignment(Qt.AlignCenter)
        done_lbl.setFont(get_font(24, bold=True))
        done_lbl.setStyleSheet(f"color: {COLOR_BODY_TEXT}; background: transparent;")
        cl.addWidget(done_lbl)

        cl.addSpacing(14)

        msg_lbl = QLabel(
            f"O {APP_NAME} foi instalado com sucesso."
        )
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setFont(get_font(13))
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {COLOR_SUBTEXT}; background: transparent;")
        cl.addWidget(msg_lbl)

        cl.addStretch()

        # Botão Abrir
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(12)

        open_btn = BlueButton("Continuar, abrir o programa")
        open_btn.setFixedSize(250, 44)
        open_btn.clicked.connect(on_open)
        btn_row.addWidget(open_btn)
        cl.addLayout(btn_row)

        cl.addSpacing(12)

        # Botão Sair
        exit_row = QHBoxLayout()
        exit_row.setAlignment(Qt.AlignCenter)
        exit_btn = QPushButton("Sair")
        exit_btn.setFont(get_font(10))
        exit_btn.setFixedSize(100, 32)
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.setStyleSheet(
            f"QPushButton {{"
            f"  border: none;"
            f"  color: {COLOR_SUBTEXT};"
            f"  background: transparent;"
            f"  font-size: 10pt;"
            f"}}"
            f"QPushButton:hover {{ color: {COLOR_BODY_TEXT}; }}"
        )
        exit_btn.clicked.connect(on_close)
        exit_row.addWidget(exit_btn)
        cl.addLayout(exit_row)

        layout.addWidget(content, stretch=1)


# ============================================================
#  PAGE: EXISTING INSTALLATION DETECTED
# ============================================================
class ExistingPage(QWidget):
    def __init__(self, install_path, on_open, on_reinstall, on_cancel):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        content = QWidget()
        content.setStyleSheet(f"background-color: {COLOR_BG};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(60, 48, 60, 48)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignCenter)

        # Logo
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(BUNDLE_DIR, "Icone_validador.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(
                100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
        logo_lbl.setStyleSheet("background: transparent;")
        cl.addWidget(logo_lbl)

        cl.addSpacing(24)

        title = QLabel("Instala\u00e7\u00e3o existente detectada")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(get_font(20, bold=True))
        title.setStyleSheet(f"color: {COLOR_BODY_TEXT}; background: transparent;")
        cl.addWidget(title)

        cl.addSpacing(12)

        path_lbl = QLabel(f"O programa j\u00e1 est\u00e1 instalado em:\n{install_path}")
        path_lbl.setAlignment(Qt.AlignCenter)
        path_lbl.setFont(get_font(11))
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet(f"color: {COLOR_SUBTEXT}; background: transparent;")
        cl.addWidget(path_lbl)

        cl.addSpacing(36)

        # Botão Abrir
        btn_open = BlueButton("Abrir o programa")
        btn_open.setFixedSize(220, 44)
        btn_open.clicked.connect(on_open)
        open_row = QHBoxLayout()
        open_row.setAlignment(Qt.AlignCenter)
        open_row.addWidget(btn_open)
        cl.addLayout(open_row)

        cl.addSpacing(12)

        # Botão Reinstalar
        btn_reinstall = QPushButton("Apagar e reinstalar")
        btn_reinstall.setFont(get_font(11))
        btn_reinstall.setMinimumWidth(240)
        btn_reinstall.setFixedHeight(38)
        btn_reinstall.setCursor(Qt.PointingHandCursor)
        btn_reinstall.setStyleSheet(
            f"QPushButton {{"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  border-radius: 4px;"
            f"  color: {COLOR_BODY_TEXT};"
            f"  background-color: {COLOR_LIGHT_BG};"
            f"  font-size: 11pt;"
            f"  padding: 0 16px;"
            f"  min-width: 200px;"
            f"}}"
            f"QPushButton:hover {{ background-color: #e0e0e0; }}"
        )
        btn_reinstall.clicked.connect(on_reinstall)
        reinstall_row = QHBoxLayout()
        reinstall_row.setAlignment(Qt.AlignCenter)
        reinstall_row.addWidget(btn_reinstall)
        cl.addLayout(reinstall_row)

        cl.addSpacing(12)

        # Botão Cancelar
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFont(get_font(10))
        btn_cancel.setFixedSize(120, 32)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton {{"
            f"  border: none;"
            f"  color: {COLOR_SUBTEXT};"
            f"  background: transparent;"
            f"  font-size: 10pt;"
            f"}}"
            f"QPushButton:hover {{ color: {COLOR_BODY_TEXT}; }}"
        )
        btn_cancel.clicked.connect(on_cancel)
        cancel_row = QHBoxLayout()
        cancel_row.setAlignment(Qt.AlignCenter)
        cancel_row.addWidget(btn_cancel)
        cl.addLayout(cancel_row)

        cl.addStretch()
        layout.addWidget(content, stretch=1)


# ============================================================
#  DETECT EXISTING INSTALLATION
# ============================================================
def find_existing_install():
    """Procura instalação existente nos locais padrão."""
    locations = [
        str(Path.home() / "ValidadorTelefones"),
        str(Path.home() / "Applications" / "ValidadorTelefones"),
        "/opt/ValidadorTelefones",
        str(Path.home() / ".local" / "share" / "ValidadorTelefones"),
    ]
    for loc in locations:
        if os.path.exists(os.path.join(loc, "app_gui.py")):
            return loc
    return None


# ============================================================
#  MAIN WINDOW
# ============================================================
class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} \u2014 Instalador")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(f"QWidget {{ background-color: {COLOR_BG}; }}")

        # Window icon
        icon_path = os.path.join(BUNDLE_DIR, "Icone_validador.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - WINDOW_WIDTH) // 2
        y = (screen.height() - WINDOW_HEIGHT) // 2
        self.move(x, y)

        # Stack
        self._stack = QStackedWidget(self)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._stack)

        self._existing_path = find_existing_install()

        # Pages
        self._page_welcome = WelcomePage(on_continue=self._go_config)
        self._page_config = ConfigPage(
            on_install=self._start_install,
            on_back=self._go_welcome
        )
        self._page_installing = InstallingPage()
        self._page_complete = CompletePage(on_open=self._open_installed, on_close=self.close)

        if self._existing_path:
            self._page_existing = ExistingPage(
                install_path=self._existing_path,
                on_open=self._open_existing,
                on_reinstall=self._reinstall,
                on_cancel=self.close
            )
            self._stack.addWidget(self._page_existing)   # index 0
            self._stack.addWidget(self._page_welcome)    # index 1
            self._stack.addWidget(self._page_config)     # index 2
            self._stack.addWidget(self._page_installing) # index 3
            self._stack.addWidget(self._page_complete)   # index 4
            self._stack.setCurrentIndex(0)
            self._idx_welcome = 1
            self._idx_config = 2
            self._idx_installing = 3
            self._idx_complete = 4
        else:
            self._stack.addWidget(self._page_welcome)    # index 0
            self._stack.addWidget(self._page_config)     # index 1
            self._stack.addWidget(self._page_installing) # index 2
            self._stack.addWidget(self._page_complete)   # index 3
            self._idx_welcome = 0
            self._idx_config = 1
            self._idx_installing = 2
            self._idx_complete = 3

        self._thread = None

    def _open_existing(self):
        """Abre o programa existente e fecha o instalador."""
        app_path = os.path.join(str(Path.home()), "Desktop", "Validador de Telefones.app")
        if IS_MAC and os.path.exists(app_path):
            subprocess.Popen(["open", app_path])
        else:
            launcher = os.path.join(self._existing_path, "executar.sh")
            if os.path.exists(launcher):
                subprocess.Popen(["bash", launcher])
        self.close()

    def _reinstall(self):
        """Confirma e reinstala — vai direto para a tela de instalação."""
        msg, btns = styled_msgbox(
            self, "Confirmar",
            f"Isso vai apagar todos os arquivos em:\n\n"
            f"{self._existing_path}\n\n"
            f"(O ambiente virtual será preservado para acelerar a reinstalação.)\n\n"
            f"Deseja continuar?",
            buttons=[
                ("Sim, apagar e reinstalar", QMessageBox.AcceptRole),
                ("Cancelar", QMessageBox.RejectRole),
            ],
            icon_type="warning"
        )

        if msg.clickedButton() == btns[0]:
            # Go directly to installing page with reinstall mode
            self._page_config.path_edit.setText(self._existing_path)
            self._stack.setCurrentIndex(self._idx_installing)
            self._page_installing.start_timer()

            self._thread = InstallerThread(self._existing_path, reinstall_mode=True)
            self._thread.progress.connect(self._page_installing.update_progress)
            self._thread.finished.connect(self._on_install_done)
            self._thread.start()

    def _go_welcome(self):
        self._stack.setCurrentIndex(self._idx_welcome)

    def _go_config(self):
        self._stack.setCurrentIndex(self._idx_config)

    def _open_installed(self):
        """Abre o programa instalado e fecha o instalador."""
        app_path = os.path.join(str(Path.home()), "Desktop", "Validador de Telefones.app")
        if IS_MAC and os.path.exists(app_path):
            subprocess.Popen(["open", app_path])
        else:
            install_dir = self._page_config.path_edit.text().strip()
            launcher = os.path.join(install_dir, "executar.sh")
            if os.path.exists(launcher):
                subprocess.Popen(["bash", launcher])
        self.close()

    def _start_install(self, path):
        if not path:
            return

        # Popup de declaração
        msg, btns = styled_msgbox(
            self, "Declara\u00e7\u00e3o de Uso",
            "Declaro que utilizarei este programa de forma \u00e9tica e "
            "respons\u00e1vel, apenas para os fins a que se destina, com as "
            "autoriza\u00e7\u00f5es necess\u00e1rias, em conformidade com a "
            "legisla\u00e7\u00e3o brasileira de telecomunica\u00e7\u00f5es e "
            "prote\u00e7\u00e3o de dados.",
            buttons=[
                ("Sim, declaro", QMessageBox.AcceptRole),
                ("N\u00e3o, cancelar", QMessageBox.RejectRole),
            ],
            icon_type="info"
        )

        if msg.clickedButton() != btns[0]:
            return

        self._stack.setCurrentIndex(self._idx_installing)
        self._page_installing.start_timer()

        self._thread = InstallerThread(path)
        self._thread.progress.connect(self._page_installing.update_progress)
        self._thread.finished.connect(self._on_install_done)
        self._thread.start()

    def _on_install_done(self, success, error_msg):
        if success:
            self._stack.setCurrentIndex(self._idx_complete)
        else:
            styled_msgbox(
                self, "Erro na instala\u00e7\u00e3o",
                f"Ocorreu um erro durante a instala\u00e7\u00e3o:\n\n{error_msg}",
                icon_type="critical"
            )
            self._stack.setCurrentIndex(self._idx_config)

    def closeEvent(self, event):
        """Warn the user if installation is still running."""
        installing_visible = (
            self._stack.currentIndex() == self._idx_installing
        )
        thread_running = (
            self._thread is not None and self._thread.isRunning()
        )
        if installing_visible and thread_running:
            msg, btns = styled_msgbox(
                self,
                "Cancelar instala\u00e7\u00e3o?",
                "A instala\u00e7\u00e3o ainda n\u00e3o foi conclu\u00edda. "
                "Se voc\u00ea fechar agora, os dados poder\u00e3o ser perdidos "
                "e a instala\u00e7\u00e3o ficar\u00e1 incompleta.",
                buttons=[
                    ("Continuar instala\u00e7\u00e3o", QMessageBox.RejectRole),
                    ("Sair mesmo assim", QMessageBox.AcceptRole),
                ],
                icon_type="warning"
            )
            # btns[0] = "Continuar instalação" (blue/positive), btns[1] = "Sair mesmo assim" (gray)
            if msg.clickedButton() == btns[1]:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ============================================================
#  ENTRY POINT
# ============================================================
def main():
    # Prevenir múltiplas instâncias
    import tempfile
    import fcntl
    lock_file = os.path.join(tempfile.gettempdir(), "validador_installer.lock")
    fp = open(lock_file, "w")
    try:
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        # Já tem uma instância rodando — sair silenciosamente
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Load Montserrat from system if available
    QFontDatabase.addApplicationFont(
        os.path.join(
            str(Path.home()),
            *(
                ("Library", "Fonts", "Montserrat-Regular.ttf")
                if IS_MAC
                else (".local", "share", "fonts", "Montserrat-Regular.ttf")
            )
        )
    )

    window = InstallerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
