#!/bin/bash
# ================================================================
#  Instalador do Validador de Telefones
#  Baixa tudo do GitHub, instala PyQt5 se necessário, e abre
#  o instalador gráfico profissional.
# ================================================================

set -e

REPO="https://raw.githubusercontent.com/doscarsoares/validador-telefones/main"
TEMP_DIR="/tmp/validador_installer"

echo ""
echo "  VALIDADOR DE TELEFONES — Preparando instalador..."
echo ""

# Criar pasta temporária
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# 1. Garantir Python3
echo "  [1/4] Verificando Python..."
if ! command -v python3 &>/dev/null; then
    echo "  Instalando Python3..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv 2>/dev/null
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip 2>/dev/null
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python python-pip 2>/dev/null
    fi
fi
echo "  OK — $(python3 --version 2>&1)"

# 2. Instalar PyQt5
echo "  [2/4] Verificando interface grafica..."
if ! python3 -c "from PyQt5.QtWidgets import QApplication" 2>/dev/null; then
    echo "  Instalando PyQt5 (interface grafica)..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3-pyqt5 2>/dev/null || pip3 install pyqt5 2>/dev/null
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3-qt5 2>/dev/null || pip3 install pyqt5 2>/dev/null
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python-pyqt5 2>/dev/null || pip3 install pyqt5 2>/dev/null
    else
        pip3 install pyqt5 2>/dev/null
    fi
fi
echo "  OK"

# 3. Baixar arquivos do instalador e do programa
echo "  [3/4] Baixando arquivos..."
ARQUIVOS="installer_gui.py app_gui.py main.py main_cloud.py classifier.py config.py phone_controller.py audio_recorder.py audio_analyzer.py transcriber.py excel_handler.py cloud_handler.py updater.py scheduler.py version.json requirements.txt Icone_validador.png"

for f in $ARQUIVOS; do
    wget -q "$REPO/$f" -O "$TEMP_DIR/$f" 2>/dev/null || curl -sL "$REPO/$f" -o "$TEMP_DIR/$f" 2>/dev/null
done
echo "  OK — $(ls "$TEMP_DIR"/*.py 2>/dev/null | wc -l) arquivos"

# 4. Abrir instalador gráfico
echo "  [4/4] Abrindo instalador..."
echo ""
cd "$TEMP_DIR"
python3 installer_gui.py

# Limpar
rm -rf "$TEMP_DIR"
