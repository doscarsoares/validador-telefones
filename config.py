"""
Configurações do Sistema de Validação de Telefones
"""

# === ADB ===
ADB_PATH = "adb"  # Caminho do executável ADB (se estiver no PATH, deixar assim)
DEVICE_SERIAL = None  # None = usar primeiro dispositivo. Ou especificar: "XXXXXXX"

# === TEMPOS (em segundos) ===
TEMPO_ESPERA_CHAMADA = 22      # Quanto tempo esperar antes de considerar "não atendeu"
TEMPO_ENTRE_CHAMADAS_MIN = 7   # Pausa MÍNIMA entre ligações
TEMPO_ENTRE_CHAMADAS_MAX = 15  # Pausa MÁXIMA entre ligações (aleatório entre min e max)
TEMPO_ENTRE_CHAMADAS = 3       # Fallback (usado se não usar aleatório)
TEMPO_GRAVACAO_APOS_ATENDER = 4  # Segundos extras após detectar que atendeu
TEMPO_TOQUE_MINIMO = 5         # Tempo mínimo de toque antes de considerar válido

# === GRAVAÇÃO DE ÁUDIO ===
# Usar BCR (Basic Call Recorder) instalado no celular
# O BCR grava internamente e salva no caminho abaixo
CAMINHO_BCR = "/storage/emulated/0/Download/Bcr/"

# === PASTA LOCAL ===
PASTA_AUDIOS = "audios/"           # Onde salvar os áudios puxados do celular
PASTA_RESULTADOS = "resultados/"   # Onde salvar os resultados

# === WHISPER (Transcrição) ===
WHISPER_MODEL = "small"    # Opções: tiny, base, small, medium, large
WHISPER_LANGUAGE = "pt"    # Português

# === CLASSIFICAÇÃO ===
# Padrões de texto encontrados em mensagens de operadora
PADROES_CLASSIFICACAO = {
    "CAIXA_POSTAL": [
        # --- Frases genéricas ---
        "caixa postal",
        "correio de voz",
        "após o sinal",
        "depois do sinal",
        "grave sua mensagem",
        "grave seu recado",
        "deixe sua mensagem",
        "deixe seu recado",
        "no momento não pode atender",
        "não pode atender sua ligação",
        "voicemail",
        "gravar mensagem",
        "tente novamente mais tarde",
        # --- VIVO ---
        "a pessoa para quem você ligou não pode atender",
        "a chamada será encaminhada para a caixa postal",
        # --- CLARO ---
        "o cliente claro que você chamou",
        "o número chamado não pode atender",
        "a ligação será transferida para a caixa de mensagem",
        "chamado não atendeu",
        # --- TIM ---
        "o número tim chamado",
        "o assinante tim",
        "encaminhada para a caixa postal",
        "tim correio de voz",
        # --- OI ---
        "o número oi",
        "o cliente oi",
        "encaminhada para o correio de voz",
    ],
    "FORA_DE_AREA": [
        # --- Frases genéricas ---
        "fora da área",
        "fora de área",
        "área de cobertura",
        "fora do alcance",
        "sem cobertura",
        "está desligado",
        "encontra-se desligado",
        "aparelho desligado",
        "fora da área de serviço",
        "no momento está indisponível",
        "temporariamente indisponível",
        # --- VIVO ---
        "o número vivo chamado está desligado ou fora da área",
        "vivo chamado não pode ser completada",
        # --- CLARO ---
        "o cliente claro chamado encontra-se desligado",
        "claro chamado está desligado ou fora",
        # --- TIM ---
        "o número tim chamado está desligado ou fora",
        "assinante tim está indisponível",
        # --- OI ---
        "o cliente oi está desligado",
        "oi chamado encontra-se desligado",
    ],
    "NUMERO_INEXISTENTE": [
        # --- Frases genéricas ---
        "não existe",
        "não é válido",
        "número inválido",
        "não foi possível completar",
        "número inexistente",
        "não pode ser completada",
        "verifique o número",
        "disque novamente",
        "este número não está disponível",
        "número discado não existe",
        "ligação não pode ser completada como discada",
        "confira o número e tente novamente",
        "código de área",
        "o número chamado não está em operação",
        "não foi possível conectar",
        "chamada não pode ser realizada",
    ],
    "BLOQUEADO": [
        "programado para não receber",
        "não aceita chamadas",
        "chamada bloqueada",
        "está bloqueado",
        "restrição de chamadas",
        "barrado",
        "não está habilitado para receber",
        "este tipo de chamada",
        "programado para não receber este tipo",
        "não recebe chamadas",
        "não pode receber sua chamada",
        "não pode receber chamada",
    ],
    "OCUPADO": [
        "ocupado",
        "tente mais tarde",
        "linha ocupada",
        "chamada em espera",
        "em outra ligação",
    ],
    "PESSOA_ATENDEU": [
        "alô",
        "alo",
        "oi",
        "pronto",
        "fala",
        "sim",
        "quem fala",
        "quem é",
        "bom dia",
        "boa tarde",
        "boa noite",
        "diga",
        "pois não",
        "hein",
        "pode falar",
        "tô ouvindo",
        "estou ouvindo",
        "fala aí",
    ],
}

# Heurísticas de tamanho do texto
LIMITE_PALAVRAS_OPERADORA = 8
LIMITE_PALAVRAS_PESSOA = 4

# Resultado padrão quando nenhum padrão é encontrado
RESULTADO_PADRAO = "NAO_ATENDEU"
