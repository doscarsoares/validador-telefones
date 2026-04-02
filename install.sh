#!/bin/bash
# Instalador rápido — baixa do GitHub e instala
set -e

echo ""
echo "  VALIDADOR DE TELEFONES — Instalando..."
echo ""

INSTALL_DIR="$HOME/ValidadorTelefones"
REPO="https://raw.githubusercontent.com/doscarsoares/validador-telefones/main"

mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/audios" "$INSTALL_DIR/resultados" "$INSTALL_DIR/planilhas"

echo "  [1/7] Baixando arquivos..."
for f in app_gui.py main.py main_cloud.py classifier.py config.py phone_controller.py audio_recorder.py audio_analyzer.py transcriber.py excel_handler.py cloud_handler.py updater.py scheduler.py version.json requirements.txt; do
    wget -q "$REPO/$f" -O "$INSTALL_DIR/$f" 2>/dev/null || curl -sL "$REPO/$f" -o "$INSTALL_DIR/$f"
done
# Ícone
wget -q "$REPO/Icone_validador.png" -O "$INSTALL_DIR/Icone_validador.png" 2>/dev/null || curl -sL "$REPO/Icone_validador.png" -o "$INSTALL_DIR/Icone_validador.png"
echo "  OK"

echo "  [2/7] Instalando dependencias do sistema..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-venv python3-pip python3-tk adb ffmpeg portaudio19-dev 2>/dev/null
elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3 python3-tkinter android-tools ffmpeg portaudio-devel 2>/dev/null
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm python python-pip tk android-tools ffmpeg portaudio 2>/dev/null
fi
echo "  OK"

echo "  [3/7] Criando ambiente Python..."
if [ ! -f "$INSTALL_DIR/venv/bin/activate" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip -q
echo "  OK"

echo "  [4/7] Instalando bibliotecas..."
pip install customtkinter openpyxl certifi Pillow -q
pip install pyaudio -q 2>/dev/null || true
echo "  OK"

echo "  [5/7] Instalando Whisper..."
pip install "numba>=0.59" --prefer-binary -q 2>/dev/null
pip install openai-whisper -q
echo "  OK"

echo "  [6/7] Baixando modelo de voz (~460MB)..."
python3 -c "import whisper; whisper.load_model('small')" 2>/dev/null
echo "  OK"

echo "  [7/7] Criando atalhos..."

# Script de execução
cat > "$INSTALL_DIR/executar.sh" << 'EOF'
#!/bin/bash
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc" 2>/dev/null
[ -f "$HOME/.profile" ] && source "$HOME/.profile" 2>/dev/null
export PATH="$PATH:/usr/local/bin:/usr/bin"
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/venv/bin/activate"
cd "$DIR"
python3 app_gui.py
deactivate 2>/dev/null
EOF
chmod +x "$INSTALL_DIR/executar.sh"

# Ícone no desktop
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
[ -d "$HOME/Área de Trabalho" ] && DESKTOP_DIR="$HOME/Área de Trabalho"

cat > "$DESKTOP_DIR/ValidadorTelefones.desktop" << DEOF
[Desktop Entry]
Name=Validador de Telefones
Comment=Validar numeros de telefone
Exec=bash "$INSTALL_DIR/executar.sh"
Icon=$INSTALL_DIR/Icone_validador.png
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
DEOF
chmod +x "$DESKTOP_DIR/ValidadorTelefones.desktop"
command -v gio &>/dev/null && gio set "$DESKTOP_DIR/ValidadorTelefones.desktop" metadata::trusted true 2>/dev/null

# Fonte Montserrat
mkdir -p "$HOME/.local/share/fonts"
wget -q "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf" -O "$HOME/.local/share/fonts/Montserrat-Regular.ttf" 2>/dev/null || true
fc-cache -f "$HOME/.local/share/fonts" 2>/dev/null

deactivate 2>/dev/null

echo ""
echo "  INSTALACAO CONCLUIDA!"
echo "  Pasta: $INSTALL_DIR"
echo "  Clique no icone na area de trabalho."
echo ""

read -p "  Abrir agora? (s/n) [s]: " resp
if [ "$resp" != "n" ] && [ "$resp" != "N" ]; then
    bash "$INSTALL_DIR/executar.sh" &
fi
