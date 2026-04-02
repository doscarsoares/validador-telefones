"""
Analisador de áudio — detecta se há fala humana ou silêncio.
Usado para distinguir pessoa atendendo vs caixa postal (silêncio pós-bip).
"""

import os
import wave
import struct
import logging
import subprocess

logger = logging.getLogger(__name__)


def analisar_audio(caminho: str) -> dict:
    """
    Analisa um arquivo de áudio e retorna informações sobre seu conteúdo.

    Retorna:
        {
            'tem_fala': bool,       # True se detectou fala (volume significativo)
            'volume_medio': float,  # Volume RMS médio (0.0 a 1.0)
            'volume_pico': float,   # Volume de pico
            'duracao': float,       # Duração em segundos
            'percentual_silencio': float,  # % do áudio que é silêncio
        }
    """
    if not caminho or not os.path.exists(caminho):
        return {"tem_fala": False, "volume_medio": 0, "volume_pico": 0,
                "duracao": 0, "percentual_silencio": 100}

    try:
        # Converter para WAV se necessário (m4a → wav)
        wav_path = caminho
        if caminho.endswith(".m4a"):
            wav_path = caminho.replace(".m4a", "_temp.wav")
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", caminho, "-ar", "16000", "-ac", "1", wav_path],
                capture_output=True, timeout=15
            )
            if result.returncode != 0:
                logger.warning(f"Erro convertendo audio: {result.stderr[:200]}")
                return {"tem_fala": False, "volume_medio": 0, "volume_pico": 0,
                        "duracao": 0, "percentual_silencio": 100}

        # Ler WAV
        with wave.open(wav_path, "rb") as wf:
            n_frames = wf.getnframes()
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            raw_data = wf.readframes(n_frames)

        # Limpar temp
        if wav_path != caminho and os.path.exists(wav_path):
            os.remove(wav_path)

        duracao = n_frames / sample_rate

        if n_frames == 0:
            return {"tem_fala": False, "volume_medio": 0, "volume_pico": 0,
                    "duracao": 0, "percentual_silencio": 100}

        # Converter para amostras
        if sample_width == 2:
            fmt = f"<{n_frames * n_channels}h"
            samples = struct.unpack(fmt, raw_data)
        else:
            return {"tem_fala": False, "volume_medio": 0, "volume_pico": 0,
                    "duracao": duracao, "percentual_silencio": 100}

        # Se estéreo, pegar média dos canais
        if n_channels == 2:
            samples = [(samples[i] + samples[i + 1]) / 2 for i in range(0, len(samples), 2)]

        max_val = 32768.0

        # Calcular RMS por janelas de 0.1s
        window_size = int(sample_rate * 0.1)  # janela de 100ms
        if window_size == 0:
            window_size = len(samples)

        rms_values = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i:i + window_size]
            if len(chunk) == 0:
                continue
            rms = (sum(s ** 2 for s in chunk) / len(chunk)) ** 0.5 / max_val
            rms_values.append(rms)

        if not rms_values:
            return {"tem_fala": False, "volume_medio": 0, "volume_pico": 0,
                    "duracao": duracao, "percentual_silencio": 100}

        volume_medio = sum(rms_values) / len(rms_values)
        volume_pico = max(rms_values)

        # Threshold para considerar "silêncio": RMS < 0.01 (~-40dB)
        THRESHOLD_SILENCIO = 0.01
        janelas_silencio = sum(1 for r in rms_values if r < THRESHOLD_SILENCIO)
        percentual_silencio = janelas_silencio / len(rms_values) * 100

        # Threshold para "tem fala": pelo menos 20% do áudio com volume > threshold
        # E volume médio razoável
        THRESHOLD_FALA = 0.015
        janelas_com_fala = sum(1 for r in rms_values if r >= THRESHOLD_FALA)
        percentual_fala = janelas_com_fala / len(rms_values) * 100

        tem_fala = percentual_fala >= 8 and volume_medio >= 0.003

        logger.info(
            f"Audio: duracao={duracao:.1f}s, vol_medio={volume_medio:.4f}, "
            f"vol_pico={volume_pico:.4f}, silencio={percentual_silencio:.0f}%, "
            f"fala={percentual_fala:.0f}%, tem_fala={tem_fala}"
        )

        # Detectar padrão de bip de ocupado/chamando
        # Bips de ocupado: picos regulares (~5s intervalo), muito uniformes
        padrao_ocupado = _detectar_bip_ocupado(samples, sample_rate)

        return {
            "tem_fala": tem_fala,
            "volume_medio": round(volume_medio, 4),
            "volume_pico": round(volume_pico, 4),
            "duracao": round(duracao, 1),
            "percentual_silencio": round(percentual_silencio, 1),
            "padrao_ocupado": padrao_ocupado,
        }

    except Exception as e:
        logger.error(f"Erro analisando audio: {e}")
        return {"tem_fala": False, "volume_medio": 0, "volume_pico": 0,
                "duracao": 0, "percentual_silencio": 100, "padrao_ocupado": False}


def _detectar_bip_ocupado(samples, sample_rate) -> bool:
    """
    Detecta padrão de bip de ocupado: picos regulares com intervalo ~5s.
    Ocupado tem regularidade < 0.15 e intervalo médio > 4s.
    """
    # Janelas de 200ms
    window = int(sample_rate * 0.2)
    max_val = 32768.0
    THRESHOLD_BIP = 0.05

    rms_list = []
    for i in range(0, len(samples), window):
        chunk = samples[i:i + window]
        if len(chunk) < window // 2:
            continue
        rms = (sum(s ** 2 for s in chunk) / len(chunk)) ** 0.5 / max_val
        rms_list.append(rms)

    # Detectar bips (sequências de janelas acima do threshold)
    bips = []
    em_bip = False
    bip_inicio = None

    for i, rms in enumerate(rms_list):
        t = i * 0.2
        if rms >= THRESHOLD_BIP and not em_bip:
            em_bip = True
            bip_inicio = t
        elif rms < THRESHOLD_BIP and em_bip:
            em_bip = False
            bips.append(bip_inicio)

    if len(bips) < 3:
        return False

    # Calcular intervalos entre bips
    intervalos = [bips[i + 1] - bips[i] for i in range(len(bips) - 1)]
    media = sum(intervalos) / len(intervalos)
    desvio = (sum((x - media) ** 2 for x in intervalos) / len(intervalos)) ** 0.5

    if media == 0:
        return False

    regularidade = desvio / media

    # Ocupado: intervalo ~5s, muito regular (< 0.15)
    is_ocupado = regularidade < 0.20 and media > 4.0

    if is_ocupado:
        logger.info(
            f"Padrao OCUPADO detectado: {len(bips)} bips, "
            f"intervalo={media:.1f}s, regularidade={regularidade:.2f}"
        )

    return is_ocupado
