# Saídas e verificações: skill analise-olist

Autor: **Lucas Girardi** · executado em 2026-11-01 (Python 3.13, pandas 3.0)

Todos os arquivos `.txt` desta pasta foram gerados pelo próprio script, com `--saida`. Cada um traz no fim o **comando** que o produziu. Para reproduzir, rode o mesmo comando na raiz do repositório.

## 1. Bases usadas

| Base | Pasta | Observação |
|---|---|---|
| Garden Shop (completa) | `dados/garden_shop/` | Arquivos recebidos durante a construção. Esquema `garden_shop`: `shipped` ≈ `delivered`, `state` = estado dos EUA, sem frete |
| Recorte Olist | `tests/fixtures/olist_recorte/` | 12 pedidos no **formato real do Olist** (nomes do enunciado), montados para provocar cada caso de borda |

A base Olist completa não estava disponível durante a construção. Com ela, basta trocar `--dados` (ver README §2).

## 2. As três perguntas e as continuações

| # | Pergunta | Arquivo | Resultado |
|---|---|---|---|
| 1 | Pedidos entregues por mês | `01_pedidos_mes_garden_shop.txt` | jan 3 · fev 3 · mar 4 · abr 2 · mai 2 · jun 3 · total 17 |
| 2 | Top 5 UFs/estados com mais pedidos entregues | `02_top_ufs_garden_shop.txt` | PA 5 · CA 4 · FL 2 · OR 2 · TX 2 |
| 3 | Ticket médio dos itens sem frete | `03_ticket_medio_garden_shop.txt` | US$ 52,09 (885,50 ÷ 17) |
| 4 | **Continuação:** "e só em mar–abr/2024?" | `04_continuacao_ticket_mar_abr_2024.txt` | US$ 53,83 (323,00 ÷ 6) |
| 5 | **Continuação:** "pedidos por mês só do estado PA" | `05_continuacao_pedidos_mes_estado_PA.txt` | jan 1 · fev 0 · mar 2 · abr 1 · mai 1 · total 5 |
| 1–3 no Olist | Mesmas perguntas no recorte | `11_…`, `12_…`, `13_…` | Ver seção 3 |
| Continuações no Olist | fev–mar/2017 e UF = SP | `14_…`, `15_…` | R$ 42,50 · SP: 2/0/1 (total 3) |

## 3. Duas análises conferidas com resultado calculado de forma independente (recorte Olist)

Os resultados esperados foram calculados **à mão**, linha a linha (tabela na docstring de `tests/test_analise.py`), e **por um segundo código** que não usa o script nem o pandas (`tests/calculo_independente.py`, só `csv` e `datetime`).

| Análise | Esperado (à mão) | Cálculo independente | Script | Situação |
|---|---|---|---|---|
| M1 pedidos por mês | 2017-01: 2 · 2017-02: 2 · 2017-03: 4 | igual | igual (`11_…`) | ✅ |
| M3 ticket médio, toda a base | (200+50+80+50+60+0+40+25) ÷ 8 = **R$ 63,13** | 63,125 | R$ 63,13 (`13_…`) | ✅ |
| M3 ticket fev–mar/2017 | (80+50+60+0+40+25) ÷ 6 = **R$ 42,50** | 42,50 | R$ 42,50 (`14_…`) | ✅ |
| M2 ranking (extra) | SP 3 · RJ 2 · MG 1 · PR 1 | — | igual (`12_…`) | ✅ |

O que o recorte comprova:
- **Cancelado e `shipped`** ficam fora (p04, p06).
- **Bordas do período:** p02 em 31/01 23:59:59 entra em janeiro; p03 em 01/02 00:00 entra em fevereiro.
- **Data inválida (p09) e ausente (p12):** excluídas e informadas.
- **Pedido sem itens (p08):** entra no denominador do ticket, com cobertura informada ("1 de 8"). Ticket só dos pedidos com itens: R$ 72,14.
- **Cliente sem correspondência (p10):** entra em M1 e M3, fica fora do ranking e é informado.
- **Pedido com 2 itens e 2 pagamentos (p01):** soma R$ 200, e não R$ 400. O teste `test_m3_pagamentos_nao_multiplicam` confirma.
- **Frete** é mostrado à parte (R$ 50,50) e não entra no ticket.

## 4. Período sem dados

| Caso | Arquivo | Resultado |
|---|---|---|
| Pedidos por mês, jan–mar/2025 (Garden Shop) | `06_…` | 2025-01: 0 · 2025-02: 0 · 2025-03: 0 · total **0** |
| Ticket médio, jan–mar/2025 (Garden Shop) | `07_…` | **não aplicável** (nenhum pedido selecionado) |
| Ticket médio, jan–jun/2018 (recorte Olist) | `16_…` | **não aplicável** |

## 5. Pergunta que a base não permite responder

| Pergunta | Base | Evidência | Resposta correta da skill |
|---|---|---|---|
| "Qual o frete médio por pedido entregue?" | Garden Shop | `00_diagnostico_garden_shop.txt`, seção "Colunas disponíveis": nenhum arquivo tem campo de frete | Não é possível: a base não registra frete. O mais próximo é o ticket médio dos itens (já sem frete) |
| "Qual foi o lucro por categoria?" | Olist | `10_olist_recorte_diagnostico.txt` e `references/relacionamentos.md`: não há custo do produto (só `vlPreco`, `vlFrete`, `vlPagamento`) | Não é possível: sem custo, não há lucro nem margem. Alternativa: valor de itens vendidos por categoria (exige `produto.csv`, fora das três análises atuais; pedir confirmação) |

A demonstração na conversa com o agente está no print da entrega.

## 6. Impedimentos (falta de acesso ou entrada inválida)

`17_impedimentos.txt`: pasta inexistente, data em formato errado e ausência de `--dados` e de `ANALISE_OLIST_DADOS`. Nos três casos o script explica o problema e sai com código 2, sem mostrar números.

## 7. Testes automatizados

`90_pytest.txt`: **33 testes passando**. Comando: `pytest` na raiz do repositório.

## 8. Revisão do que a IA gerou

Decisões e código revisados durante a construção, com o registro nos PRs:
- **Arredondamento:** a 1ª versão mostrava R$ 63,125 como "63,12" (arredondamento bancário do Python). Foi trocado para arredondamento comercial (63,13), com teste.
- **Pergunta sem resposta:** a 1ª versão do diagnóstico não listava todas as colunas, então o agente não teria evidência para dizer que um campo não existe. Foi incluída a seção "Colunas disponíveis", com teste.
- **Denominador do ticket:** seguimos o enunciado (pedidos selecionados, incluindo os sem itens) e mostramos, como referência, o ticket dos pedidos com itens. A divergência fica sempre visível na resposta.
- **Base recebida diferente da pedida:** em vez de forçar nomes do Olist sobre a Garden Shop, foi criada a camada de esquema, com as equivalências declaradas em toda resposta.
