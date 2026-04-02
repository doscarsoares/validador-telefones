#!/usr/bin/env python3
"""
=================================================================
  VALIDADOR DE TELEFONES v2.0 — Remoto via BCR + ADB
=================================================================

Disca para uma lista de números via celular Android (ADB).
Puxa a gravação interna do BCR, transcreve com Whisper, classifica.
Funciona 100% remoto — sem microfone do computador.

Classificações:
  ✅ Pessoa Atendeu
  📫 Caixa Postal
  📵 Fora de Área
  ❌ Número Inexistente
  🚫 Bloqueado
  📞 Ocupado
  ⏰ Não Atendeu
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from config import (
    TEMPO_ESPERA_CHAMADA,
    TEMPO_ENTRE_CHAMADAS,
    PASTA_AUDIOS,
    PASTA_RESULTADOS,
)
from phone_controller import PhoneController
from audio_recorder import AudioRecorder
from transcriber import transcrever, carregar_modelo
from classifier import classificar
from audio_analyzer import analisar_audio
from excel_handler import ler_numeros, salvar_resultados


def _formatar_numero(numero: str) -> str:
    """
    Remove prefixo de código de país (55) e DDD (92) se presente.
    5592981523468 → 981523468
    92981523468   → 981523468
    981523468     → 981523468
    """
    n = numero.strip()
    # Remover código do país 55
    if len(n) == 13 and n.startswith("55"):
        n = n[4:]  # Remove 55 + DDD (2 dígitos)
    elif len(n) == 11 and n[:2] in ("92", "91", "96", "97", "69", "68", "63"):
        n = n[2:]  # Remove DDD
    return n


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )


def print_banner():
    print("""
╔══════════════════════════════════════════════════╗
║     📞  VALIDADOR DE TELEFONES v2.0  📞         ║
║     BCR + ADB + Whisper (modo remoto)            ║
╚══════════════════════════════════════════════════╝
    """)


def print_progresso(atual: int, total: int, resultado: dict):
    pct = atual / total
    barra = "█" * int(pct * 30) + "░" * (30 - int(pct * 30))
    print(f"\n  [{barra}] {atual}/{total} ({pct:.0%})")
    print(f"  Resultado: {resultado.get('descricao', '?')} (confiança: {resultado.get('confianca', 0):.0%})")
    trans = resultado.get('transcricao', '(sem áudio)')
    if trans:
        print(f"  Transcrição: {trans[:70]}")
    print()


def processar_numero(
    numero_info: dict,
    phone: PhoneController,
    recorder: AudioRecorder,
) -> dict:
    """
    Processa um número: disca → monitora estado → puxa áudio BCR → transcreve → classifica.
    """
    numero = numero_info["numero"]
    nome = numero_info.get("nome", "")
    logger = logging.getLogger(__name__)

    logger.info(f"{'='*50}")
    logger.info(f"Processando: {numero} ({nome})")
    logger.info(f"{'='*50}")

    resultado = {
        "numero": numero,
        "nome": nome,
        "horario": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }

    try:
        # 1. Discar (remover prefixo 55 + DDD se presente)
        numero_discar = _formatar_numero(numero)
        sucesso = phone.discar(numero_discar)
        if not sucesso:
            resultado.update({
                "codigo": "ERRO",
                "descricao": "⚠️ Erro ao discar",
                "confianca": 0,
                "padrao_encontrado": "falha no ADB",
                "transcricao": "",
            })
            return resultado

        time.sleep(2)

        # 2. Monitorar estado (detecta DIALING → ACTIVE ou timeout)
        logger.info("Monitorando chamada...")
        timestamp_inicio = time.time()
        monitor = phone.monitorar_chamada(TEMPO_ESPERA_CHAMADA)

        # 3. Encerrar chamada
        phone.encerrar_chamada()
        time.sleep(1)

        # 4. Ler call log
        call_log = phone.ler_call_log(numero_discar)
        logger.info(f"Call log: duracao={call_log['duration']}s, tipo={call_log['type']}")

        # 5. Puxar áudio BCR SEMPRE (gravação completa, inclui fala da operadora)
        transcricao = ""
        audio_info = None

        logger.info("Puxando gravação do celular...")
        audio_path = recorder.puxar_gravacao(numero_discar, timestamp_inicio)
        dialing_longo = monitor.get("tempo_ate_atender", 0) and monitor["tempo_ate_atender"] > 20

        if audio_path:
            audio_info = analisar_audio(audio_path)
            if audio_info.get("tem_fala") or dialing_longo or monitor.get("atendeu"):
                # Transcrever se tem fala OU se DIALING foi longo (provável operadora)
                transcricao = transcrever(audio_path)
                logger.info(f"Transcrição: {transcricao[:80]}")
            else:
                logger.info("Audio silencioso — sem fala detectada")
        else:
            logger.info("Sem gravação BCR disponível")

        # 6. Classificar
        class_result = classificar(transcricao, monitor, call_log, audio_info)

        resultado.update(class_result)
        resultado["duracao_chamada"] = call_log["duration"]

    except Exception as e:
        logger.error(f"Erro processando {numero}: {e}")
        resultado.update({
            "codigo": "ERRO",
            "descricao": "⚠️ Erro na Ligação",
            "confianca": 0,
            "padrao_encontrado": str(e),
            "transcricao": "",
        })

    return resultado


def main():
    parser = argparse.ArgumentParser(
        description="Validador de Telefones v2.0 — Remoto via BCR + ADB"
    )
    parser.add_argument("planilha", help="Caminho da planilha Excel com os números")
    parser.add_argument("--coluna", default=None, help="Nome da coluna de telefones")
    parser.add_argument("--aba", default=None, help="Nome da aba da planilha")
    parser.add_argument("--saida", default=None, help="Caminho do arquivo de saída")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verboso")
    parser.add_argument("--limite", type=int, default=0, help="Limitar número de chamadas (0=todas)")
    parser.add_argument("--inicio", type=int, default=1, help="Começar do N-ésimo número")
    parser.add_argument("--teste", action="store_true", help="Modo teste: só ler números, não discar")

    args = parser.parse_args()

    setup_logging(args.verbose)
    print_banner()

    logger = logging.getLogger(__name__)

    os.makedirs(PASTA_AUDIOS, exist_ok=True)
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)

    # 1. Ler números da planilha
    print("📋 Lendo planilha...")
    numeros = ler_numeros(args.planilha, args.coluna, args.aba)

    if not numeros:
        print("❌ Nenhum número encontrado na planilha!")
        sys.exit(1)

    print(f"   Encontrados: {len(numeros)} números\n")

    if args.inicio > 1:
        numeros = numeros[args.inicio - 1:]
    if args.limite > 0:
        numeros = numeros[:args.limite]

    # Modo teste
    if args.teste:
        print("🧪 MODO TESTE — apenas mostrando números:\n")
        for i, n in enumerate(numeros, 1):
            print(f"  {i}. {n['numero']}  ({n.get('nome', '')})")
        print(f"\n  Total: {len(numeros)} números")
        sys.exit(0)

    # 2. Inicializar
    print("📱 Conectando ao celular Android...")
    phone = PhoneController()

    print("🎙️  Inicializando gravador (BCR no celular)...")
    recorder = AudioRecorder()

    print("🧠 Carregando modelo Whisper...")
    carregar_modelo()

    tempo_est = len(numeros) * (TEMPO_ESPERA_CHAMADA + TEMPO_ENTRE_CHAMADAS + 10) // 60
    print(f"\n{'='*50}")
    print(f"  Iniciando validação de {len(numeros)} números")
    print(f"  Tempo estimado: ~{tempo_est} minutos")
    print(f"  Modo: REMOTO (áudio interno do celular via BCR)")
    print(f"{'='*50}")

    input("\n  Pressione ENTER para começar (Ctrl+C para cancelar)...")

    # 3. Processar cada número
    resultados = []

    try:
        for i, numero_info in enumerate(numeros, 1):
            print(f"\n{'─'*50}")
            print(f"  📞 Ligação {i}/{len(numeros)}")
            print(f"  Número: {numero_info['numero']}")
            if numero_info.get("nome"):
                print(f"  Nome: {numero_info['nome']}")
            print(f"{'─'*50}")

            resultado = processar_numero(numero_info, phone, recorder)
            resultados.append(resultado)

            print_progresso(i, len(numeros), resultado)

            # Salvar parcial a cada 10 ligações
            if i % 10 == 0:
                salvar_resultados(resultados, args.saida)
                logger.info(f"Resultados parciais salvos ({i}/{len(numeros)})")

            # Pausa entre chamadas
            if i < len(numeros):
                print(f"  ⏳ Aguardando {TEMPO_ENTRE_CHAMADAS}s antes da próxima...")
                time.sleep(TEMPO_ENTRE_CHAMADAS)

    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrompido pelo usuário!")
        print(f"   Processados: {len(resultados)}/{len(numeros)}")

    # 4. Salvar resultados
    if resultados:
        print("\n💾 Salvando resultados...")
        caminho_saida = salvar_resultados(resultados, args.saida)
        print(f"   Arquivo salvo: {caminho_saida}")

        # Resumo final
        print(f"\n{'='*50}")
        print("  📊 RESUMO FINAL")
        print(f"{'='*50}")

        contagem = {}
        confianca_media = []
        for r in resultados:
            cat = r.get("descricao", "?")
            contagem[cat] = contagem.get(cat, 0) + 1
            confianca_media.append(r.get("confianca", 0))

        for cat, qtd in sorted(contagem.items(), key=lambda x: -x[1]):
            pct = qtd / len(resultados) * 100
            print(f"   {cat}: {qtd} ({pct:.0f}%)")

        media = sum(confianca_media) / len(confianca_media) if confianca_media else 0
        print(f"\n   Total processado: {len(resultados)}")
        print(f"   Confiança média: {media:.0%}")
        print(f"   Arquivo: {caminho_saida}")
    else:
        print("\n❌ Nenhum resultado para salvar.")

    print("\n✅ Concluído!\n")


if __name__ == "__main__":
    main()
