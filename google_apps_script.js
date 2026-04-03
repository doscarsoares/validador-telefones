/**
 * ================================================================
 *  VALIDADOR DE TELEFONES — Google Apps Script (Servidor na Nuvem)
 * ================================================================
 *
 * COMO USAR:
 * 1. Abra Google Sheets → Extensões → Apps Script
 * 2. Cole este código inteiro
 * 3. Clique em "Implantar" → "Nova implantação"
 * 4. Tipo: "App da Web"
 * 5. Executar como: "Eu"
 * 6. Quem tem acesso: "Qualquer pessoa"
 * 7. Copie a URL gerada
 * 8. Cole a URL no config.py do programa no celular
 *
 * ABAS (criadas automaticamente):
 * - "Disponíveis": números novos aguardando primeira ligação
 * - "Tentar Novamente": números que precisam ser ligados novamente
 * - "Em Andamento": números sendo discados agora
 * - "Atendeu": RESULTADO ÚTIL — pessoa real atendeu
 * - "Não Atende": tentou 3x e ninguém atendeu (número existe mas não atende)
 * - "Desligados/Inexistentes": números bloqueados, desligados, fora de área (após 3 tentativas)
 * - "Descartados": números que não existem (descarte imediato)
 * - "Resultados": histórico completo de todas as ligações
 * - "Config": configurações e estatísticas
 */

// ================================================================
//  CONFIGURAÇÃO
// ================================================================

const CONFIG = {
  PROPORCOES: {
    VIVO:  0.41,
    CLARO: 0.25,
    TIM:   0.20,
    OI:    0.14,
  },

  PREFIXOS: {
    VIVO:  ["92995", "92996", "92997", "92998", "92999"],
    CLARO: ["92991", "92992", "92993", "92994"],
    TIM:   ["92981", "92982", "92983"],
    OI:    ["92984", "92985", "92988"],
  },

  LOTE_GERACAO: 500,
  MINIMO_DISPONIVEL: 200,
  NUMEROS_POR_PEDIDO: 10,
  TIMEOUT_ANDAMENTO_MIN: 15,

  // Regras de retry por classificação
  // max_tentativas: quantas vezes ligar no total
  // intervalo_min: minutos mínimos entre tentativas
  RETRY: {
    "Não Atendeu":          { max_tentativas: 3, intervalo_min: 180 },  // 3 horas
    "Caixa Postal":         { max_tentativas: 3, intervalo_min: 180 },  // 3 horas
    "Ocupado":              { max_tentativas: 3, intervalo_min: 120 },  // 2 horas
    "Fora de Área":         { max_tentativas: 2, intervalo_min: 360 },  // 6 horas
    "Erro na Ligação":      { max_tentativas: 3, intervalo_min: 10  },  // 10 minutos (não incomoda, nem chama)
    "Bloqueado":            { max_tentativas: 3, intervalo_min: 180 },  // 3 horas — pode ser temporário
    "Silêncio Incerto":     { max_tentativas: 3, intervalo_min: 120 },  // 2 horas — pode ser pessoa ou inválido
  },

  // Classificações que vão direto pro lixo (descartados)
  DESCARTAR: [
    "Número Inexistente",
  ],
};

// ================================================================
//  INICIALIZAÇÃO
// ================================================================

function inicializar() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  function criarAba(nome, headers) {
    let ab = ss.getSheetByName(nome);
    if (!ab) {
      ab = ss.insertSheet(nome);
      ab.getRange(1, 1, 1, headers.length).setValues([headers]);
      ab.getRange(1, 1, 1, headers.length).setFontWeight("bold");
    }
    return ab;
  }

  criarAba("Disponíveis", ["Número", "Operadora"]);

  criarAba("Tentar Novamente", [
    "Número", "Operadora", "Tentativas", "Última Classificação",
    "Última Tentativa", "Próxima Tentativa Após"
  ]);

  criarAba("Em Andamento", ["Número", "Operadora", "Celular", "Hora Início", "Tentativa"]);

  criarAba("Atendeu", [
    "Número", "Operadora", "Confiança", "Transcrição",
    "Celular", "Hora", "Tentativa"
  ]);

  criarAba("Não Atende", [
    "Número", "Operadora", "Tentativas", "Última Classificação",
    "Celular", "Hora"
  ]);

  criarAba("Desligados/Inexistentes", [
    "Número", "Operadora", "Motivo", "Tentativas", "Celular", "Hora"
  ]);

  criarAba("Descartados", [
    "Número", "Operadora", "Motivo", "Tentativas", "Celular", "Hora"
  ]);

  criarAba("Resultados", [
    "Número", "Operadora", "Classificação", "Confiança",
    "Transcrição", "Celular", "Hora", "Duração", "Tentativa"
  ]);

  // Aba Config
  let abConf = ss.getSheetByName("Config");
  if (!abConf) {
    abConf = ss.insertSheet("Config");
    abConf.getRange("A1:B1").setValues([["Parâmetro", "Valor"]]);
    abConf.getRange("A1:B1").setFontWeight("bold");
    abConf.getRange("A2:B9").setValues([
      ["Total Gerados", 0],
      ["Total Discados", 0],
      ["Pessoa Atendeu", 0],
      ["Não Atendeu", 0],
      ["Descartados", 0],
      ["Esgotados (3x)", 0],
      ["Aguardando Religar", 0],
      ["Última Atualização", ""],
    ]);
  }

  gerarNumeros(CONFIG.LOTE_GERACAO);

  SpreadsheetApp.getUi().alert(
    "✅ Sistema inicializado!\n\n" +
    "Agora faça a implantação:\n" +
    "Implantar → Nova implantação → App da Web\n" +
    "Executar como: Eu\n" +
    "Acesso: Qualquer pessoa"
  );
}

// ================================================================
//  GERAÇÃO DE NÚMEROS ALEATÓRIOS
// ================================================================

function gerarNumero(operadora) {
  const prefixos = CONFIG.PREFIXOS[operadora];
  const prefixo = prefixos[Math.floor(Math.random() * prefixos.length)];
  const faltam = 11 - prefixo.length;
  let sufixo = "";
  for (let i = 0; i < faltam; i++) {
    sufixo += Math.floor(Math.random() * 10).toString();
  }
  return prefixo + sufixo;
}

function _coletarTodosNumeros() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const existentes = new Set();

  const abas = ["Disponíveis", "Em Andamento", "Resultados", "Tentar Novamente", "Descartados"];
  for (const nomeAba of abas) {
    const aba = ss.getSheetByName(nomeAba);
    if (!aba || aba.getLastRow() <= 1) continue;
    const dados = aba.getRange(2, 1, aba.getLastRow() - 1, 1).getValues();
    for (const row of dados) {
      if (row[0]) existentes.add(row[0].toString());
    }
  }

  return existentes;
}

function gerarNumeros(quantidade) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const abDisp = ss.getSheetByName("Disponíveis");

  const existentes = _coletarTodosNumeros();

  const porOperadora = {
    VIVO:  Math.round(quantidade * CONFIG.PROPORCOES.VIVO),
    CLARO: Math.round(quantidade * CONFIG.PROPORCOES.CLARO),
    TIM:   Math.round(quantidade * CONFIG.PROPORCOES.TIM),
    OI:    quantidade - Math.round(quantidade * CONFIG.PROPORCOES.VIVO)
                      - Math.round(quantidade * CONFIG.PROPORCOES.CLARO)
                      - Math.round(quantidade * CONFIG.PROPORCOES.TIM),
  };

  const novos = [];
  for (const [operadora, qtd] of Object.entries(porOperadora)) {
    let gerados = 0;
    let tentativas = 0;
    while (gerados < qtd && tentativas < qtd * 10) {
      const numero = gerarNumero(operadora);
      tentativas++;
      if (!existentes.has(numero)) {
        existentes.add(numero);
        novos.push([numero, operadora]);
        gerados++;
      }
    }
  }

  // Embaralhar
  for (let i = novos.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [novos[i], novos[j]] = [novos[j], novos[i]];
  }

  if (novos.length > 0) {
    const ultimaLinha = Math.max(abDisp.getLastRow(), 1);
    abDisp.getRange(ultimaLinha + 1, 1, novos.length, 2).setValues(novos);
  }

  // Atualizar config
  const abConf = ss.getSheetByName("Config");
  if (abConf) {
    const totalAtual = parseInt(abConf.getRange("B2").getValue()) || 0;
    abConf.getRange("B2").setValue(totalAtual + novos.length);
    abConf.getRange("B8").setValue(new Date().toLocaleString("pt-BR"));
  }

  return novos.length;
}

// ================================================================
//  API
// ================================================================

function doGet(e) {
  const acao = (e.parameter.acao || "").toLowerCase();
  const celular = e.parameter.celular || "desconhecido";
  const qtd = parseInt(e.parameter.qtd) || CONFIG.NUMEROS_POR_PEDIDO;

  try {
    switch (acao) {
      case "pedir":
        return responder(pedirNumeros(celular, qtd));
      case "status":
        return responder(getStatus());
      default:
        return responder({
          erro: false,
          mensagem: "Validador de Telefones API",
          acoes: ["pedir", "status"],
        });
    }
  } catch (err) {
    return responder({ erro: true, mensagem: err.toString() });
  }
}

function doPost(e) {
  try {
    const dados = JSON.parse(e.postData.contents);
    const acao = (dados.acao || "").toLowerCase();

    switch (acao) {
      case "resultado":
        return responder(registrarResultado(dados));
      case "resultados":
        return responder(registrarResultados(dados));
      case "devolver":
        return responder(devolverNumeros(dados));
      default:
        return responder({ erro: true, mensagem: "Ação desconhecida: " + acao });
    }
  } catch (err) {
    return responder({ erro: true, mensagem: err.toString() });
  }
}

function responder(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// ================================================================
//  PEDIR NÚMEROS
//  Prioridade: 1º Religar (que já passou o intervalo), 2º Disponíveis
// ================================================================

function pedirNumeros(celular, quantidade) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const abDisp = ss.getSheetByName("Disponíveis");
    const abRel = ss.getSheetByName("Tentar Novamente");
    const abAnd = ss.getSheetByName("Em Andamento");

    const agora = new Date();
    const agoraStr = agora.toLocaleString("pt-BR");
    const numeros = [];
    let qtdFalta = quantidade;

    // --- 1º: Pegar da aba Religar (números prontos para religar) ---
    if (abRel.getLastRow() > 1) {
      const dadosRel = abRel.getDataRange().getValues();
      const linhasRemover = [];

      for (let i = 1; i < dadosRel.length && qtdFalta > 0; i++) {
        const proximaStr = dadosRel[i][5]; // "Próxima Tentativa Após"
        if (!proximaStr) continue;

        const proxima = new Date(proximaStr);
        if (agora >= proxima) {
          // Pronto para religar
          const numero = dadosRel[i][0].toString();
          const operadora = dadosRel[i][1];
          const tentativa = (parseInt(dadosRel[i][2]) || 0) + 1;

          numeros.push({
            numero: numero,
            operadora: operadora,
            tentativa: tentativa,
          });

          // Mover para Em Andamento
          const ultimaAnd = Math.max(abAnd.getLastRow(), 1);
          abAnd.getRange(ultimaAnd + 1, 1, 1, 5).setValues([
            [numero, operadora, celular, agoraStr, tentativa]
          ]);

          linhasRemover.push(i + 1); // +1 porque getDataRange é 0-based, deleteRow é 1-based
          qtdFalta--;
        }
      }

      // Remover de Religar (de baixo pra cima)
      for (let i = linhasRemover.length - 1; i >= 0; i--) {
        abRel.deleteRow(linhasRemover[i]);
      }
    }

    // --- 2º: Pegar de Disponíveis (números novos) ---
    if (qtdFalta > 0) {
      // Verificar se precisa gerar mais
      const totalDisp = abDisp.getLastRow() - 1;
      if (totalDisp < CONFIG.MINIMO_DISPONIVEL) {
        gerarNumeros(CONFIG.LOTE_GERACAO);
      }

      const ultimaLinha = abDisp.getLastRow();
      if (ultimaLinha > 1) {
        const qtdReal = Math.min(qtdFalta, ultimaLinha - 1);
        const range = abDisp.getRange(2, 1, qtdReal, 2);
        const dados = range.getValues();

        for (const row of dados) {
          numeros.push({
            numero: row[0].toString(),
            operadora: row[1],
            tentativa: 1,
          });
        }

        // Mover para Em Andamento
        const paraAnd = dados.map(row => [row[0], row[1], celular, agoraStr, 1]);
        const ultimaAnd = Math.max(abAnd.getLastRow(), 1);
        abAnd.getRange(ultimaAnd + 1, 1, paraAnd.length, 5).setValues(paraAnd);

        // Remover de Disponíveis
        abDisp.deleteRows(2, qtdReal);
      }
    }

    return {
      erro: false,
      numeros: numeros,
      celular: celular,
      quantidade: numeros.length,
      disponiveis_restantes: Math.max(abDisp.getLastRow() - 1, 0),
      religar_pendentes: Math.max(abRel.getLastRow() - 1, 0),
    };

  } finally {
    lock.releaseLock();
  }
}

// ================================================================
//  REGISTRAR RESULTADO
//  Decide: pessoa atendeu → resultado final
//          não atendeu/ocupado → religar ou descartar
//          inexistente/bloqueado → descartar
// ================================================================

function _extrairClassificacao(classificacaoCompleta) {
  // Remove emoji do início: "✅ Pessoa Atendeu" → "Pessoa Atendeu"
  return classificacaoCompleta.replace(/^[^\w\s]+\s*/, "").trim();
}

function registrarResultado(dados) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const abAnd = ss.getSheetByName("Em Andamento");
    const abRes = ss.getSheetByName("Resultados");
    const abRel = ss.getSheetByName("Tentar Novamente");
    const abDesc = ss.getSheetByName("Descartados");
    const abConf = ss.getSheetByName("Config");

    const numero = (dados.numero || "").toString();
    const celular = dados.celular || "desconhecido";
    const classificacaoRaw = dados.classificacao || "";
    const classificacao = _extrairClassificacao(classificacaoRaw);
    const tentativa = parseInt(dados.tentativa) || 1;
    const agora = new Date();
    const agoraStr = agora.toLocaleString("pt-BR");

    // 1. Gravar no histórico de resultados (sempre)
    const ultimaRes = Math.max(abRes.getLastRow(), 1);
    abRes.getRange(ultimaRes + 1, 1, 1, 9).setValues([[
      numero,
      dados.operadora || "",
      classificacaoRaw,
      dados.confianca || 0,
      (dados.transcricao || "").substring(0, 200),
      celular,
      agoraStr,
      dados.duracao || 0,
      tentativa,
    ]]);

    // 2. Remover de Em Andamento
    const dadosAnd = abAnd.getDataRange().getValues();
    for (let i = dadosAnd.length - 1; i >= 1; i--) {
      if (dadosAnd[i][0].toString() === numero) {
        abAnd.deleteRow(i + 1);
        break;
      }
    }

    // 3. Decidir destino
    const abAtendeu = ss.getSheetByName("Atendeu");
    const abEsgotado = ss.getSheetByName("Não Atende");
    let destino = "";

    if (classificacao.includes("Pessoa")) {
      // === PESSOA ATENDEU → aba "Atendeu" ===
      destino = "atendeu";
      const ult = Math.max(abAtendeu.getLastRow(), 1);
      abAtendeu.getRange(ult + 1, 1, 1, 7).setValues([[
        numero,
        dados.operadora || "",
        dados.confianca || 0,
        (dados.transcricao || "").substring(0, 200),
        celular,
        agoraStr,
        tentativa,
      ]]);

    } else {
      // Verificar se deve descartar (inexistente, bloqueado)
      let ehDescarte = false;
      for (const motivo of CONFIG.DESCARTAR) {
        if (classificacao.includes(motivo)) {
          ehDescarte = true;
          break;
        }
      }

      if (ehDescarte) {
        // === DESCARTAR → aba "Descartados" ===
        destino = "descartar";
        const ult = Math.max(abDesc.getLastRow(), 1);
        abDesc.getRange(ult + 1, 1, 1, 6).setValues([[
          numero, dados.operadora || "", classificacaoRaw,
          tentativa, celular, agoraStr,
        ]]);

      } else {
        // Não atendeu / ocupado / caixa postal / fora de área / erro
        // Verificar se ainda tem tentativas
        let regraEncontrada = null;
        for (const [tipo, regra] of Object.entries(CONFIG.RETRY)) {
          if (classificacao.includes(tipo)) {
            regraEncontrada = regra;
            break;
          }
        }

        // Se não encontrou regra específica, usar padrão (3 tentativas, 3h)
        if (!regraEncontrada) {
          regraEncontrada = { max_tentativas: 3, intervalo_min: 180 };
        }

        if (tentativa < regraEncontrada.max_tentativas) {
          // === TENTAR NOVAMENTE ===
          destino = "tentar_novamente";
          const proximaDate = new Date(agora.getTime() + regraEncontrada.intervalo_min * 60 * 1000);
          const proximaStr = proximaDate.toLocaleString("pt-BR");

          const ult = Math.max(abRel.getLastRow(), 1);
          abRel.getRange(ult + 1, 1, 1, 6).setValues([[
            numero, dados.operadora || "", tentativa,
            classificacaoRaw, agoraStr, proximaStr,
          ]]);
        } else {
          // Esgotou tentativas — decidir aba de destino
          // Bloqueado / Fora de Área → "Desligados/Inexistentes"
          // Não Atendeu / Ocupado / Caixa Postal → "Não Atende" (número existe mas não atende)
          const ehDesligado = classificacao.includes("Bloqueado") ||
                              classificacao.includes("Fora de Área") ||
                              classificacao.includes("Fora de Area") ||
                              classificacao.includes("Silêncio Incerto");

          if (ehDesligado) {
            destino = "desligado_inexistente";
            const abDeslig = ss.getSheetByName("Desligados/Inexistentes");
            const ult = Math.max(abDeslig.getLastRow(), 1);
            abDeslig.getRange(ult + 1, 1, 1, 6).setValues([[
              numero, dados.operadora || "", classificacaoRaw,
              tentativa, celular, agoraStr,
            ]]);
          } else {
            destino = "esgotado";
            const ult = Math.max(abEsgotado.getLastRow(), 1);
            abEsgotado.getRange(ult + 1, 1, 1, 6).setValues([[
              numero, dados.operadora || "", tentativa,
              classificacaoRaw, celular, agoraStr,
            ]]);
          }
        }
      }
    }

    // 4. Atualizar contadores
    if (abConf) {
      const totalDiscados = parseInt(abConf.getRange("B3").getValue()) || 0;
      abConf.getRange("B3").setValue(totalDiscados + 1);

      if (destino === "atendeu") {
        const total = parseInt(abConf.getRange("B4").getValue()) || 0;
        abConf.getRange("B4").setValue(total + 1);
      } else {
        const total = parseInt(abConf.getRange("B5").getValue()) || 0;
        abConf.getRange("B5").setValue(total + 1);
      }

      if (destino === "descartar") {
        const total = parseInt(abConf.getRange("B6").getValue()) || 0;
        abConf.getRange("B6").setValue(total + 1);
      }

      if (destino === "esgotado") {
        const total = parseInt(abConf.getRange("B7").getValue()) || 0;
        abConf.getRange("B7").setValue(total + 1);
      }

      abConf.getRange("B9").setValue(agoraStr);
    }

    return {
      erro: false,
      mensagem: "Resultado registrado",
      numero: numero,
      destino: destino,
      tentativa: tentativa,
    };

  } finally {
    lock.releaseLock();
  }
}

// ================================================================
//  REGISTRAR RESULTADOS EM LOTE
// ================================================================

function registrarResultados(dados) {
  const resultados = dados.resultados || [];
  const celular = dados.celular || "desconhecido";

  let registrados = 0;
  for (const r of resultados) {
    r.celular = celular;
    registrarResultado(r);
    registrados++;
  }

  return { erro: false, registrados: registrados };
}

// ================================================================
//  DEVOLVER NÚMEROS
// ================================================================

function devolverNumeros(dados) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const abDisp = ss.getSheetByName("Disponíveis");
    const abAnd = ss.getSheetByName("Em Andamento");

    const numeros = dados.numeros || [];
    let devolvidos = 0;

    for (const num of numeros) {
      const numero = num.toString();
      const dadosAnd = abAnd.getDataRange().getValues();

      for (let i = dadosAnd.length - 1; i >= 1; i--) {
        if (dadosAnd[i][0].toString() === numero) {
          const operadora = dadosAnd[i][1];
          abAnd.deleteRow(i + 1);

          const ultimaDisp = Math.max(abDisp.getLastRow(), 1);
          abDisp.getRange(ultimaDisp + 1, 1, 1, 2).setValues([[numero, operadora]]);
          devolvidos++;
          break;
        }
      }
    }

    return { erro: false, devolvidos: devolvidos };

  } finally {
    lock.releaseLock();
  }
}

// ================================================================
//  STATUS
// ================================================================

function getStatus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const contar = (nome) => {
    const ab = ss.getSheetByName(nome);
    return ab ? Math.max(ab.getLastRow() - 1, 0) : 0;
  };

  const abRes = ss.getSheetByName("Resultados");
  const classificacoes = {};
  const totalRes = contar("Resultados");
  if (totalRes > 0) {
    const dados = abRes.getRange(2, 3, totalRes, 1).getValues();
    for (const row of dados) {
      const cls = row[0] || "?";
      classificacoes[cls] = (classificacoes[cls] || 0) + 1;
    }
  }

  const abAnd = ss.getSheetByName("Em Andamento");
  const celulares = {};
  const totalAnd = contar("Em Andamento");
  if (totalAnd > 0) {
    const dados = abAnd.getRange(2, 3, totalAnd, 1).getValues();
    for (const row of dados) {
      const cel = row[0] || "?";
      celulares[cel] = (celulares[cel] || 0) + 1;
    }
  }

  return {
    erro: false,
    disponiveis: contar("Disponíveis"),
    tentar_novamente: contar("Tentar Novamente"),
    em_andamento: totalAnd,
    atendeu: contar("Atendeu"),
    esgotado: contar("Não Atende"),
    resultados: totalRes,
    descartados: contar("Descartados"),
    classificacoes: classificacoes,
    celulares_ativos: celulares,
  };
}

// ================================================================
//  LIMPEZA — Devolver números com timeout
// ================================================================

function limparAndamento() {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const abAnd = ss.getSheetByName("Em Andamento");
    const abDisp = ss.getSheetByName("Disponíveis");

    const dados = abAnd.getDataRange().getValues();
    const agora = new Date();
    const timeoutMs = CONFIG.TIMEOUT_ANDAMENTO_MIN * 60 * 1000;
    let devolvidos = 0;

    for (let i = dados.length - 1; i >= 1; i--) {
      const horaStr = dados[i][3];
      if (!horaStr) continue;

      const hora = new Date(horaStr);
      if (agora - hora > timeoutMs) {
        const ultimaDisp = Math.max(abDisp.getLastRow(), 1);
        abDisp.getRange(ultimaDisp + 1, 1, 1, 2).setValues([[dados[i][0], dados[i][1]]]);
        abAnd.deleteRow(i + 1);
        devolvidos++;
      }
    }

    return { devolvidos: devolvidos };

  } finally {
    lock.releaseLock();
  }
}

// ================================================================
//  TRIGGERS E MENU
// ================================================================

function configurarTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === "limparAndamento") {
      ScriptApp.deleteTrigger(trigger);
    }
  }

  ScriptApp.newTrigger("limparAndamento")
    .timeBased()
    .everyMinutes(5)
    .create();

  SpreadsheetApp.getUi().alert("✅ Limpeza automática configurada (a cada 5 minutos)");
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("📞 Validador")
    .addItem("Inicializar Sistema", "inicializar")
    .addItem("Gerar +500 Números", "gerarMais")
    .addItem("Limpar Em Andamento (timeout)", "limparAndamento")
    .addItem("Configurar Limpeza Automática", "configurarTrigger")
    .addItem("Ver Status", "mostrarStatus")
    .addToUi();
}

function gerarMais() {
  const gerados = gerarNumeros(CONFIG.LOTE_GERACAO);
  SpreadsheetApp.getUi().alert("✅ " + gerados + " números gerados!");
}

function mostrarStatus() {
  const s = getStatus();
  SpreadsheetApp.getUi().alert(
    "📊 Status do Sistema\n\n" +
    "Disponíveis: " + s.disponiveis + "\n" +
    "Tentar Novamente: " + s.tentar_novamente + "\n" +
    "Em Andamento: " + s.em_andamento + "\n" +
    "Atendeu: " + s.atendeu + "\n" +
    "Esgotado (3x): " + s.esgotado + "\n" +
    "Descartados: " + s.descartados + "\n" +
    "Histórico total: " + s.resultados + "\n\n" +
    "Classificações:\n" +
    Object.entries(s.classificacoes).map(([k, v]) => "  " + k + ": " + v).join("\n")
  );
}
