# analise-olist: skill de copiloto de analytics

Autor: **Lucas Girardi** · Lista 03 de IA Generativa

Skill para o **Claude Code** que transforma o agente num copiloto de analytics da base Olist. O usuário pergunta em linguagem natural ("quantos pedidos entregues por mês?", "e só em SP?") e o agente segue um procedimento fixo: entende a pergunta, consulta as regras, executa `scripts/analise.py` sobre os CSVs e responde com métrica, filtros, arquivos usados, comando executado, saída e limitações.

```
.claude/skills/analise-olist/
├── SKILL.md                      # instruções da skill (quando usar, entradas, procedimento, saída, limites)
├── references/
│   ├── regras-de-negocio.md      # regras R1–R5, métricas M1–M3, ausentes/inválidos/órfãos
│   ├── relacionamentos.md        # tabelas, chaves, cardinalidade, como não multiplicar valores
│   └── esquemas-de-dados.md      # mapeamento Olist × Garden Shop
└── scripts/
    ├── analise.py                # análises reutilizáveis (CLI)
    ├── esquemas.py               # nomes de arquivos/colunas por base
    └── requirements.txt
tests/                            # 32 testes + recorte Olist + cálculo independente
saidas/                           # saídas das análises e verificações executadas
dados/garden_shop/                # base disponível na construção (cópia sem alteração)
```

## 1. Instalação

```bash
git clone https://github.com/lucasgirardi/analise-olist-skill.git
cd analise-olist-skill
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r .claude/skills/analise-olist/scripts/requirements.txt
```

## 2. Como informar a pasta dos dados

O script **não tem caminho fixo**. Informe a pasta que contém os CSVs de uma destas formas:

```bash
# a) por parâmetro, a cada execução
python .claude/skills/analise-olist/scripts/analise.py pedidos_mes --dados /caminho/para/olist

# b) por variável de ambiente, uma vez por sessão do terminal
export ANALISE_OLIST_DADOS=/caminho/para/olist          # Windows (PowerShell): $env:ANALISE_OLIST_DADOS="C:\caminho\olist"
python .claude/skills/analise-olist/scripts/analise.py pedidos_mes
```

A pasta do Olist precisa ter pelo menos `pedido.csv`, `cliente.csv` e `item_pedido.csv`. Os demais arquivos do enunciado podem estar lá, mas não entram nas três análises. Uma sugestão é colocá-los em `dados/olist/` (essa pasta é ignorada pelo Git, porque a base completa não vai para o repositório). Separador (`,` `;` ou tab) e codificação (UTF-8 ou Latin-1) são detectados automaticamente. O script **só lê** os arquivos.

Para conferir se a pasta está correta, rode o diagnóstico:

```bash
python .claude/skills/analise-olist/scripts/analise.py diagnostico --dados /caminho/para/olist
```

> **Sobre a base disponível:** durante a construção, os arquivos recebidos foram os da Garden Shop, e não os do Olist. A skill foi feita com uma camada de esquema (`scripts/esquemas.py`): ela roda hoje em `dados/garden_shop/`, com as equivalências documentadas em `references/esquemas-de-dados.md`, e roda no Olist assim que a pasta com `pedido.csv`… for informada. Os nomes de campo do Olist vêm do enunciado e de consultas SQL reais sobre o mesmo esquema. **Confira-os com o `dicionario.xlsx` do professor.** Se algo divergir, ajuste só `esquemas.py`.

## 3. Como usar a skill no Claude Code

1. Abra o Claude Code **na raiz deste repositório** (`claude`). A skill é reconhecida em `.claude/skills/analise-olist/`.
2. Confira se ela foi carregada: pergunte "quais skills você tem disponíveis?" ou use `/skills`. `analise-olist` deve aparecer.
3. Diga onde estão os dados e pergunte. Exemplos:
   - "Os CSVs do Olist estão em `dados/olist`. Quantos pedidos entregues tivemos por mês?"
   - "Quais as 5 UFs dos clientes com mais pedidos entregues?"
   - "Qual o ticket médio dos itens por pedido entregue, sem frete?"
   - Continuação: "E se considerarmos só o 1º semestre de 2018?" ou "Agora só SP."
4. O agente executa o script e responde com métrica, filtros, arquivos, comando e saída.

No Codex, copie a pasta `analise-olist` para `.agents/skills/analise-olist/`. O conteúdo é o mesmo.

## 4. Uso direto pelo terminal

| Análise | Comando |
|---|---|
| Pedidos entregues por mês | `python .claude/skills/analise-olist/scripts/analise.py pedidos_mes --dados PASTA [--inicio 2017-01] [--fim 2017-12] [--uf SP]` |
| Top UFs | `python .claude/skills/analise-olist/scripts/analise.py top_ufs --dados PASTA [--top 5] [filtros]` |
| Ticket médio sem frete | `python .claude/skills/analise-olist/scripts/analise.py ticket_medio --dados PASTA [filtros]` |
| Diagnóstico | `python .claude/skills/analise-olist/scripts/analise.py diagnostico --dados PASTA` |

Opções: `--inicio`/`--fim` (inclusivos, `AAAA-MM-DD` ou `AAAA-MM`), `--uf SP,RJ`, `--top N`, `--situacao`, `--esquema auto|olist|garden_shop`, `--json` e `--saida ARQUIVO` (fora da pasta de dados).

## 5. Verificação

```bash
pytest            # 32 testes
```

Os testes cobrem:
- as três análises no **recorte** `tests/fixtures/olist_recorte/` (formato real do Olist), com resultados calculados **à mão** (docstring de `tests/test_analise.py`) e por **código independente** (`tests/calculo_independente.py`, só biblioteca padrão);
- bordas do período, período sem dados (0 e "não aplicável"), pedido sem itens, datas inválidas, chaves órfãs, empate no ranking, pagamentos que não multiplicam valores, separador `;`;
- a base Garden Shop, conferida por contagem direta;
- a linha de comando, a variável de ambiente, os impedimentos e a garantia de que os arquivos de dados não mudam.

As saídas das análises e as verificações executadas estão em [`saidas/`](saidas/).
