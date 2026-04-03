"""
Sistema de atualização automática via GitHub.
Verifica e baixa atualizações do repositório.
"""

import os
import json
import logging
import ssl
import urllib.request

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

logger = logging.getLogger(__name__)

# Repositório no GitHub
GITHUB_USER = "doscarsoares"
GITHUB_REPO = "validador-telefones"
GITHUB_BRANCH = "main"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"


def get_versao_local() -> dict:
    """Lê a versão local do version.json."""
    path = os.path.join(os.path.dirname(__file__), "version.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"versao": "0.0", "data": "", "arquivos": []}


def get_versao_remota() -> dict:
    """Baixa o version.json do GitHub para ver se há atualização."""
    url = f"{GITHUB_RAW}/version.json"
    try:
        req = urllib.request.Request(url)
        req.add_header("Cache-Control", "no-cache")
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Erro ao verificar atualizações: {e}")
        return None


def verificar_atualizacao() -> dict:
    """
    Verifica se há atualização disponível.
    Retorna dict com status:
      {"disponivel": True/False, "versao_local": "2.0", "versao_remota": "2.1", ...}
    """
    local = get_versao_local()
    remota = get_versao_remota()

    if remota is None:
        return {
            "disponivel": False,
            "erro": True,
            "mensagem": "Não foi possível verificar (sem internet?)",
        }

    disponivel = remota.get("versao", "0") != local.get("versao", "0")

    return {
        "disponivel": disponivel,
        "erro": False,
        "versao_local": local.get("versao", "?"),
        "versao_remota": remota.get("versao", "?"),
        "data_remota": remota.get("data", ""),
        "mensagem": remota.get("mensagem", ""),
        "url_padrao": remota.get("url_padrao", ""),
        "arquivos": remota.get("arquivos", []),
    }


def aplicar_atualizacao(callback=None) -> dict:
    """
    Baixa e substitui os arquivos atualizados do GitHub.
    callback(progresso, mensagem) é chamado para atualizar a interface.
    """
    install_dir = os.path.dirname(__file__)

    # Verificar versão remota
    remota = get_versao_remota()
    if remota is None:
        return {"sucesso": False, "mensagem": "Sem conexão com o servidor"}

    arquivos = remota.get("arquivos", [])
    total = len(arquivos)
    atualizados = 0
    erros = []

    for i, arquivo in enumerate(arquivos):
        if callback:
            callback(i / total, f"Baixando {arquivo}...")

        url = f"{GITHUB_RAW}/{arquivo}"
        destino = os.path.join(install_dir, arquivo)

        try:
            req = urllib.request.Request(url)
            req.add_header("Cache-Control", "no-cache")
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as resp:
                conteudo = resp.read()

            # Verificar se o conteúdo é diferente do local
            conteudo_local = b""
            if os.path.exists(destino):
                with open(destino, "rb") as f:
                    conteudo_local = f.read()

            if conteudo != conteudo_local:
                with open(destino, "wb") as f:
                    f.write(conteudo)
                atualizados += 1
                logger.info(f"Atualizado: {arquivo}")
            else:
                logger.debug(f"Sem mudança: {arquivo}")

        except Exception as e:
            erros.append(f"{arquivo}: {e}")
            logger.error(f"Erro baixando {arquivo}: {e}")

    if callback:
        callback(1.0, "Concluído!")

    return {
        "sucesso": len(erros) == 0,
        "atualizados": atualizados,
        "total": total,
        "erros": erros,
        "versao": remota.get("versao", "?"),
        "mensagem": remota.get("mensagem", ""),
        "url_padrao": remota.get("url_padrao", ""),
    }
