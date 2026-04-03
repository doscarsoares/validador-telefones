"""
Agendador automático semanal.
Liga automaticamente no horário comercial e para fora dele.

Horários (fuso Manaus, UTC-4):
  Seg-Sex: 08:00 - 18:00
  Sáb-Dom: 09:00 - 18:00
"""

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Fuso horário de Manaus (UTC-4)
FUSO_MANAUS = timezone(timedelta(hours=-4))

# Horários
HORARIOS = {
    # dia_da_semana: (hora_inicio, hora_fim)
    0: (8, 18),   # Segunda
    1: (8, 18),   # Terça
    2: (8, 18),   # Quarta
    3: (8, 18),   # Quinta
    4: (8, 18),   # Sexta
    5: (9, 18),   # Sábado
    6: (9, 18),   # Domingo
}


def agora_manaus() -> datetime:
    """Retorna a hora atual em Manaus."""
    return datetime.now(FUSO_MANAUS)


def esta_no_horario() -> bool:
    """Verifica se o horário atual está dentro do período permitido."""
    now = agora_manaus()
    dia = now.weekday()  # 0=Seg, 6=Dom
    hora = now.hour

    inicio, fim = HORARIOS[dia]
    return inicio <= hora < fim


def proximo_inicio() -> str:
    """Retorna quando será o próximo horário de início (texto legível)."""
    now = agora_manaus()
    dia = now.weekday()
    hora = now.hour

    inicio, fim = HORARIOS[dia]

    if hora < inicio:
        # Ainda hoje, falta começar
        minutos = (inicio - hora) * 60 - now.minute
        if minutos <= 60:
            return f"em {minutos} minutos"
        return f"hoje às {inicio}:00"
    elif hora >= fim:
        # Já passou, próximo dia
        prox_dia = (dia + 1) % 7
        prox_inicio = HORARIOS[prox_dia][0]
        nomes_dia = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
        return f"{nomes_dia[prox_dia]} às {prox_inicio}:00"
    else:
        # Está no horário agora
        return "agora"


def tempo_ate_parar() -> str:
    """Retorna quanto tempo falta até parar (texto legível)."""
    now = agora_manaus()
    dia = now.weekday()
    hora = now.hour

    _, fim = HORARIOS[dia]
    minutos = (fim - hora) * 60 - now.minute

    if minutos <= 0:
        return "agora"
    elif minutos <= 60:
        return f"em {minutos} min"
    else:
        horas = minutos // 60
        mins = minutos % 60
        return f"em {horas}h{mins:02d}"


def status_horario() -> dict:
    """Retorna status completo do horário."""
    now = agora_manaus()
    dia = now.weekday()
    inicio, fim = HORARIOS[dia]
    no_horario = esta_no_horario()

    nomes_dia = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]

    return {
        "no_horario": no_horario,
        "hora_atual": now.strftime("%H:%M"),
        "dia": nomes_dia[dia],
        "inicio": f"{inicio}:00",
        "fim": f"{fim}:00",
        "proximo_inicio": proximo_inicio(),
        "tempo_ate_parar": tempo_ate_parar() if no_horario else None,
    }
