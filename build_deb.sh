#!/bin/bash
# ================================================================
#  Build .deb do Validador de Telefones — roda no macOS
#  Gera pacote .deb para Ubuntu/Debian/Mint
# ================================================================
set -e

APP="validador-telefones"
VERSION="1.0"
ARCH="all"
PKG="${APP}_${VERSION}_${ARCH}"
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$SRC/dist"

echo "Construindo ${PKG}.deb..."

# Limpar
rm -rf "/tmp/$PKG" "$OUT/${PKG}.deb"
mkdir -p "$OUT"

# ── Estrutura do .deb ────────────────────────────────────────
mkdir -p "/tmp/$PKG/DEBIAN"
mkdir -p "/tmp/$PKG/opt/ValidadorTelefones/audios"
mkdir -p "/tmp/$PKG/opt/ValidadorTelefones/resultados"
mkdir -p "/tmp/$PKG/opt/ValidadorTelefones/planilhas"
mkdir -p "/tmp/$PKG/usr/share/applications"
mkdir -p "/tmp/$PKG/usr/share/icons/hicolor/256x256/apps"
mkdir -p "/tmp/$PKG/usr/share/icons/hicolor/128x128/apps"
mkdir -p "/tmp/$PKG/usr/share/icons/hicolor/64x64/apps"
mkdir -p "/tmp/$PKG/usr/share/icons/hicolor/48x48/apps"
mkdir -p "/tmp/$PKG/usr/share/icons/hicolor/32x32/apps"
mkdir -p "/tmp/$PKG/usr/share/metainfo"
mkdir -p "/tmp/$PKG/usr/local/bin"

# ── Copiar arquivos do programa ──────────────────────────────
for f in app_gui.py main.py main_cloud.py classifier.py config.py \
         phone_controller.py audio_recorder.py audio_analyzer.py \
         transcriber.py excel_handler.py cloud_handler.py \
         updater.py scheduler.py protection.py \
         version.json requirements.txt; do
    [ -f "$SRC/$f" ] && cp "$SRC/$f" "/tmp/$PKG/opt/ValidadorTelefones/"
done

# Ícone
cp "$SRC/Icone_validador.png" "/tmp/$PKG/opt/ValidadorTelefones/"

# ── Ícones em vários tamanhos ────────────────────────────────
sips -z 256 256 "$SRC/Icone_validador.png" --out "/tmp/$PKG/usr/share/icons/hicolor/256x256/apps/validador-telefones.png" &>/dev/null
sips -z 128 128 "$SRC/Icone_validador.png" --out "/tmp/$PKG/usr/share/icons/hicolor/128x128/apps/validador-telefones.png" &>/dev/null
sips -z 64 64 "$SRC/Icone_validador.png" --out "/tmp/$PKG/usr/share/icons/hicolor/64x64/apps/validador-telefones.png" &>/dev/null
sips -z 48 48 "$SRC/Icone_validador.png" --out "/tmp/$PKG/usr/share/icons/hicolor/48x48/apps/validador-telefones.png" &>/dev/null
sips -z 32 32 "$SRC/Icone_validador.png" --out "/tmp/$PKG/usr/share/icons/hicolor/32x32/apps/validador-telefones.png" &>/dev/null

# ── AppStream metainfo ───────────────────────────────────────
cat > "/tmp/$PKG/usr/share/metainfo/validador-telefones.appdata.xml" << 'APPDATA'
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.validador.telefones</id>
  <name>Validador de Telefones</name>
  <summary>Validar numeros de telefone via ligacao automatica</summary>
  <description>
    <p>Sistema de validacao automatica de telefones via celular Android (ADB).
    Classifica chamadas com inteligencia artificial (Whisper).
    Integrado com Google Sheets para gerenciamento na nuvem.</p>
  </description>
  <icon type="stock">validador-telefones</icon>
  <categories>
    <category>Utility</category>
    <category>Office</category>
  </categories>
</component>
APPDATA

# ── Arquivo .desktop ─────────────────────────────────────────
cat > "/tmp/$PKG/usr/share/applications/validador-telefones.desktop" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=Validador de Telefones
Comment=Validar numeros de telefone via ligacao automatica
Exec=/opt/ValidadorTelefones/executar.sh
Icon=validador-telefones
Terminal=false
Categories=Utility;Office;
StartupNotify=true
StartupWMClass=validador-telefones
DESKTOP

# ── Script executar.sh (launcher) ────────────────────────────
cat > "/tmp/$PKG/opt/ValidadorTelefones/executar.sh" << 'LAUNCHER'
#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:$PATH"
DIR="/opt/ValidadorTelefones"
cd "$DIR"
"$DIR/venv/bin/python3" app_gui.py &
LAUNCHER
chmod 755 "/tmp/$PKG/opt/ValidadorTelefones/executar.sh"

# ── Link no PATH ─────────────────────────────────────────────
cat > "/tmp/$PKG/usr/local/bin/validador-telefones" << 'BINLINK'
#!/bin/bash
exec /opt/ValidadorTelefones/executar.sh "$@"
BINLINK
chmod 755 "/tmp/$PKG/usr/local/bin/validador-telefones"

# ── DEBIAN/control ───────────────────────────────────────────
cat > "/tmp/$PKG/DEBIAN/control" << CTRL
Package: validador-telefones
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: 5000
Maintainer: Validador Telefones <contato@validador.com>
Description: Validador de Telefones v1.0 Beelza
 Sistema de validacao automatica de telefones via celular Android (ADB).
 Classifica chamadas com inteligencia artificial (Whisper).
 Integrado com Google Sheets para gerenciamento na nuvem.
CTRL

# ── DEBIAN/postinst (pós-instalação) ─────────────────────────
cat > "/tmp/$PKG/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

APP_DIR="/opt/ValidadorTelefones"
VENV_DIR="$APP_DIR/venv"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Validador de Telefones — Configurando...      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Dependências do sistema
echo "[1/6] Instalando dependencias do sistema..."
apt-get update -qq 2>/dev/null
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-tk \
    adb ffmpeg portaudio19-dev libportaudio2 \
    build-essential 2>/dev/null || true

# udev rules for ADB (Android devices)
UDEV_RULES="/etc/udev/rules.d/51-android.rules"
if [ ! -f "$UDEV_RULES" ]; then
    cat > "$UDEV_RULES" << 'UDEV'
# Samsung
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
# Motorola
SUBSYSTEM=="usb", ATTR{idVendor}=="22b8", MODE="0666", GROUP="plugdev"
# Xiaomi
SUBSYSTEM=="usb", ATTR{idVendor}=="2717", MODE="0666", GROUP="plugdev"
# Google
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="plugdev"
# OnePlus
SUBSYSTEM=="usb", ATTR{idVendor}=="2a70", MODE="0666", GROUP="plugdev"
# LG
SUBSYSTEM=="usb", ATTR{idVendor}=="1004", MODE="0666", GROUP="plugdev"
# Huawei
SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", MODE="0666", GROUP="plugdev"
# ASUS
SUBSYSTEM=="usb", ATTR{idVendor}=="0b05", MODE="0666", GROUP="plugdev"
# Sony
SUBSYSTEM=="usb", ATTR{idVendor}=="0fce", MODE="0666", GROUP="plugdev"
# Generic Android (fastboot/adb)
SUBSYSTEM=="usb", ATTR{idVendor}=="1d6b", MODE="0666", GROUP="plugdev"
UDEV
    chmod 644 "$UDEV_RULES"
fi
# Add all human users to plugdev group
for home_dir in /home/*; do
    uname="$(basename "$home_dir")"
    if id "$uname" &>/dev/null; then
        usermod -aG plugdev "$uname" 2>/dev/null || true
    fi
done
# Reload udev rules
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

# 2. Encontrar Python 3.11+
echo "[2/6] Verificando Python..."
PYTHON_CMD=""
for pv in python3.12 python3.11 python3; do
    if command -v "$pv" &>/dev/null; then
        VER=$("$pv" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_CMD="$pv"
            echo "  Usando $pv ($VER)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  Python 3.10+ nao encontrado, tentando instalar..."
    apt-get install -y python3.11 python3.11-venv 2>/dev/null || \
    apt-get install -y python3 python3-venv 2>/dev/null
    PYTHON_CMD="python3"
fi

# Install versioned python3-tk matching the selected Python version
PY_VER=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
apt-get install -y "python${PY_VER}-tk" 2>/dev/null || true

# 3. Criar venv (só se não existir)
echo "[3/6] Configurando ambiente Python..."
if [ ! -f "$VENV_DIR/bin/python3" ]; then
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

# 4. Instalar pacotes pip (só os que faltam)
echo "[4/6] Verificando pacotes..."
PIP="$VENV_DIR/bin/pip"
"$PIP" install --upgrade pip -q 2>/dev/null

for pkg in customtkinter openpyxl certifi Pillow; do
    "$PIP" show "$pkg" &>/dev/null || "$PIP" install "$pkg" -q 2>/dev/null
done

# PyAudio (pode falhar)
"$PIP" show pyaudio &>/dev/null || "$PIP" install pyaudio -q 2>/dev/null || true

# Whisper (pesado — só se não tiver)
if ! "$PIP" show openai-whisper &>/dev/null; then
    echo "[5/6] Instalando Whisper (pode demorar)..."
    "$PIP" install numba --prefer-binary -q 2>/dev/null
    "$PIP" install openai-whisper -q 2>/dev/null
else
    echo "[5/6] Whisper ja instalado."
fi

# 5. Modelo Whisper (só se não tiver)
echo "[6/6] Verificando modelo de voz..."
WHISPER_CACHE="$APP_DIR/.whisper_cache"
mkdir -p "$WHISPER_CACHE"
MODEL_FOUND=0
if [ -f "$WHISPER_CACHE/small.pt" ]; then
    echo "  Modelo ja baixado."
    MODEL_FOUND=1
fi
if [ "$MODEL_FOUND" -eq 0 ]; then
    # Checar nas homes dos usuarios
    for home_dir in /home/*; do
        if [ -f "$home_dir/.cache/whisper/small.pt" ]; then
            echo "  Modelo encontrado em $home_dir"
            cp "$home_dir/.cache/whisper/small.pt" "$WHISPER_CACHE/" 2>/dev/null
            MODEL_FOUND=1
            break
        fi
    done
fi
if [ "$MODEL_FOUND" -eq 0 ]; then
    echo "  Baixando modelo (460MB)..."
    "$VENV_DIR/bin/python3" -c \
        "import whisper; whisper.load_model('small', download_root='$WHISPER_CACHE')" \
        2>/dev/null || true
fi
chmod -R 777 "$WHISPER_CACHE" 2>/dev/null || true

# 6. Permissões
chmod -R 777 "$APP_DIR"
chmod 755 "$APP_DIR/executar.sh"

# Criar pastas de dados com permissão de escrita pra todos
chmod 777 "$APP_DIR/audios" "$APP_DIR/resultados" "$APP_DIR/planilhas" 2>/dev/null

# Atualizar desktop database
command -v update-desktop-database &>/dev/null && update-desktop-database /usr/share/applications/ 2>/dev/null || true
command -v gtk-update-icon-cache &>/dev/null && gtk-update-icon-cache -f /usr/share/icons/hicolor/ 2>/dev/null || true

# Fonte Montserrat
for home_dir in /home/*; do
    FONT_DIR="$home_dir/.local/share/fonts"
    if [ ! -f "$FONT_DIR/Montserrat-Regular.ttf" ]; then
        mkdir -p "$FONT_DIR"
        wget -q "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf" \
            -O "$FONT_DIR/Montserrat-Regular.ttf" 2>/dev/null || true
        chown -R "$(basename "$home_dir"):$(basename "$home_dir")" "$FONT_DIR" 2>/dev/null || true
    fi
done
fc-cache -f 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Instalacao concluida!                          ║"
echo "║   Abra pelo menu de aplicativos ou digite:       ║"
echo "║   validador-telefones                            ║"
echo "║                                                  ║"
echo "║   IMPORTANTE: desconecte e reconecte o celular   ║"
echo "║   para que as regras ADB entrem em vigor.        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
POSTINST
chmod 755 "/tmp/$PKG/DEBIAN/postinst"

# ── DEBIAN/prerm (antes de desinstalar) ──────────────────────
cat > "/tmp/$PKG/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
# Matar o programa se estiver rodando
pkill -f "app_gui.py" 2>/dev/null || true
sleep 1
PRERM
chmod 755 "/tmp/$PKG/DEBIAN/prerm"

# ── DEBIAN/postrm (depois de desinstalar) ────────────────────
cat > "/tmp/$PKG/DEBIAN/postrm" << 'POSTRM'
#!/bin/bash
if [ "$1" = "purge" ]; then
    rm -rf /opt/ValidadorTelefones
fi
# Atualizar menus
command -v update-desktop-database &>/dev/null && update-desktop-database /usr/share/applications/ 2>/dev/null || true
command -v gtk-update-icon-cache &>/dev/null && gtk-update-icon-cache -f /usr/share/icons/hicolor/ 2>/dev/null || true
POSTRM
chmod 755 "/tmp/$PKG/DEBIAN/postrm"

# ── Permissões corretas ──────────────────────────────────────
find "/tmp/$PKG" -type d -exec chmod 755 {} \;
find "/tmp/$PKG/opt" -type f -exec chmod 644 {} \;
chmod 755 "/tmp/$PKG/opt/ValidadorTelefones/executar.sh"
chmod 755 "/tmp/$PKG/usr/local/bin/validador-telefones"
chmod 755 "/tmp/$PKG/DEBIAN/postinst"
chmod 755 "/tmp/$PKG/DEBIAN/prerm"
chmod 755 "/tmp/$PKG/DEBIAN/postrm"

# ── Build ────────────────────────────────────────────────────
dpkg-deb --root-owner-group --build "/tmp/$PKG" "$OUT/${PKG}.deb"

# Limpar
rm -rf "/tmp/$PKG"

echo ""
echo "Criado: $OUT/${PKG}.deb"
echo "Tamanho: $(du -h "$OUT/${PKG}.deb" | cut -f1)"
echo ""
echo "Instalar no Linux com:"
echo "  sudo dpkg -i ${PKG}.deb"
echo "  sudo apt-get install -f"
