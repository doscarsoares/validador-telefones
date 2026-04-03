"""
Controlador do telefone Android via ADB.
Faz chamadas, encerra, monitora estados, lê call log.
"""

import subprocess
import time
import re
import logging

from config import ADB_PATH, DEVICE_SERIAL, TEMPO_ESPERA_CHAMADA, TEMPO_GRAVACAO_APOS_ATENDER

logger = logging.getLogger(__name__)


class PhoneController:
    """Controla um celular Android via ADB para fazer/encerrar chamadas."""

    def __init__(self):
        self.adb = ADB_PATH
        self.device = DEVICE_SERIAL
        self._verificar_conexao()

    def _cmd(self, args: list[str], timeout: int = 10) -> str:
        cmd = [self.adb]
        if self.device:
            cmd += ["-s", self.device]
        cmd += args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout no comando ADB: {' '.join(args[:3])}")
            return ""
        except FileNotFoundError:
            raise RuntimeError(f"ADB não encontrado em '{self.adb}'.")

    def _verificar_conexao(self):
        output = self._cmd(["devices"])
        lines = [l for l in output.split("\n") if "\tdevice" in l]
        if not lines:
            raise RuntimeError(
                "Nenhum dispositivo Android conectado!\n"
                "1. Conecte o celular via USB\n"
                "2. Ative 'Depuração USB'\n"
                "3. Aceite o prompt no celular"
            )
        device_id = lines[0].split("\t")[0]
        if not self.device:
            self.device = device_id
        logger.info(f"Dispositivo conectado: {self.device}")

    def get_telecom_state(self) -> str:
        """
        Retorna o estado da chamada via dumpsys telecom.
        Retorna: 'DIALING', 'ACTIVE', 'RINGING', 'DISCONNECTED', 'IDLE', etc.
        """
        output = self._cmd(["shell", "dumpsys", "telecom"])
        match = re.search(
            r"state=(DIALING|ACTIVE|RINGING|ON_HOLD|CONNECTING|PULLING|DISCONNECTING|DISCONNECTED)",
            output
        )
        if match:
            return match.group(1)
        return "IDLE"

    def discar(self, numero: str) -> bool:
        numero_limpo = re.sub(r"[^\d+]", "", numero)
        if not numero_limpo:
            logger.error(f"Número inválido: {numero}")
            return False
        logger.info(f"Discando: {numero_limpo}")
        self._cmd([
            "shell", "am", "start",
            "-a", "android.intent.action.CALL",
            "-d", f"tel:{numero_limpo}"
        ])
        # Silenciar microfone para a pessoa não ouvir o ambiente
        time.sleep(1)
        self.silenciar_microfone()
        return True

    def silenciar_microfone(self):
        """Silencia o microfone durante a chamada sem aviso na tela."""
        self._cmd(["shell", "media", "volume", "--stream", "6", "--set", "0"])
        logger.info("Microfone silenciado (volume TX = 0)")

    def rejeitar_chamada_recebida(self):
        """Se tiver chamada entrando (RINGING), rejeita e continua."""
        estado = self.get_telecom_state()
        if estado == "RINGING":
            logger.info("Chamada recebida detectada — rejeitando...")
            self._cmd(["shell", "input", "keyevent", "KEYCODE_ENDCALL"])
            time.sleep(1)
            return True
        return False

    def esta_conectado(self) -> bool:
        """Verifica se o celular ainda está conectado via ADB."""
        try:
            output = self._cmd(["devices"], timeout=5)
            return "\tdevice" in output
        except Exception:
            return False

    def encerrar_chamada(self):
        logger.info("Encerrando chamada...")
        self._cmd(["shell", "input", "keyevent", "KEYCODE_ENDCALL"])
        time.sleep(1)

    def monitorar_chamada(self, timeout: int = None) -> dict:
        """
        Monitora a chamada via dumpsys telecom.
        Detecta transições: IDLE → DIALING → ACTIVE (atendeu) → IDLE (desligou).

        Retorna dict com:
            atendeu: True se a chamada foi atendida (state=ACTIVE)
            tempo_ate_atender: segundos até atender (None se não atendeu)
            duracao_offhook: segundos total fora do IDLE
            desligou_rapido: True se voltou a IDLE em < 5s
            estados: lista de (tempo, estado)
        """
        if timeout is None:
            timeout = TEMPO_ESPERA_CHAMADA

        inicio = time.time()
        estados = []
        estado_anterior = "IDLE"
        atendeu = False
        tempo_ate_atender = None
        primeiro_nao_idle = None

        # Esperar sair de IDLE (até 5s)
        while time.time() - inicio < 5:
            estado = self.get_telecom_state()
            if estado != "IDLE":
                t = time.time() - inicio
                estados.append((round(t, 1), estado))
                logger.info(f"  Estado: {estado} em t={t:.1f}s")
                estado_anterior = estado
                primeiro_nao_idle = t
                break
            time.sleep(0.3)

        if primeiro_nao_idle is None:
            logger.warning("Chamada não iniciou (nunca saiu de IDLE)")
            return {
                "atendeu": False,
                "tempo_ate_atender": None,
                "duracao_offhook": 0,
                "desligou_rapido": True,
                "estados": [(0, "IDLE")],
                "tempo_total": round(time.time() - inicio, 1),
            }

        # Monitorar até ACTIVE (atendeu), IDLE (desligou), ou timeout
        while time.time() - inicio < timeout:
            estado = self.get_telecom_state()
            t = time.time() - inicio

            if estado != estado_anterior:
                estados.append((round(t, 1), estado))
                logger.info(f"  Estado: {estado} em t={t:.1f}s")
                estado_anterior = estado

            # Atendeu!
            if estado == "ACTIVE":
                atendeu = True
                tempo_ate_atender = round(t, 1)
                logger.info(f"  >>> ATENDEU em t={t:.1f}s! Gravando {TEMPO_GRAVACAO_APOS_ATENDER}s...")
                # Esperar N segundos para captar áudio da conversa
                time.sleep(TEMPO_GRAVACAO_APOS_ATENDER)
                break

            # Chamada terminou (voltou a IDLE ou desconectou)
            if estado in ("IDLE", "DISCONNECTED"):
                # Confirmar que realmente terminou (esperar 1.5s)
                time.sleep(1.5)
                estado2 = self.get_telecom_state()
                if estado2 in ("IDLE", "DISCONNECTED"):
                    break
                # Se voltou a outro estado, continuar monitorando

            time.sleep(0.8)

        tempo_total = time.time() - inicio
        duracao_offhook = tempo_total - primeiro_nao_idle if primeiro_nao_idle is not None else 0
        desligou_rapido = duracao_offhook < 5 and not atendeu

        return {
            "atendeu": atendeu,
            "tempo_ate_atender": tempo_ate_atender,
            "duracao_offhook": round(duracao_offhook, 1),
            "desligou_rapido": desligou_rapido,
            "estados": estados,
            "tempo_total": round(tempo_total, 1),
        }

    def ler_call_log(self, numero: str) -> dict:
        """Lê a entrada mais recente do call log para o número discado."""
        time.sleep(1)

        output = self._cmd([
            "shell", "content", "query",
            "--uri", "content://call_log/calls",
            "--projection", "_id:number:type:duration:date",
            "--sort", "date DESC",
        ])

        num_limpo = re.sub(r"[^\d]", "", numero)

        for line in output.split("\n")[:15]:
            if "Row:" not in line:
                continue
            match_dur = re.search(r"duration=(\d+)", line)
            match_type = re.search(r"type=(\d+)", line)
            match_num = re.search(r"number=(\d+)", line)

            if match_dur and match_type and match_num:
                num_log = match_num.group(1)
                # Match: últimos 8 dígitos iguais
                if num_limpo[-8:] == num_log[-8:]:
                    dur = int(match_dur.group(1))
                    typ = int(match_type.group(1))
                    logger.info(f"Call log: {num_log} -> duracao={dur}s, tipo={typ}")
                    return {"duration": dur, "type": typ}

        # Fallback: primeira entrada (mais recente)
        for line in output.split("\n"):
            if "Row: 0" in line:
                match_dur = re.search(r"duration=(\d+)", line)
                match_type = re.search(r"type=(\d+)", line)
                if match_dur and match_type:
                    dur = int(match_dur.group(1))
                    typ = int(match_type.group(1))
                    logger.info(f"Call log (fallback Row 0): duracao={dur}s, tipo={typ}")
                    return {"duration": dur, "type": typ}

        logger.warning(f"Call log nao encontrado para {numero}")
        return {"duration": 0, "type": 0}

    def listar_dispositivos(self) -> list[str]:
        output = self._cmd(["devices", "-l"])
        return output.split("\n")
