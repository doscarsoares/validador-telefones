#!/bin/bash
# Script de build do instalador Mac
cd "$(dirname "$0")"
source venv/bin/activate

rm -rf dist build *.spec

pyinstaller \
    --onedir --windowed \
    --name "SETUP_ValidadorTelefones" \
    --icon "Icone_validador.icns" \
    --add-data "app_gui.py:." --add-data "main.py:." --add-data "main_cloud.py:." \
    --add-data "classifier.py:." --add-data "config.py:." --add-data "phone_controller.py:." \
    --add-data "audio_recorder.py:." --add-data "audio_analyzer.py:." --add-data "transcriber.py:." \
    --add-data "excel_handler.py:." --add-data "cloud_handler.py:." --add-data "updater.py:." \
    --add-data "scheduler.py:." --add-data "protection.py:." \
    --add-data "version.json:." --add-data "requirements.txt:." \
    --add-data "Icone_validador.png:." --add-data "Icone_validador.icns:." --add-data "LEIA-ME.html:." \
    --osx-bundle-identifier "com.validador.telefones.setup" \
    installer_gui.py

# Limpar lixo (sem codesign — ele quebra o ícone)
xattr -cr dist/SETUP_ValidadorTelefones.app 2>/dev/null
find dist/SETUP_ValidadorTelefones.app -name "._*" -delete 2>/dev/null
find dist/SETUP_ValidadorTelefones.app -name ".DS_Store" -delete 2>/dev/null

# Garantir ícone correto
cp Icone_validador.icns dist/SETUP_ValidadorTelefones.app/Contents/Resources/

# Limpar cache de ícones do Mac
sudo rm -rf /Library/Caches/com.apple.iconservices.store 2>/dev/null
sudo find /private/var/folders -name "com.apple.iconservices" -exec rm -rf {} + 2>/dev/null
sudo find /private/var/folders -name "com.apple.dock.iconcache" -exec rm -rf {} + 2>/dev/null

# Copiar pro Downloads
rm -rf ~/Documents/Downloads/SETUP_ValidadorTelefones.app
cp -r dist/SETUP_ValidadorTelefones.app ~/Documents/Downloads/
touch ~/Documents/Downloads/SETUP_ValidadorTelefones.app

# Reiniciar Dock e Finder pra pegar ícone novo
killall Dock 2>/dev/null
killall Finder 2>/dev/null

echo "Build concluído!"
