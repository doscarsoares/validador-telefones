"""
Classificador de chamadas.

LÓGICA SIMPLES:
  Só é PESSOA ATENDEU se tiver evidência POSITIVA de pessoa:
  - Transcrição com padrão de pessoa ("alô", "oi", "bom dia", etc.)
  - Fala detectada + texto sem padrão de operadora + texto faz sentido

  Todo o resto = NÃO ATENDEU (com detalhe do motivo: caixa postal,
  desligado, fora de área, inexistente, etc.)
"""

import re
import logging
from config import PADROES_CLASSIFICACAO, RESULTADO_PADRAO

logger = logging.getLogger(__name__)

NOMES_RESULTADO = {
    "PESSOA_ATENDEU": "✅ Pessoa Atendeu",
    "SILENCIO_INCERTO": "❓ Silêncio Incerto",
    "CAIXA_POSTAL": "📫 Caixa Postal",
    "FORA_DE_AREA": "📵 Fora de Área",
    "NUMERO_INEXISTENTE": "❌ Número Inexistente",
    "BLOQUEADO": "🚫 Bloqueado",
    "OCUPADO": "📞 Ocupado",
    "NAO_ATENDEU": "⏰ Não Atendeu",
    "ERRO": "⚠️ Erro na Ligação",
}


def classificar(transcricao: str, monitor: dict, call_log: dict, audio_info: dict = None) -> dict:
    """
    Classifica a chamada.
    Pergunta central: TEM EVIDÊNCIA DE PESSOA? Se não → não atendeu.
    """
    atendeu = monitor.get("atendeu", False)
    desligou_rapido = monitor.get("desligou_rapido", False)
    duracao_offhook = monitor.get("duracao_offhook", 0)
    texto = transcricao.lower().strip() if transcricao else ""

    tem_fala = False
    if audio_info:
        tem_fala = audio_info.get("tem_fala", False)
    elif texto and len(texto) > 3:
        tem_fala = True

    # =====================================================
    # PASSO 1: Se tem transcrição, checar padrões conhecidos
    # (tanto de operadora quanto de pessoa)
    # =====================================================
    if texto:
        resultado_texto = _classificar_por_texto(texto)
        if resultado_texto:
            if atendeu:
                resultado_texto["confianca"] = min(0.98, resultado_texto["confianca"] + 0.10)

            # Caixa postal com DIALING curto (<15s) = número bloqueado/inválido
            # Caixa postal real toca pelo menos 20s antes de cair
            if resultado_texto["codigo"] == "CAIXA_POSTAL":
                duracao_dialing = monitor.get("tempo_ate_atender") or duracao_offhook
                if duracao_dialing < 15:
                    return _resultado("BLOQUEADO", 0.92,
                                      f"(caixa postal direta sem toques: DIALING {duracao_dialing:.0f}s)", transcricao)

            return resultado_texto

    # =====================================================
    # PASSO 2: Desligou rápido → inexistente
    # =====================================================
    if desligou_rapido:
        return _resultado("NUMERO_INEXISTENTE", 0.92,
                          f"(desligou rapido: {duracao_offhook}s)", transcricao)

    # =====================================================
    # PASSO 3: ACTIVE + tem fala + texto SEM padrão de operadora
    # Única forma de ser PESSOA: precisa de ACTIVE + fala real
    # E o texto não pode ser lixo do Whisper (operadora incompreensível)
    # =====================================================
    if atendeu and tem_fala:
        # ACTIVE + fala + nenhum padrão de operadora bateu (passo 1 já checou)
        # Se o Whisper não reconheceu como operadora, assumir PESSOA.
        # É mais seguro: falso positivo de pessoa → vai pra aba "Atendeu"
        # e o usuário confere. Falso negativo (perder pessoa real) é pior.
        if texto:
            return _resultado("PESSOA_ATENDEU", 0.75,
                              f"(ACTIVE + fala sem padrao operadora: '{texto[:50]}')", transcricao)
        else:
            return _resultado("PESSOA_ATENDEU", 0.65,
                              "(ACTIVE + fala sem transcrição)", transcricao)

    # =====================================================
    # PASSO 5: ACTIVE + silêncio total = INCERTO
    # Pode ser pessoa calada OU número inválido (1 bip e nada)
    # Mandar pra "Tentar Novamente" — se 3x seguidas der silêncio,
    # é inválido e será descartado.
    # =====================================================
    if atendeu and not tem_fala:
        return _resultado("SILENCIO_INCERTO", 0.50,
                          "(ACTIVE + silencio total — tentar novamente)", transcricao)

    # =====================================================
    # PASSO 6: Nunca ACTIVE → não atendeu
    # =====================================================
    if duracao_offhook >= 5 and not atendeu:
        return _resultado("NAO_ATENDEU", 0.92,
                          f"(tocou {duracao_offhook}s sem atender)", transcricao)

    # =====================================================
    # FALLBACK
    # =====================================================
    return _resultado("NAO_ATENDEU", 0.50,
                      f"(incerto: offhook={duracao_offhook}s, atendeu={atendeu})", transcricao)


def _classificar_por_texto(texto: str) -> dict | None:
    """Classifica baseado nos padrões de texto da transcrição."""
    if not texto:
        return None

    ordem = [
        "NUMERO_INEXISTENTE",
        "FORA_DE_AREA",
        "BLOQUEADO",
        "CAIXA_POSTAL",
        "OCUPADO",
        "PESSOA_ATENDEU",
    ]

    # Padrões curtos (<=4 chars) precisam de match por palavra inteira
    # para evitar "oi" dentro de "coisa", "sim" dentro de "simples", etc.
    TAMANHO_PALAVRA_INTEIRA = 4

    for categoria in ordem:
        padroes = PADROES_CLASSIFICACAO.get(categoria, [])
        for padrao in padroes:
            if len(padrao) <= TAMANHO_PALAVRA_INTEIRA:
                # Match por palavra inteira
                if re.search(r'\b' + re.escape(padrao) + r'\b', texto):
                    confianca = min(0.95, 0.75 + len(padrao) / 40)
                    return _resultado(categoria, confianca, padrao, texto)
            else:
                if padrao in texto:
                    confianca = min(0.95, 0.75 + len(padrao) / 40)
                    return _resultado(categoria, confianca, padrao, texto)

    return None


def _resultado(codigo: str, confianca: float, padrao: str, transcricao: str) -> dict:
    resultado = {
        "codigo": codigo,
        "descricao": NOMES_RESULTADO.get(codigo, codigo),
        "confianca": round(confianca, 2),
        "padrao_encontrado": padrao,
        "transcricao": transcricao or "",
    }
    logger.info(
        f"Classificacao: {resultado['descricao']} "
        f"(confianca: {resultado['confianca']}) "
        f"[padrao: {padrao}]"
    )
    return resultado
