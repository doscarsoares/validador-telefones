"""
Manipulador de planilhas Excel.
Lê números de telefone e escreve resultados de volta.
Detecta automaticamente qual coluna contém os telefones.
"""

import os
import re
import logging
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

logger = logging.getLogger(__name__)

# Cores para os resultados
CORES = {
    "PESSOA_ATENDEU":     "92D050",  # Verde
    "CAIXA_POSTAL":       "FFC000",  # Amarelo
    "FORA_DE_AREA":       "FF6600",  # Laranja
    "NUMERO_INEXISTENTE": "FF0000",  # Vermelho
    "BLOQUEADO":          "A020F0",  # Roxo
    "OCUPADO":            "00B0F0",  # Azul
    "NAO_ATENDEU":        "BFBFBF",  # Cinza
    "ERRO":               "808080",  # Cinza escuro
}


def _parece_telefone(valor) -> bool:
    """Verifica se um valor parece ser um número de telefone."""
    if valor is None:
        return False
    apenas_digitos = re.sub(r"[^\d]", "", str(valor))
    # Telefone brasileiro: 8 dígitos (fixo local) até 15 (com código país)
    return 8 <= len(apenas_digitos) <= 15


def _encontrar_coluna_telefone(ws) -> int:
    """
    Encontra a coluna que contém os telefones.
    Estratégia:
      1. Procurar pelo nome do cabeçalho
      2. Se não achar, escanear o conteúdo de cada coluna
    """
    headers = {}
    for col_idx, cell in enumerate(ws[1], 1):
        if cell.value:
            headers[str(cell.value).strip().lower()] = col_idx

    # ESTRATÉGIA 1: Procurar pelo nome do cabeçalho
    nomes_telefone = [
        "telefone", "celular", "fone", "tel", "phone", "número", "numero",
        "whatsapp", "contato", "number", "mobile", "cell", "contact",
        "num", "fones", "telefones", "números", "numeros", "ddd",
    ]
    for nome in nomes_telefone:
        for header, idx in headers.items():
            if nome in header:
                logger.info(f"Coluna de telefone encontrada pelo cabeçalho: '{header}' (coluna {idx})")
                return idx

    # ESTRATÉGIA 2: Escanear o conteúdo de cada coluna
    # Quem tiver mais valores que parecem telefone, ganha
    logger.info("Cabeçalho não reconhecido. Escaneando conteúdo das colunas...")
    melhor_coluna = None
    melhor_score = 0

    for col_idx in range(1, ws.max_column + 1):
        score = 0
        for row_idx in range(2, min(52, ws.max_row + 1)):  # Checar até 50 linhas
            celula = ws.cell(row=row_idx, column=col_idx).value
            if _parece_telefone(celula):
                score += 1
        if score > melhor_score:
            melhor_score = score
            melhor_coluna = col_idx

    if melhor_coluna and melhor_score >= 2:
        header_nome = ws.cell(row=1, column=melhor_coluna).value or f"Coluna {melhor_coluna}"
        logger.info(f"Coluna de telefone detectada pelo conteúdo: '{header_nome}' (coluna {melhor_coluna}, score={melhor_score})")
        return melhor_coluna

    # FALLBACK: usar a primeira coluna
    logger.warning("Não foi possível detectar coluna de telefone. Usando coluna 1.")
    return 1


def _encontrar_coluna_nome(ws, col_tel: int) -> int | None:
    """Encontra a coluna que contém os nomes (se existir)."""
    nomes_nome = ["nome", "name", "funcionário", "funcionario", "responsável", "responsavel", "pessoa", "colaborador"]
    for col_idx, cell in enumerate(ws[1], 1):
        if cell.value and col_idx != col_tel:
            header = str(cell.value).strip().lower()
            for nome in nomes_nome:
                if nome in header:
                    return col_idx
    return None


def ler_numeros(caminho_excel: str, coluna_telefone: str = None, aba: str = None) -> list[dict]:
    """
    Lê números de telefone de uma planilha Excel.
    Detecta automaticamente a coluna de telefones pelo cabeçalho ou conteúdo.
    
    Args:
        caminho_excel: Caminho do arquivo .xlsx
        coluna_telefone: Nome da coluna com os telefones (auto-detecta se None)
        aba: Nome da aba (usa a primeira se None)
    
    Returns:
        Lista de dicts: [{"linha": 2, "numero": "92991234567", "nome": "João"}, ...]
    """
    if not os.path.exists(caminho_excel):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_excel}")

    wb = load_workbook(caminho_excel, data_only=True)
    ws = wb[aba] if aba and aba in wb.sheetnames else wb.active

    logger.info(f"Lendo planilha: {caminho_excel} (aba: {ws.title})")
    logger.info(f"Dimensões: {ws.max_row} linhas x {ws.max_column} colunas")

    # Mostrar cabeçalhos encontrados
    headers_info = []
    for col_idx, cell in enumerate(ws[1], 1):
        if cell.value:
            headers_info.append(f"Coluna {col_idx}: '{cell.value}'")
    logger.info(f"Cabeçalhos: {', '.join(headers_info)}")

    # Encontrar coluna de telefone
    if coluna_telefone:
        # Usuário especificou a coluna
        headers = {}
        for col_idx, cell in enumerate(ws[1], 1):
            if cell.value:
                headers[str(cell.value).strip().lower()] = col_idx
        col_tel = headers.get(coluna_telefone.lower())
        if not col_tel:
            logger.warning(f"Coluna '{coluna_telefone}' não encontrada. Detectando automaticamente...")
            col_tel = _encontrar_coluna_telefone(ws)
    else:
        col_tel = _encontrar_coluna_telefone(ws)

    # Encontrar coluna de nome
    col_nome = _encontrar_coluna_nome(ws, col_tel)

    # Ler dados
    numeros = []
    ignorados = 0

    for row in ws.iter_rows(min_row=2, max_col=ws.max_column):
        celula_tel = row[col_tel - 1]
        if celula_tel.value is not None and str(celula_tel.value).strip():
            valor_original = str(celula_tel.value).strip()
            # Limpar formatação: remover tudo que não é dígito ou +
            numero = re.sub(r"[^\d+]", "", valor_original)

            if _parece_telefone(numero):
                nome = ""
                if col_nome and len(row) >= col_nome:
                    nome = str(row[col_nome - 1].value or "").strip()

                numeros.append({
                    "linha": celula_tel.row,
                    "numero": numero,
                    "nome": nome,
                })
            else:
                ignorados += 1

    logger.info(f"Total de números encontrados: {len(numeros)}")
    if ignorados > 0:
        logger.info(f"Valores ignorados (não parecem telefone): {ignorados}")

    wb.close()
    return numeros


def salvar_resultados(resultados: list[dict], caminho_saida: str = None):
    """
    Salva os resultados em uma nova planilha Excel formatada.
    """
    if not caminho_saida:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("resultados", exist_ok=True)
        caminho_saida = f"resultados/validacao_{timestamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"

    # Cabeçalho
    headers = ["#", "Nome", "Telefone", "Resultado", "Confiança", "Transcrição", "Padrão Detectado", "Horário"]
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    # Dados
    for i, res in enumerate(resultados, 1):
        row = i + 1
        ws.cell(row=row, column=1, value=i).border = border
        ws.cell(row=row, column=2, value=res.get("nome", "")).border = border
        ws.cell(row=row, column=3, value=res.get("numero", "")).border = border

        # Resultado com cor
        cell_resultado = ws.cell(row=row, column=4, value=res.get("descricao", ""))
        cor = CORES.get(res.get("codigo", ""), "FFFFFF")
        cell_resultado.fill = PatternFill(start_color=cor, end_color=cor, fill_type="solid")
        if cor in ["FF0000", "A020F0"]:
            cell_resultado.font = Font(color="FFFFFF", bold=True)
        else:
            cell_resultado.font = Font(bold=True)
        cell_resultado.border = border

        ws.cell(row=row, column=5, value=f"{res.get('confianca', 0):.0%}").border = border
        ws.cell(row=row, column=6, value=res.get("transcricao", "")).border = border
        ws.cell(row=row, column=7, value=res.get("padrao_encontrado", "")).border = border
        ws.cell(row=row, column=8, value=res.get("horario", "")).border = border

    # Ajustar larguras
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 40
    ws.column_dimensions["G"].width = 25
    ws.column_dimensions["H"].width = 20

    # Resumo na segunda aba
    ws2 = wb.create_sheet("Resumo")
    ws2.cell(row=1, column=1, value="Resumo da Validação").font = Font(bold=True, size=14)
    ws2.cell(row=2, column=1, value=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    ws2.cell(row=3, column=1, value=f"Total de números: {len(resultados)}")

    # Contagem por categoria
    contagem = {}
    for res in resultados:
        cat = res.get("descricao", "Desconhecido")
        contagem[cat] = contagem.get(cat, 0) + 1

    row = 5
    ws2.cell(row=row, column=1, value="Categoria").font = Font(bold=True)
    ws2.cell(row=row, column=2, value="Quantidade").font = Font(bold=True)
    ws2.cell(row=row, column=3, value="Percentual").font = Font(bold=True)

    for cat, qtd in sorted(contagem.items(), key=lambda x: -x[1]):
        row += 1
        ws2.cell(row=row, column=1, value=cat)
        ws2.cell(row=row, column=2, value=qtd)
        ws2.cell(row=row, column=3, value=f"{qtd/len(resultados)*100:.1f}%")

    ws2.column_dimensions["A"].width = 25
    ws2.column_dimensions["B"].width = 15
    ws2.column_dimensions["C"].width = 12

    wb.save(caminho_saida)
    logger.info(f"Resultados salvos: {caminho_saida}")
    return caminho_saida
