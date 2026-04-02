"""
Gravador de áudio via BCR (Basic Call Recorder).
Puxa a gravação feita pelo celular Android, sem usar microfone do computador.
"""

import os
import re
import time
import logging
import subprocess
from datetime import datetime

from config import CAMINHO_BCR, PASTA_AUDIOS, ADB_PATH, DEVICE_SERIAL

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Puxa gravações de chamada do BCR no celular Android."""

    def __init__(self):
        os.makedirs(PASTA_AUDIOS, exist_ok=True)
        self.adb = ADB_PATH
        self.device = DEVICE_SERIAL
        logger.info("AudioRecorder inicializado (modo: BCR no celular)")

    def _cmd(self, args: list[str], timeout: int = 15) -> str:
        cmd = [self.adb]
        if self.device:
            cmd += ["-s", self.device]
        cmd += args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout ADB: {' '.join(cmd)}")
            return ""

    def listar_gravacoes_bcr(self) -> list[str]:
        """Lista arquivos .m4a no diretório BCR do celular, mais recentes primeiro."""
        output = self._cmd(["shell", "ls", "-lt", CAMINHO_BCR])
        arquivos = []
        for line in output.split("\n"):
            if ".m4a" in line:
                parts = line.split()
                if parts:
                    arquivos.append(parts[-1])
        return arquivos

    def puxar_gravacao(self, numero: str, timestamp_inicio: float) -> str:
        """
        Puxa a gravação BCR mais recente que corresponde ao número discado.

        Args:
            numero: Número discado (para fazer match no nome do arquivo)
            timestamp_inicio: Timestamp de quando a chamada foi iniciada

        Returns:
            Caminho local do arquivo de áudio, ou "" se não encontrado.
        """
        numero_limpo = re.sub(r"[^\d]", "", numero)
        # BCR usa os últimos dígitos no nome do arquivo
        sufixo = numero_limpo[-11:] if len(numero_limpo) > 11 else numero_limpo

        # Esperar um pouco para o BCR salvar o arquivo
        time.sleep(2)

        # Tentar até 3 vezes (BCR pode demorar para salvar)
        for tentativa in range(3):
            arquivos = self.listar_gravacoes_bcr()

            for arquivo in arquivos:
                if sufixo in arquivo and arquivo.endswith(".m4a"):
                    # Encontrou o arquivo correspondente
                    caminho_remoto = f"{CAMINHO_BCR}{arquivo}"

                    # Nome local
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nome_local = f"{ts}_{numero_limpo}.m4a"
                    caminho_local = os.path.join(PASTA_AUDIOS, nome_local)

                    # Puxar do celular
                    result = self._cmd(["pull", caminho_remoto, caminho_local], timeout=30)

                    if os.path.exists(caminho_local) and os.path.getsize(caminho_local) > 500:
                        logger.info(f"Gravação BCR puxada: {caminho_local} ({os.path.getsize(caminho_local)} bytes)")
                        return caminho_local
                    else:
                        logger.warning(f"Arquivo puxado mas vazio ou pequeno: {caminho_local}")

            if tentativa < 2:
                logger.info(f"Gravação BCR não encontrada ainda, tentando novamente... ({tentativa + 1}/3)")
                time.sleep(2)

        logger.warning(f"Nenhuma gravação BCR encontrada para {numero}")
        return ""

    def limpar_gravacao_celular(self, numero: str):
        """Remove a gravação do celular para economizar espaço."""
        numero_limpo = re.sub(r"[^\d]", "", numero)
        sufixo = numero_limpo[-11:] if len(numero_limpo) > 11 else numero_limpo

        arquivos = self.listar_gravacoes_bcr()
        for arquivo in arquivos:
            if sufixo in arquivo:
                caminho = f"{CAMINHO_BCR}{arquivo}"
                self._cmd(["shell", "rm", caminho])
                logger.debug(f"Removida gravação do celular: {arquivo}")
