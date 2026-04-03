#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   📞 Validador de Telefones — Instalador Gráfico    ║
║   PyQt5 Wizard • Windows / Mac / Linux              ║
╚══════════════════════════════════════════════════════╝
"""

import sys
import os
import platform
import subprocess
import threading
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWizard, QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
    QProgressBar, QTextEdit, QCheckBox, QLineEdit, QPushButton,
    QFileDialog, QComboBox, QGroupBox, QRadioButton, QFrame,
    QMessageBox, QSpacerItem, QSizePolicy, QWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon, QPainter


# ============================================================
#  CONSTANTES
# ============================================================
APP_NAME = "Validador de Telefones"
APP_VERSION = "1.0"
WINDOW_WIDTH = 750
WINDOW_HEIGHT = 520

# Detectar SO
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Pasta padrão de instalação
if IS_WINDOWS:
    DEFAULT_INSTALL_DIR = str(Path.home() / "PhoneValidator")
elif IS_MAC:
    DEFAULT_INSTALL_DIR = str(Path.home() / "PhoneValidator")
else:
    DEFAULT_INSTALL_DIR = str(Path.home() / "PhoneValidator")


# ============================================================
#  ESTILO (Tema Escuro Moderno)
# ============================================================
STYLESHEET = """
QWizard {
    background-color: #1a1a2e;
}

QWizardPage {
    background-color: #1a1a2e;
    color: #e0e0e0;
}

QLabel {
    color: #e0e0e0;
    font-size: 13px;
}

QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #00d4aa;
    padding: 5px 0;
}

QLabel#subtitle {
    font-size: 14px;
    color: #8892b0;
    padding-bottom: 10px;
}

QLabel#version {
    font-size: 11px;
    color: #5a6480;
}

QLabel#step_label {
    font-size: 12px;
    color: #00d4aa;
    font-weight: bold;
}

QLabel#feature_icon {
    font-size: 20px;
}

QPushButton {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    min-width: 90px;
}

QPushButton:hover {
    background-color: #0f3460;
    border-color: #00d4aa;
}

QPushButton:pressed {
    background-color: #00d4aa;
    color: #1a1a2e;
}

QPushButton#btn_primary {
    background-color: #00d4aa;
    color: #1a1a2e;
    font-weight: bold;
    border: none;
}

QPushButton#btn_primary:hover {
    background-color: #00e8bb;
}

QPushButton#btn_browse {
    min-width: 40px;
    padding: 6px 12px;
    font-size: 16px;
}

QProgressBar {
    border: none;
    border-radius: 8px;
    text-align: center;
    background-color: #16213e;
    color: #e0e0e0;
    font-size: 12px;
    min-height: 22px;
}

QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00d4aa, stop:1 #0ea5e9);
}

QTextEdit {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}

QCheckBox {
    color: #e0e0e0;
    font-size: 13px;
    spacing: 8px;
    padding: 4px 0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #0f3460;
    background-color: #16213e;
}

QCheckBox::indicator:checked {
    background-color: #00d4aa;
    border-color: #00d4aa;
}

QCheckBox::indicator:hover {
    border-color: #00d4aa;
}

QRadioButton {
    color: #e0e0e0;
    font-size: 13px;
    spacing: 8px;
    padding: 4px 0;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #0f3460;
    background-color: #16213e;
}

QRadioButton::indicator:checked {
    background-color: #00d4aa;
    border-color: #00d4aa;
}

QLineEdit {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #00d4aa;
}

QComboBox {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QGroupBox {
    color: #00d4aa;
    border: 1px solid #1e2d3d;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: bold;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    padding: 0 8px;
}

QFrame#separator {
    background-color: #1e2d3d;
    max-height: 1px;
}

QFrame#feature_card {
    background-color: #16213e;
    border-radius: 8px;
    padding: 12px;
}
"""


# ============================================================
#  THREAD DE INSTALAÇÃO
# ============================================================
class InstallerThread(QThread):
    """Executa os comandos de instalação em background."""
    progress = pyqtSignal(int)       # 0-100
    log_message = pyqtSignal(str)    # Mensagens para o log
    step_changed = pyqtSignal(str)   # Nome do passo atual
    finished_ok = pyqtSignal()       # Instalação concluída com sucesso
    finished_error = pyqtSignal(str) # Instalação falhou

    def __init__(self, install_dir, options):
        super().__init__()
        self.install_dir = install_dir
        self.options = options

    def log(self, msg):
        self.log_message.emit(msg)

    def run_cmd(self, cmd, desc=""):
        """Executa um comando e retorna (sucesso, output)."""
        if desc:
            self.log(f"  → {desc}")
        try:
            if IS_WINDOWS:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300,
                    shell=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300,
                    shell=isinstance(cmd, str)
                )
            if result.returncode != 0 and result.stderr.strip():
                self.log(f"    ⚠ {result.stderr.strip()[:200]}")
            return result.returncode == 0, result.stdout
        except subprocess.TimeoutExpired:
            self.log(f"    ⚠ Timeout")
            return False, ""
        except Exception as e:
            self.log(f"    ⚠ Erro: {e}")
            return False, ""

    def run(self):
        try:
            steps = self._get_steps()
            total = len(steps)

            for i, (name, func) in enumerate(steps):
                self.step_changed.emit(name)
                self.log(f"\n{'─'*40}")
                self.log(f"  {name}")
                self.log(f"{'─'*40}")

                success = func()
                if not success:
                    self.log(f"\n  ❌ Falha em: {name}")
                    # Continua mesmo com erro (melhor tentar tudo)

                pct = int((i + 1) / total * 100)
                self.progress.emit(pct)

            self.log(f"\n{'═'*40}")
            self.log("  ✅ Instalação concluída!")
            self.log(f"{'═'*40}")
            self.finished_ok.emit()

        except Exception as e:
            self.finished_error.emit(str(e))

    def _get_steps(self):
        """Retorna lista de passos baseado no SO."""
        steps = [
            ("Criando pastas", self._criar_pastas),
            ("Copiando arquivos", self._copiar_arquivos),
        ]

        if IS_WINDOWS:
            steps += [
                ("Verificando Python", self._check_python),
                ("Criando ambiente virtual", self._criar_venv),
                ("Instalando bibliotecas Python", self._instalar_pip),
                ("Instalando Whisper", self._instalar_whisper),
                ("Verificando ADB", self._check_adb),
                ("Verificando FFmpeg", self._check_ffmpeg),
                ("Baixando modelo de voz", self._baixar_modelo),
                ("Criando atalho na Área de Trabalho", self._criar_atalho_windows),
            ]
        elif IS_MAC:
            steps += [
                ("Verificando Homebrew", self._check_brew),
                ("Instalando dependências (brew)", self._instalar_brew_deps),
                ("Criando ambiente virtual", self._criar_venv),
                ("Instalando bibliotecas Python", self._instalar_pip),
                ("Instalando Whisper", self._instalar_whisper),
                ("Baixando modelo de voz", self._baixar_modelo),
                ("Configurando permissões", self._config_mac),
            ]
        else:  # Linux
            steps += [
                ("Instalando dependências (apt)", self._instalar_apt),
                ("Criando ambiente virtual", self._criar_venv),
                ("Instalando bibliotecas Python", self._instalar_pip),
                ("Instalando Whisper", self._instalar_whisper),
                ("Baixando modelo de voz", self._baixar_modelo),
                ("Configurando USB (udev)", self._config_udev),
                ("Criando atalho", self._criar_atalho_linux),
            ]

        steps.append(("Finalizando", self._finalizar))
        return steps

    # --- Passos comuns ---

    def _criar_pastas(self):
        for pasta in ["audios", "resultados", "planilhas"]:
            p = os.path.join(self.install_dir, pasta)
            os.makedirs(p, exist_ok=True)
            self.log(f"    📁 {pasta}/")
        return True

    def _copiar_arquivos(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        arquivos = [
            "config.py", "main.py", "main_cloud.py", "phone_controller.py",
            "audio_recorder.py", "transcriber.py", "classifier.py", "cloud_handler.py", "updater.py", "scheduler.py", "app_gui.py",
            "excel_handler.py", "requirements.txt", "version.json", "Icone_validador.png", "Icone_validador.icns", "LEIA-ME.html",
        ]
        for arq in arquivos:
            src = os.path.join(src_dir, arq)
            dst = os.path.join(self.install_dir, arq)
            if os.path.exists(src) and src != dst:
                shutil.copy2(src, dst)
                self.log(f"    📄 {arq}")
            elif not os.path.exists(src):
                self.log(f"    ⚠ {arq} não encontrado")
        return True

    def _criar_venv(self):
        venv_path = os.path.join(self.install_dir, "venv")
        if os.path.exists(venv_path):
            self.log("    Ambiente virtual já existe")
            return True
        ok, _ = self.run_cmd(
            f"{sys.executable} -m venv \"{venv_path}\"",
            "Criando venv..."
        )
        return ok

    def _get_pip(self):
        """Retorna caminho do pip no venv."""
        venv = os.path.join(self.install_dir, "venv")
        if IS_WINDOWS:
            return os.path.join(venv, "Scripts", "pip.exe")
        return os.path.join(venv, "bin", "pip")

    def _get_python_venv(self):
        """Retorna caminho do python no venv."""
        venv = os.path.join(self.install_dir, "venv")
        if IS_WINDOWS:
            return os.path.join(venv, "Scripts", "python.exe")
        return os.path.join(venv, "bin", "python3")

    def _instalar_pip(self):
        pip = self._get_pip()
        self.run_cmd(f"\"{pip}\" install --upgrade pip", "Atualizando pip...")
        ok, _ = self.run_cmd(f"\"{pip}\" install openpyxl pyaudio", "Instalando openpyxl e pyaudio...")
        if not ok:
            # PyAudio pode falhar no Windows — tentar com wheel
            self.log("    Tentando PyAudio alternativo...")
            self.run_cmd(f"\"{pip}\" install openpyxl", "openpyxl...")
            self.run_cmd(f"\"{pip}\" install pyaudio", "pyaudio...")
        return True

    def _instalar_whisper(self):
        pip = self._get_pip()
        ok, _ = self.run_cmd(
            f"\"{pip}\" install openai-whisper",
            "Instalando Whisper (pode demorar alguns minutos)..."
        )
        return ok

    def _baixar_modelo(self):
        python = self._get_python_venv()
        modelo = self.options.get("whisper_model", "base")
        ok, _ = self.run_cmd(
            f"\"{python}\" -c \"import whisper; whisper.load_model('{modelo}')\"",
            f"Baixando modelo '{modelo}'..."
        )
        return ok

    def _finalizar(self):
        self.log("    Verificando instalação...")
        python = self._get_python_venv()
        ok, _ = self.run_cmd(
            f"\"{python}\" -c \"import openpyxl; import whisper; print('OK')\"",
            "Testando imports..."
        )
        if ok:
            self.log("    ✅ Todos os módulos carregados com sucesso!")
        return True

    # --- Windows ---

    def _check_python(self):
        ok, out = self.run_cmd("python --version", "Verificando Python...")
        if ok:
            self.log(f"    ✅ {out.strip()}")
        return ok

    def _check_adb(self):
        ok, _ = self.run_cmd("adb version", "Verificando ADB...")
        if ok:
            self.log("    ✅ ADB encontrado")
        else:
            self.log("    ⚠ ADB não encontrado!")
            self.log("    Baixe em: https://developer.android.com/tools/releases/platform-tools")
            self.log("    Extraia e adicione a pasta ao PATH do sistema")
        return True  # Não bloquear por isso

    def _check_ffmpeg(self):
        ok, _ = self.run_cmd("ffmpeg -version", "Verificando FFmpeg...")
        if ok:
            self.log("    ✅ FFmpeg encontrado")
        else:
            self.log("    ⚠ FFmpeg não encontrado!")
            self.log("    Instale: choco install ffmpeg  OU  scoop install ffmpeg")
            self.log("    Ou baixe em: https://ffmpeg.org/download.html")
        return True

    def _criar_atalho_windows(self):
        try:
            desktop = os.path.join(Path.home(), "Desktop")
            if not os.path.exists(desktop):
                desktop = os.path.join(Path.home(), "Área de Trabalho")

            # Criar .bat para executar
            bat_path = os.path.join(self.install_dir, "EXECUTAR.bat")
            python_venv = self._get_python_venv()
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{self.install_dir}"\n')
                f.write(f'"{python_venv}" main.py\n')
                f.write(f'pause\n')

            # Criar atalho .bat na área de trabalho
            shortcut_path = os.path.join(desktop, "Validador de Telefones.bat")
            with open(shortcut_path, "w", encoding="utf-8") as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{self.install_dir}"\n')
                f.write(f'"{python_venv}" main.py\n')
                f.write(f'pause\n')

            self.log(f"    📌 Atalho criado na Área de Trabalho")
            return True
        except Exception as e:
            self.log(f"    ⚠ Não foi possível criar atalho: {e}")
            return True

    # --- Mac ---

    def _check_brew(self):
        ok, _ = self.run_cmd("brew --version", "Verificando Homebrew...")
        if ok:
            self.log("    ✅ Homebrew encontrado")
        else:
            self.log("    Instalando Homebrew...")
            self.run_cmd(
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                "Baixando Homebrew..."
            )
        return True

    def _instalar_brew_deps(self):
        deps = ["ffmpeg", "portaudio", "android-platform-tools"]
        for dep in deps:
            self.run_cmd(f"brew install {dep}", f"Instalando {dep}...")
        return True

    def _config_mac(self):
        self.run_cmd(f"chmod +x \"{self.install_dir}\"/*.sh", "Permissões...")
        self.run_cmd(f"xattr -r -d com.apple.quarantine \"{self.install_dir}\"", "Quarentena...")
        return True

    # --- Linux ---

    def _instalar_apt(self):
        deps = "python3 python3-pip python3-venv android-tools-adb ffmpeg portaudio19-dev python3-pyaudio"
        ok, _ = self.run_cmd(
            f"sudo apt install -y {deps}",
            "Instalando pacotes do sistema..."
        )
        return ok

    def _config_udev(self):
        rules = (
            'SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ATTR{idVendor}=="2717", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ATTR{idVendor}=="22b8", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ATTR{idVendor}=="1004", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", MODE="0666", GROUP="plugdev"\n'
        )
        try:
            rules_file = "/etc/udev/rules.d/51-android.rules"
            self.run_cmd(f"sudo bash -c 'echo \"{rules}\" > {rules_file}'", "Regras USB...")
            self.run_cmd("sudo udevadm control --reload-rules", "Recarregando udev...")
            return True
        except:
            return True

    def _criar_atalho_linux(self):
        desktop_file = os.path.join(
            Path.home(), ".local", "share", "applications", "phone-validator.desktop"
        )
        python_venv = self._get_python_venv()
        content = (
            "[Desktop Entry]\n"
            f"Name={APP_NAME}\n"
            "Comment=Validador de Telefones\n"
            f"Exec=bash -c 'cd \"{self.install_dir}\" && \"{python_venv}\" main.py; exec bash'\n"
            "Terminal=true\n"
            "Type=Application\n"
            "Categories=Utility;\n"
        )
        try:
            os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
            with open(desktop_file, "w") as f:
                f.write(content)
            os.chmod(desktop_file, 0o755)
            self.log("    📌 Atalho criado no menu de aplicativos")
        except Exception as e:
            self.log(f"    ⚠ {e}")
        return True


# ============================================================
#  PÁGINAS DO WIZARD
# ============================================================

class WelcomePage(QWizardPage):
    """Página 1: Bem-vindo."""

    def __init__(self):
        super().__init__()
        self.setTitle("")

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(40, 20, 40, 20)

        # Ícone grande
        icon_label = QLabel("📞")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFont(QFont("Segoe UI Emoji", 48))
        layout.addWidget(icon_label)

        # Título
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Versão
        version = QLabel(f"Versão {APP_VERSION}")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # Separador
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        layout.addSpacing(10)

        # Features
        features = [
            ("📱", "Discagem automática via celular Android (ADB)"),
            ("🧠", "Reconhecimento de voz com inteligência artificial"),
            ("📊", "Classificação automática das chamadas"),
            ("📋", "Resultados exportados em planilha Excel"),
        ]

        for emoji, text in features:
            row = QHBoxLayout()
            row.setSpacing(12)

            icon = QLabel(emoji)
            icon.setObjectName("feature_icon")
            icon.setFixedWidth(30)
            row.addWidget(icon)

            desc = QLabel(text)
            desc.setWordWrap(True)
            row.addWidget(desc)

            layout.addLayout(row)

        layout.addStretch()

        # SO detectado
        so = "Windows" if IS_WINDOWS else ("macOS" if IS_MAC else "Linux")
        so_label = QLabel(f"Sistema detectado: {so} • Python {platform.python_version()}")
        so_label.setObjectName("version")
        so_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(so_label)

        self.setLayout(layout)


class ConfigPage(QWizardPage):
    """Página 2: Configurações."""

    def __init__(self):
        super().__init__()
        self.setTitle("")

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(40, 20, 40, 20)

        # Título
        step = QLabel("⚙️  Configurações")
        step.setObjectName("title")
        layout.addWidget(step)

        subtitle = QLabel("Escolha onde instalar e as opções do sistema")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # --- Local de instalação ---
        group_dir = QGroupBox("Local de Instalação")
        dir_layout = QHBoxLayout()

        self.dir_input = QLineEdit(DEFAULT_INSTALL_DIR)
        self.dir_input.setPlaceholderText("Pasta de instalação")
        dir_layout.addWidget(self.dir_input)

        btn_browse = QPushButton("📁")
        btn_browse.setObjectName("btn_browse")
        btn_browse.clicked.connect(self._browse)
        dir_layout.addWidget(btn_browse)

        group_dir.setLayout(dir_layout)
        layout.addWidget(group_dir)

        # --- Modo de gravação ---
        group_rec = QGroupBox("Modo de Gravação de Áudio")
        rec_layout = QVBoxLayout()

        self.radio_mic = QRadioButton("🎙️  Microfone do computador (celular no viva-voz)")
        self.radio_mic.setChecked(True)
        rec_layout.addWidget(self.radio_mic)

        self.radio_app = QRadioButton("📱  App de gravação no celular (ACR, Cube, etc.)")
        rec_layout.addWidget(self.radio_app)

        group_rec.setLayout(rec_layout)
        layout.addWidget(group_rec)

        # --- Modelo Whisper ---
        group_model = QGroupBox("Modelo de Reconhecimento de Voz")
        model_layout = QVBoxLayout()

        model_info = QLabel("Modelos maiores são mais precisos, mas mais lentos e pesados.")
        model_info.setObjectName("subtitle")
        model_layout.addWidget(model_info)

        self.combo_model = QComboBox()
        self.combo_model.addItem("tiny  —  75 MB, muito rápido, precisão básica", "tiny")
        self.combo_model.addItem("base  —  150 MB, rápido, boa precisão (recomendado)", "base")
        self.combo_model.addItem("small  —  500 MB, médio, muito preciso", "small")
        self.combo_model.addItem("medium  —  1.5 GB, lento, excelente precisão", "medium")
        self.combo_model.setCurrentIndex(1)  # base como padrão
        model_layout.addWidget(self.combo_model)

        group_model.setLayout(model_layout)
        layout.addWidget(group_model)

        # --- Opções extras ---
        group_opts = QGroupBox("Opções")
        opts_layout = QVBoxLayout()

        self.check_shortcut = QCheckBox("Criar atalho na Área de Trabalho")
        self.check_shortcut.setChecked(True)
        opts_layout.addWidget(self.check_shortcut)

        self.check_adb = QCheckBox("Instalar/verificar ADB (Android Debug Bridge)")
        self.check_adb.setChecked(True)
        opts_layout.addWidget(self.check_adb)

        group_opts.setLayout(opts_layout)
        layout.addWidget(group_opts)

        layout.addStretch()

        # Registrar campos para o wizard
        self.registerField("install_dir", self.dir_input)

        self.setLayout(layout)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de instalação")
        if folder:
            self.dir_input.setText(folder)

    def get_options(self):
        return {
            "install_dir": self.dir_input.text(),
            "recording_mode": "microfone" if self.radio_mic.isChecked() else "app_android",
            "whisper_model": self.combo_model.currentData(),
            "create_shortcut": self.check_shortcut.isChecked(),
            "install_adb": self.check_adb.isChecked(),
        }


class InstallPage(QWizardPage):
    """Página 3: Progresso da instalação."""

    def __init__(self):
        super().__init__()
        self.setTitle("")
        self._complete = False

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(40, 20, 40, 20)

        # Título
        step = QLabel("📦  Instalando...")
        step.setObjectName("title")
        layout.addWidget(step)

        # Passo atual
        self.step_label = QLabel("Preparando...")
        self.step_label.setObjectName("step_label")
        layout.addWidget(self.step_label)

        # Barra de progresso
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Log
        log_label = QLabel("Detalhes:")
        log_label.setObjectName("subtitle")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def initializePage(self):
        """Começa a instalação quando a página aparece."""
        wizard = self.wizard()
        config_page = wizard.page(1)
        options = config_page.get_options()
        install_dir = options["install_dir"]

        self.thread = InstallerThread(install_dir, options)
        self.thread.progress.connect(self._on_progress)
        self.thread.log_message.connect(self._on_log)
        self.thread.step_changed.connect(self._on_step)
        self.thread.finished_ok.connect(self._on_finished)
        self.thread.finished_error.connect(self._on_error)
        self.thread.start()

    def _on_progress(self, value):
        self.progress.setValue(value)

    def _on_log(self, msg):
        self.log_text.append(msg)
        # Auto scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_step(self, step_name):
        self.step_label.setText(f"⏳  {step_name}")

    def _on_finished(self):
        self.step_label.setText("✅  Instalação concluída!")
        self.progress.setValue(100)
        self._complete = True
        self.completeChanged.emit()

    def _on_error(self, error):
        self.step_label.setText(f"❌  Erro: {error}")
        self._on_log(f"\n❌ ERRO: {error}")
        self._complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self._complete


class FinishPage(QWizardPage):
    """Página 4: Conclusão."""

    def __init__(self):
        super().__init__()
        self.setTitle("")

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(40, 30, 40, 20)

        # Ícone
        icon = QLabel("🎉")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont("Segoe UI Emoji", 48))
        layout.addWidget(icon)

        # Título
        title = QLabel("Instalação Concluída!")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        # Próximos passos
        steps_title = QLabel("Próximos passos:")
        steps_title.setObjectName("step_label")
        layout.addWidget(steps_title)

        steps = [
            "1️⃣  Conecte o celular Android via cabo USB",
            "2️⃣  Ative 'Depuração USB' no celular",
            "      (Configurações → Sobre → toque 7x em 'Número da versão'",
            "       → Opções de desenvolvedor → Depuração USB)",
            "3️⃣  Coloque a planilha .xlsx na pasta 'planilhas/'",
            "4️⃣  Execute o programa pelo atalho ou pelo terminal",
        ]

        for s in steps:
            lbl = QLabel(s)
            lbl.setStyleSheet("padding-left: 10px;")
            layout.addWidget(lbl)

        layout.addStretch()

        # Botão abrir pasta
        self.btn_open = QPushButton("📂  Abrir Pasta de Instalação")
        self.btn_open.setObjectName("btn_primary")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_folder)
        layout.addWidget(self.btn_open, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.setLayout(layout)

    def _open_folder(self):
        wizard = self.wizard()
        config_page = wizard.page(1)
        install_dir = config_page.dir_input.text()

        if os.path.exists(install_dir):
            if IS_WINDOWS:
                os.startfile(install_dir)
            elif IS_MAC:
                subprocess.run(["open", install_dir])
            else:
                subprocess.run(["xdg-open", install_dir])


# ============================================================
#  WIZARD PRINCIPAL
# ============================================================
class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} — Instalador")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWizardStyle(QWizard.ModernStyle)

        # Botões em português
        self.setButtonText(QWizard.NextButton, "Próximo ›")
        self.setButtonText(QWizard.BackButton, "‹ Voltar")
        self.setButtonText(QWizard.CancelButton, "Cancelar")
        self.setButtonText(QWizard.FinishButton, "Concluir")

        # Páginas
        self.addPage(WelcomePage())      # 0
        self.addPage(ConfigPage())       # 1
        self.addPage(InstallPage())      # 2
        self.addPage(FinishPage())       # 3


# ============================================================
#  MAIN
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    # Tema escuro no Fusion
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#1a1a2e"))
    palette.setColor(QPalette.WindowText, QColor("#e0e0e0"))
    palette.setColor(QPalette.Base, QColor("#16213e"))
    palette.setColor(QPalette.AlternateBase, QColor("#1a1a2e"))
    palette.setColor(QPalette.ToolTipBase, QColor("#16213e"))
    palette.setColor(QPalette.ToolTipText, QColor("#e0e0e0"))
    palette.setColor(QPalette.Text, QColor("#e0e0e0"))
    palette.setColor(QPalette.Button, QColor("#16213e"))
    palette.setColor(QPalette.ButtonText, QColor("#e0e0e0"))
    palette.setColor(QPalette.Highlight, QColor("#00d4aa"))
    palette.setColor(QPalette.HighlightedText, QColor("#1a1a2e"))
    app.setPalette(palette)

    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
