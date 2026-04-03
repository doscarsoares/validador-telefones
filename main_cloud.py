#!/usr/bin/env python3
"""
=================================================================
  VALIDADOR DE TELEFONES — MODO NUVEM
  Pega números do Google Sheets, disca, devolve resultados.
=================================================================
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
from cloud_handler import CloudHandler


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
║     📞  VALIDADOR DE TELEFONES — NUVEM  📞      ║
║     Google Sheets + ADB + Whisper                ║
╚══════════════════════════════════════════════════╝
    """)


def processar_numero(numero_info, phone, recorder):
    """Processa um número: disca → monitora → transcreve → classifica."""
    numero = numero_info["numero"]
    operadora = numero_info.get("operadora", "")
    logger = logging.getLogger(__name__)

    logger.info(f"{'='*50}")
    logger.info(f"Processando: {numero} ({operadora})")

    tentativa = numero_info.get("tentativa", 1)

    resultado = {
        "numero": numero,
        "operadora": operadora,
        "tentativa": tentativa,
        "horario": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }

    try:
        # 1. Discar
        # Remover DDD 92 se presente (o celular já está no DDD 92)
        numero_discar = numero
        if len(numero) == 11 and numero.startswith("92"):
            numero_discar = numero[2:]  # Remove DDD

        sucesso = phone.discar(numero_discar)
        if not sucesso:
            resultado.update({
                "codigo": "ERRO", "descricao": "⚠️ Erro ao discar",
                "confianca": 0, "padrao_encontrado": "falha ADB", "transcricao": "",
            })
            return resultado

        time.sleep(2)

        # 2. Monitorar
        timestamp_inicio = time.time()
        monitor = phone.monitorar_chamada(TEMPO_ESPERA_CHAMADA)

        # 3. Encerrar
        phone.encerrar_chamada()
        time.sleep(1)

        # 4. Call log
        call_log = phone.ler_call_log(numero_discar)

        # 5. Áudio — sempre puxar
        transcricao = ""
        audio_info = None
        dialing_longo = monitor.get("tempo_ate_atender", 0) and monitor["tempo_ate_atender"] > 20

        audio_path = recorder.puxar_gravacao(numero_discar, timestamp_inicio)
        if audio_path:
            audio_info = analisar_audio(audio_path)
            if audio_info.get("tem_fala") or dialing_longo or monitor.get("atendeu"):
                transcricao = transcrever(audio_path)

        # 6. Classificar
        class_result = classificar(transcricao, monitor, call_log, audio_info)
        resultado.update(class_result)
        resultado["duracao_chamada"] = call_log.get("duration", 0)

    except Exception as e:
        logger.error(f"Erro processando {numero}: {e}")
        resultado.update({
            "codigo": "ERRO", "descricao": "⚠️ Erro na Ligação",
            "confianca": 0, "padrao_encontrado": str(e), "transcricao": "",
        })

    return resultado


def main():
    parser = argparse.ArgumentParser(description="Validador de Telefones — Modo Nuvem")
    parser.add_argument("url", help="URL do Google Apps Script")
    parser.add_argument("--celular", default=None, help="Nome deste celular (ex: cel1)")
    parser.add_argument("--lote", type=int, default=10, help="Números por lote (padrão: 10)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--continuo", action="store_true", help="Rodar sem parar (pede mais números automaticamente)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    print_banner()

    logger = logging.getLogger(__name__)
    os.makedirs(PASTA_AUDIOS, exist_ok=True)
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)

    # Nome do celular
    nome_celular = args.celular
    if not nome_celular:
        nome_celular = input("  Nome deste celular (ex: cel1, cel2): ").strip() or "celular1"

    # Conectar
    print("📱 Conectando ao celular Android...")
    phone = PhoneController()

    print("🎙️  Inicializando gravador...")
    recorder = AudioRecorder()

    print("🧠 Carregando Whisper...")
    carregar_modelo()

    # Conectar à nuvem
    print(f"☁️  Conectando à nuvem...")
    cloud = CloudHandler(args.url, nome_celular)

    # Verificar conexão
    status = cloud.get_status()
    if status.get("erro"):
        print(f"❌ Erro ao conectar na nuvem: {status.get('mensagem')}")
        sys.exit(1)

    print(f"   Disponíveis: {status.get('disponiveis', '?')}")
    print(f"   Em andamento: {status.get('em_andamento', '?')}")
    print(f"   Resultados: {status.get('resultados', '?')}")

    print(f"\n{'='*50}")
    print(f"  Celular: {nome_celular}")
    print(f"  Lote: {args.lote} números por vez")
    print(f"  Modo: {'CONTÍNUO' if args.continuo else 'ÚNICO'}")
    print(f"{'='*50}")

    input("\n  Pressione ENTER para começar (Ctrl+C para cancelar)...")

    total_processado = 0

    try:
        while True:
            # Pedir números
            print(f"\n☁️  Pedindo {args.lote} números da nuvem...")
            numeros = cloud.pedir_numeros(args.lote)

            if not numeros:
                print("  Sem números disponíveis!")
                if args.continuo:
                    print("  Aguardando 30s para novos números...")
                    time.sleep(30)
                    continue
                else:
                    break

            print(f"  Recebidos: {len(numeros)} números")

            # Processar cada número
            numeros_pendentes = [n["numero"] for n in numeros]

            for i, numero_info in enumerate(numeros, 1):
                print(f"\n{'─'*50}")
                print(f"  📞 Ligação {i}/{len(numeros)} (total: {total_processado + i})")
                tent = numero_info.get('tentativa', 1)
                tent_str = f" [tentativa {tent}]" if tent > 1 else ""
                print(f"  Número: {numero_info['numero']} ({numero_info.get('operadora', '?')}){tent_str}")
                print(f"{'─'*50}")

                resultado = processar_numero(numero_info, phone, recorder)
                resultado["operadora"] = numero_info.get("operadora", "")

                # Enviar resultado imediatamente
                cloud.enviar_resultado(resultado)

                # Remover dos pendentes
                if numero_info["numero"] in numeros_pendentes:
                    numeros_pendentes.remove(numero_info["numero"])

                # Mostrar progresso
                desc = resultado.get("descricao", "?")
                conf = resultado.get("confianca", 0)
                print(f"\n  Resultado: {desc} (confiança: {conf:.0%})")

                total_processado += 1

                # Pausa entre chamadas
                if i < len(numeros):
                    time.sleep(TEMPO_ENTRE_CHAMADAS)

            if not args.continuo:
                print(f"\n  Lote concluído! ({total_processado} números processados)")
                resp = input("  Pedir mais números? (s/n): ").strip().lower()
                if resp != "s":
                    break

    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrompido!")
        print(f"   Processados: {total_processado}")

        # Devolver números não processados
        if numeros_pendentes:
            print(f"   Devolvendo {len(numeros_pendentes)} números não processados...")
            cloud.devolver_numeros(numeros_pendentes)

    # Status final
    print(f"\n{'='*50}")
    print("  📊 STATUS FINAL")
    status = cloud.get_status()
    if not status.get("erro"):
        print(f"  Disponíveis: {status.get('disponiveis', '?')}")
        print(f"  Em andamento: {status.get('em_andamento', '?')}")
        print(f"  Resultados: {status.get('resultados', '?')}")
    print(f"  Este celular processou: {total_processado}")
    print(f"{'='*50}")
    print(f"\n✅ Concluído!\n")


if __name__ == "__main__":
    main()
