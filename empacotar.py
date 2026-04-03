#!/usr/bin/env python3
"""
Empacotador — Transforma o instalador GUI em arquivo único executável.

Gera:
  Windows: SETUP_ValidadorTelefones.exe
  Mac:     SETUP_ValidadorTelefones.app
  Linux:   SETUP_ValidadorTelefones

Uso:
  pip install pyinstaller pyqt5
  python empacotar.py
"""

import subprocess
import platform
import sys
import os

def main():
    so = platform.system()
    nome = "SETUP_ValidadorTelefones"

    print(f"{'='*50}")
    print(f"  Empacotando instalador para {so}")
    print(f"{'='*50}")
    print()

    # Verificar PyInstaller
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  ⚠️  PyInstaller não encontrado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Verificar PyQt5
    try:
        from PyQt5 import QtWidgets
        print(f"  ✅ PyQt5 encontrado")
    except ImportError:
        print("  ⚠️  PyQt5 não encontrado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyqt5"])

    # Arquivos a incluir no pacote
    data_files = [
        "config.py",
        "main.py",
        "phone_controller.py",
        "audio_recorder.py",
        "transcriber.py",
        "classifier.py",
        "excel_handler.py",
        "requirements.txt",
    ]

    # Montar comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # Arquivo único
        "--windowed",          # Sem janela de console
        f"--name={nome}",
        "--clean",
    ]

    # Adicionar data files
    sep = ";" if so == "Windows" else ":"
    for f in data_files:
        if os.path.exists(f):
            cmd.append(f"--add-data={f}{sep}.")

    cmd.append("installer_gui.py")

    print(f"\n  Executando PyInstaller...\n")
    print(f"  {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n{'='*50}")
        print(f"  ✅ Empacotamento concluído!")
        print(f"{'='*50}")

        if so == "Windows":
            print(f"\n  Arquivo: dist/{nome}.exe")
        elif so == "Darwin":
            print(f"\n  Arquivo: dist/{nome}.app")
        else:
            print(f"\n  Arquivo: dist/{nome}")

        print(f"\n  Distribua esse arquivo único.")
        print(f"  A pessoa só precisa clicar duas vezes nele.")
    else:
        print(f"\n  ❌ Erro no empacotamento!")


if __name__ == "__main__":
    main()
