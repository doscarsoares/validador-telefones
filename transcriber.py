"""
Transcritor de áudio usando OpenAI Whisper.
Converte áudio gravado em texto para classificação.
"""

import logging
import os

from config import WHISPER_MODEL, WHISPER_LANGUAGE

logger = logging.getLogger(__name__)

# Variável global para cachear o modelo (carrega só uma vez)
_modelo = None


def carregar_modelo():
    """Carrega o modelo Whisper (só uma vez)."""
    global _modelo
    if _modelo is None:
        try:
            import whisper
        except ImportError:
            raise RuntimeError(
                "Whisper não instalado! Execute:\n"
                "  pip install openai-whisper\n"
                "Também precisa do ffmpeg:\n"
                "  Windows: choco install ffmpeg  OU  scoop install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg\n"
                "  Mac: brew install ffmpeg"
            )
        logger.info(f"Carregando modelo Whisper '{WHISPER_MODEL}'...")
        _modelo = whisper.load_model(WHISPER_MODEL)
        logger.info("Modelo Whisper carregado!")
    return _modelo


def transcrever(caminho_audio: str) -> str:
    """
    Transcreve um arquivo de áudio para texto.
    Retorna a transcrição em texto.
    """
    if not caminho_audio or not os.path.exists(caminho_audio):
        logger.warning(f"Arquivo de áudio não encontrado: {caminho_audio}")
        return ""

    # Verificar se o arquivo tem conteúdo
    if os.path.getsize(caminho_audio) < 1000:  # Menos de 1KB = provavelmente vazio
        logger.warning(f"Arquivo de áudio muito pequeno: {caminho_audio}")
        return ""

    modelo = carregar_modelo()

    try:
        logger.info(f"Transcrevendo: {caminho_audio}")
        resultado = modelo.transcribe(
            caminho_audio,
            language=WHISPER_LANGUAGE,
            fp16=False,  # Usar FP32 para compatibilidade com CPU
            initial_prompt="Ligação telefônica. Possíveis respostas: alô, oi, bom dia, boa tarde. Ou mensagem de operadora: o número chamado está desligado ou fora da área de cobertura. Grave seu recado após o sinal. Caixa postal. Correio de voz.",
        )
        texto = resultado["text"].strip()
        logger.info(f"Transcrição: '{texto}'")
        return texto

    except Exception as e:
        logger.error(f"Erro na transcrição: {e}")
        return ""


def transcrever_com_segmentos(caminho_audio: str) -> dict:
    """
    Transcreve com detalhes de segmentos (timestamps).
    Útil para análise mais detalhada.
    """
    if not caminho_audio or not os.path.exists(caminho_audio):
        return {"text": "", "segments": []}

    modelo = carregar_modelo()

    try:
        resultado = modelo.transcribe(
            caminho_audio,
            language=WHISPER_LANGUAGE,
            fp16=False,
        )
        return {
            "text": resultado["text"].strip(),
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in resultado.get("segments", [])
            ],
        }
    except Exception as e:
        logger.error(f"Erro na transcrição: {e}")
        return {"text": "", "segments": []}
