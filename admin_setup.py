#!/usr/bin/env python3
"""
Configuração de administração — rode apenas uma vez.
Define a senha e encripta a URL do Google Sheets.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from protection import (
    encrypt_string, decrypt_string, set_admin_password,
    save_protected_url, is_admin_configured, verify_admin_password,
    create_manifest
)


def main():
    print("\n  CONFIGURAÇÃO DE PROTEÇÃO\n")

    # 1. Senha
    if is_admin_configured():
        print("  Senha já configurada.")
        pwd = input("  Digite a senha atual: ")
        if not verify_admin_password(pwd):
            print("  Senha incorreta!")
            return
    else:
        print("  Definir senha de administração:")
        pwd = input("  Nova senha: ")
        pwd2 = input("  Confirmar: ")
        if pwd != pwd2:
            print("  Senhas não coincidem!")
            return
        set_admin_password(pwd)
        print("  Senha definida!")

    # 2. URL
    print()
    url = input("  URL do Google Sheets: ").strip()
    if url:
        encrypted = encrypt_string(url)
        print(f"\n  URL encriptada: {encrypted[:50]}...")
        save_protected_url(url, pwd)
        print("  URL salva com proteção!")

        # Verificar
        from protection import get_protected_url
        decrypted = get_protected_url()
        assert decrypted == url, "Erro na encriptação!"
        print("  Verificação OK!")

    # 3. Manifest
    print()
    install_dir = input("  Pasta de instalação (ou Enter para atual): ").strip()
    if not install_dir:
        install_dir = os.path.dirname(__file__)
    create_manifest(install_dir)
    print(f"  Manifest de integridade criado!")

    print("\n  Proteção configurada com sucesso!\n")


if __name__ == "__main__":
    main()
