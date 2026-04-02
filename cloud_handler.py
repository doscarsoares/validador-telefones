"""
Conexão com o Google Sheets (servidor na nuvem).
Pede números, envia resultados.
"""

import json
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)


class CloudHandler:
    """Comunica com o Google Apps Script para pedir números e enviar resultados."""

    def __init__(self, url_script: str, nome_celular: str):
        self.url = url_script.rstrip("/")
        self.celular = nome_celular
        logger.info(f"CloudHandler: celular='{nome_celular}', url={url_script[:50]}...")

    def pedir_numeros(self, quantidade: int = 10) -> list[dict]:
        """
        Pede números para discar.
        Retorna lista de dicts: [{"numero": "92991234567", "operadora": "CLARO"}, ...]
        """
        params = urllib.parse.urlencode({
            "acao": "pedir",
            "celular": self.celular,
            "qtd": quantidade,
        })
        url = f"{self.url}?{params}"

        try:
            logger.info(f"Pedindo {quantidade} números da nuvem...")
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                dados = json.loads(resp.read().decode("utf-8"))

            if dados.get("erro"):
                logger.error(f"Erro da nuvem: {dados.get('mensagem')}")
                return []

            numeros = dados.get("numeros", [])
            restantes = dados.get("disponiveis_restantes", "?")
            logger.info(f"Recebidos {len(numeros)} números ({restantes} restantes na fila)")
            return numeros

        except Exception as e:
            logger.error(f"Erro ao pedir números: {e}")
            return []

    def enviar_resultado(self, resultado: dict) -> bool:
        """
        Envia o resultado de uma ligação para a nuvem.
        """
        payload = {
            "acao": "resultado",
            "celular": self.celular,
            "numero": resultado.get("numero", ""),
            "operadora": resultado.get("operadora", ""),
            "classificacao": resultado.get("descricao", ""),
            "confianca": resultado.get("confianca", 0),
            "transcricao": resultado.get("transcricao", "")[:200],
            "duracao": resultado.get("duracao_chamada", 0),
            "tentativa": resultado.get("tentativa", 1),
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resposta = json.loads(resp.read().decode("utf-8"))

            if resposta.get("erro"):
                logger.error(f"Erro ao enviar resultado: {resposta.get('mensagem')}")
                return False

            logger.info(f"Resultado enviado: {resultado.get('numero')} → {resultado.get('descricao')}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar resultado: {e}")
            return False

    def enviar_resultados_lote(self, resultados: list[dict]) -> bool:
        """
        Envia vários resultados de uma vez.
        """
        payload = {
            "acao": "resultados",
            "celular": self.celular,
            "resultados": [
                {
                    "numero": r.get("numero", ""),
                    "operadora": r.get("operadora", ""),
                    "classificacao": r.get("descricao", ""),
                    "confianca": r.get("confianca", 0),
                    "transcricao": r.get("transcricao", "")[:200],
                    "duracao": r.get("duracao_chamada", 0),
                }
                for r in resultados
            ],
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resposta = json.loads(resp.read().decode("utf-8"))

            if resposta.get("erro"):
                logger.error(f"Erro ao enviar lote: {resposta.get('mensagem')}")
                return False

            logger.info(f"Lote enviado: {len(resultados)} resultados")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar lote: {e}")
            return False

    def devolver_numeros(self, numeros: list[str]) -> bool:
        """
        Devolve números que não foram discados (ex: programa interrompido).
        """
        payload = {
            "acao": "devolver",
            "celular": self.celular,
            "numeros": numeros,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resposta = json.loads(resp.read().decode("utf-8"))

            logger.info(f"Devolvidos {len(numeros)} números")
            return True

        except Exception as e:
            logger.error(f"Erro ao devolver números: {e}")
            return False

    def get_status(self) -> dict:
        """Consulta status do sistema."""
        params = urllib.parse.urlencode({"acao": "status"})
        url = f"{self.url}?{params}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Erro ao consultar status: {e}")
            return {"erro": True, "mensagem": str(e)}
