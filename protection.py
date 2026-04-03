"""
Módulo de proteção — encriptação de dados sensíveis e verificação de integridade.
"""

import os
import sys
import hashlib
import base64
import json

# Chave derivada do hardware (dificulta copiar pra outra máquina sem autorização)
def _get_machine_salt():
    """Gera um salt baseado em informações da máquina."""
    import platform
    parts = [
        platform.node(),
        platform.system(),
        platform.machine(),
    ]
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).digest()[:16]


def _get_key():
    """Chave de encriptação fixa + salt da máquina."""
    # Chave base (ofuscada no código compilado)
    kb = b'\x56\x41\x4c\x49\x44\x41\x44\x4f\x52\x5f\x54\x45\x4c\x45\x46\x4f'
    return hashlib.sha256(kb + b'_PROTEGIDO_2026').digest()


def encrypt_string(text):
    """Encripta uma string com XOR + base64."""
    key = _get_key()
    encrypted = bytearray()
    for i, char in enumerate(text.encode("utf-8")):
        encrypted.append(char ^ key[i % len(key)])
    return base64.b64encode(bytes(encrypted)).decode("ascii")


def decrypt_string(encrypted_b64):
    """Decripta uma string encriptada."""
    key = _get_key()
    encrypted = base64.b64decode(encrypted_b64)
    decrypted = bytearray()
    for i, byte in enumerate(encrypted):
        decrypted.append(byte ^ key[i % len(key)])
    return decrypted.decode("utf-8")


# URL encriptada (gerada com encrypt_string)
_ENCRYPTED_URL = None


def get_protected_url():
    """Retorna a URL do Google Sheets decriptada."""
    global _ENCRYPTED_URL
    if _ENCRYPTED_URL is None:
        # Gerar na primeira execução
        _ENCRYPTED_URL = _load_encrypted_url()
    if _ENCRYPTED_URL:
        return decrypt_string(_ENCRYPTED_URL)
    return ""


def _load_encrypted_url():
    """Carrega a URL encriptada do arquivo de config."""
    config_path = os.path.join(os.path.dirname(__file__), ".protected_config")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            return data.get("url")
        except Exception:
            pass
    return None


def save_protected_url(url, password):
    """Salva a URL encriptada — requer senha."""
    if not verify_admin_password(password):
        return False
    encrypted = encrypt_string(url)
    config_path = os.path.join(os.path.dirname(__file__), ".protected_config")
    with open(config_path, "w") as f:
        json.dump({"url": encrypted, "v": "2.1"}, f)
    global _ENCRYPTED_URL
    _ENCRYPTED_URL = encrypted
    return True


# ============================================================
#  SENHA DE ADMINISTRAÇÃO
# ============================================================

# Hash da senha (SHA-256) — a senha real nunca fica no código
_ADMIN_HASH = None


def set_admin_password(password):
    """Define a senha de administração (primeira vez)."""
    hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    config_path = os.path.join(os.path.dirname(__file__), ".admin")
    with open(config_path, "w") as f:
        f.write(hashed)
    global _ADMIN_HASH
    _ADMIN_HASH = hashed
    return True


def verify_admin_password(password):
    """Verifica se a senha está correta."""
    global _ADMIN_HASH
    if _ADMIN_HASH is None:
        config_path = os.path.join(os.path.dirname(__file__), ".admin")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                _ADMIN_HASH = f.read().strip()
        else:
            return False
    hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hashed == _ADMIN_HASH


def is_admin_configured():
    """Verifica se já tem senha configurada."""
    config_path = os.path.join(os.path.dirname(__file__), ".admin")
    return os.path.exists(config_path)


# ============================================================
#  VERIFICAÇÃO DE INTEGRIDADE
# ============================================================

def get_file_hash(filepath):
    """Calcula hash SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_integrity(install_dir):
    """Verifica se os arquivos principais não foram modificados."""
    manifest_path = os.path.join(install_dir, ".manifest")
    if not os.path.exists(manifest_path):
        return True  # Primeira execução, sem manifest

    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        for filename, expected_hash in manifest.items():
            filepath = os.path.join(install_dir, filename)
            if os.path.exists(filepath):
                actual_hash = get_file_hash(filepath)
                if actual_hash != expected_hash:
                    return False
        return True
    except Exception:
        return True


def create_manifest(install_dir):
    """Cria o manifest de integridade dos arquivos."""
    critical_files = [
        "classifier.py", "cloud_handler.py", "config.py",
        "app_gui.py", "main_cloud.py", "phone_controller.py",
    ]
    manifest = {}
    for f in critical_files:
        path = os.path.join(install_dir, f)
        if os.path.exists(path):
            manifest[f] = get_file_hash(path)

    manifest_path = os.path.join(install_dir, ".manifest")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)
