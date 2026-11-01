---
name: analise-olist
description: "Copiloto de analytics da base Olist (pedido.csv, cliente.csv, item_pedido.csv...). Use quando o usuário pedir, em linguagem natural, contagens de pedidos entregues por mês, ranking das UFs dos clientes com mais pedidos entregues, ticket médio do preço dos itens sem frete, ou continuações dessas análises (outro período, outra UF, top N), ou quando quiser diagnosticar os arquivos dessa base. Executa scripts/analise.py e responde com métrica, filtros, arquivos, comando e saída."
---

# analise-olist: copiloto de analytics do marketplace Olist

Autor: **Lucas Girardi**

## 1. Tarefa e resultado esperado

Responda perguntas de negócio sobre pedidos, vendas e clientes do Olist para a equipe do marketplace. Para isso, **execute código Python sobre os CSVs informados** e produza uma resposta verificável: métrica, filtros, arquivos usados, código, comando, saída e limitações.

- **Objetivo:** permitir que quem não programa investigue pedidos entregues, a distribuição por UF e o ticket médio, mudando o período e os filtros pela conversa.
- **Incluído:** (M1) pedidos entregues por mês; (M2) ranking das UFs dos clientes com mais pedidos entregues; (M3) ticket médio do preço dos itens por pedido entregue, sem frete; diagnóstico da base; continuações com outro período, outra UF, outro tamanho de ranking ou outra situação de pedido.
- **Fora do escopo:** dashboards, previsões, lucro e margem (não há custo), estoque, dados pessoais de clientes, alterar os arquivos de dados, métricas novas sem combinar a definição com o usuário.

## 2. Quando usar

Use esta skill quando o pedido envolver **pedidos, clientes por UF, itens ou ticket médio da base Olist** (ou de uma pasta de dados no esquema suportado) e exigir um número calculado a partir dos arquivos.

Não use quando a pergunta for conceitual ("o que é ticket médio?"), quando não houver pasta de dados a consultar, ou quando o pedido for sobre outra base sem esquema mapeado em [references/esquemas-de-dados.md](references/esquemas-de-dados.md). Nesse último caso, explique o que falta.

## 3. Entradas

| Entrada | Formato ou origem | Obrigatória | Como usar ou validar |
|---|---|---|---|
| Pergunta | Texto do usuário | Sim | Traduza para uma métrica (M1, M2 ou M3), filtros e período. Se não couber em nenhuma, siga a seção 6, passo 3 |
| Pasta dos dados | `--dados CAMINHO` ou variável de ambiente `ANALISE_OLIST_DADOS` | Sim | Deve conter `pedido.csv`, `cliente.csv` e `item_pedido.csv` (Olist). Confira com `diagnostico` antes da primeira análise |
| Período | `--inicio` / `--fim` em `AAAA-MM-DD` ou `AAAA-MM` | Não | Padrão: toda a base. Ambos **inclusivos**. Converta expressões como "1º trimestre de 2018" em datas explícitas e diga quais usou |
| UF do cliente | `--uf SP` ou `--uf SP,RJ` | Não | Sigla de 2 letras de `cliente.descUF` |
| Tamanho do ranking | `--top N` | Não | Padrão 5 (M2) |
| Situação | `--situacao` | Não | Padrão `delivered`. Só mude se o usuário pedir explicitamente outro status |

**Entrada ausente:** se o usuário não informou a pasta e `ANALISE_OLIST_DADOS` não existe, **pergunte o caminho** e não invente um. Se a pergunta for ambígua de um jeito que muda o número (ex.: "vendas" = pedidos, itens ou valor?), pergunte, ou aplique o padrão da seção 5 e **diga qual padrão usou**.

**Entrada inválida:** o script responde com `Impedimento: …` e código de saída 2 (pasta inexistente, arquivo ou coluna ausente, data em formato errado, início depois do fim). Repasse a mensagem ao usuário e diga como corrigir.

## 4. Saída

- **Entrega:** a resposta na conversa, com estes blocos, nesta ordem:
  1. **Resposta direta** em uma ou duas frases, com o número principal.
  2. **Métrica** (a fórmula, como o script imprime).
  3. **Filtros:** situação, período com a convenção de datas, UF e top N.
  4. **Arquivos utilizados.**
  5. **Execução:** o caminho do script, o **comando exato** e a **saída relevante** (a tabela ou os valores).
  6. **Qualidade e cobertura:** pedidos excluídos por data inválida, pedidos sem itens, órfãos, empates.
  7. **Limitações** ou sugestão de próxima pergunta, se houver.
- **Formato:** texto com tabela em Markdown. Valores com vírgula decimal, na moeda que o script imprimir (R$ no Olist). Meses como `AAAA-MM`.
- **Destino:** apenas a conversa. Grave arquivo só se o usuário pedir (`--saida`, **fora** da pasta de dados, por exemplo `saidas/`).
- **Evidências:** o comando e a saída do script. **Nenhum número pode aparecer como "calculado" sem uma execução nesta conversa que o sustente.**

## 5. Regras específicas da tarefa

Antes de calcular, leia [references/regras-de-negocio.md](references/regras-de-negocio.md). Resumo das regras que mais mudam o resultado:

1. **Pedido entregue** = `descSituacao = delivered`. **Data de referência** = `dtPedido`. Conte **`idPedido` distintos**.
2. **Período inclusivo** nas duas pontas, comparado pela data (horário ignorado). `AAAA-MM` vale o mês inteiro.
3. **Ranking de UF:** pedido ⨝ cliente por `idCliente`, usando `descUF`. Pedidos sem cliente correspondente ficam fora do ranking e são informados.
4. **Ticket médio** = Σ `vlPreco` dos itens dos pedidos selecionados ÷ nº de pedidos distintos selecionados. **Sem `vlFrete` e sem `vlPagamento`.** Pedidos sem itens entram no denominador; informe quantos são.
5. **Sem pedidos:** contagem = 0; média = **não aplicável**.
6. **Nunca combine itens com pagamentos:** isso multiplica valores. As tabelas, chaves e cardinalidades estão em [references/relacionamentos.md](references/relacionamentos.md).

## 6. Procedimento

### Compreender o pedido

1. Identifique a métrica (M1, M2 ou M3), o período, as UFs, o top N e se o pedido é uma **continuação** (ex.: "e só em SP?"). Numa continuação, **mantenha os filtros anteriores e altere apenas o que foi pedido**, dizendo o que mudou.
2. Confirme a pasta dos dados. Na primeira análise da conversa, rode o diagnóstico para conferir arquivos, colunas, período disponível e problemas de chave:
   `python .claude/skills/analise-olist/scripts/analise.py diagnostico --dados <PASTA>`
3. Se a pergunta exigir um campo que não existe (lucro, custo, estoque, motivo de cancelamento) ou uma definição não acordada, **não calcule**. Diga o que falta (com base em [references/relacionamentos.md](references/relacionamentos.md) e no diagnóstico) e ofereça a pergunta mais próxima que a base responde.

### Executar a tarefa

4. Rode o script com os parâmetros traduzidos. Os caminhos são relativos à raiz do repositório:
   - M1: `python .claude/skills/analise-olist/scripts/analise.py pedidos_mes --dados <PASTA> [--inicio …] [--fim …] [--uf …]`
   - M2: `python .claude/skills/analise-olist/scripts/analise.py top_ufs --dados <PASTA> [--top 5] [filtros]`
   - M3: `python .claude/skills/analise-olist/scripts/analise.py ticket_medio --dados <PASTA> [filtros]`
5. Para variações que o script já aceita, **reutilize-o**; não reescreva o cálculo. Só escreva código novo se o pedido sair dessas três métricas e o usuário aceitar a definição. Nesse caso, siga as mesmas regras (distintos, agregar antes de combinar), mostre o código e execute-o.
6. Se o script falhar, leia a mensagem de `Impedimento`, corrija o parâmetro se for um erro seu, ou explique ao usuário o que impede a análise. **Não substitua a execução por uma estimativa.**

### Conferir o resultado

7. Confira a coerência interna: a soma dos meses (M1) = total; o ranking (M2) não passa do total de pedidos; em M3, `ticket × pedidos ≈ soma dos itens`.
8. Leia a seção "Qualidade e cobertura" da saída. Se houver exclusões (datas inválidas, órfãos, pedidos sem itens, empate no corte), **leve-as para a resposta**.
9. Se um número parecer estranho (ex.: zero num período que deveria ter dados), confira o período disponível no diagnóstico e os filtros aplicados antes de responder. Se não conseguir resolver, informe o que ficou sem verificar.

### Entregar

10. Responda no formato da seção 4.
11. Informe as decisões tomadas (padrões aplicados, interpretação do período) e as limitações. Se a pasta usar o esquema Garden Shop, declare as equivalências ([references/esquemas-de-dados.md](references/esquemas-de-dados.md)).

## 7. Recursos de apoio

- **Referências:**
  - [references/regras-de-negocio.md](references/regras-de-negocio.md): consulte antes de qualquer cálculo e ao interpretar continuações.
  - [references/relacionamentos.md](references/relacionamentos.md): consulte ao escolher arquivos e combinar tabelas, e para decidir se uma pergunta é respondível.
  - [references/esquemas-de-dados.md](references/esquemas-de-dados.md): consulte quando a pasta não tiver `pedido.csv` ou o usuário perguntar sobre nomes de campos.
- **Scripts:**
  - [scripts/analise.py](scripts/analise.py): execute para todas as análises e o diagnóstico (`--help` lista as opções).
  - [scripts/esquemas.py](scripts/esquemas.py): edite apenas para mapear uma base com outros nomes de arquivo ou coluna.

Os caminhos dos recursos são relativos à pasta da skill. A pasta dos dados **não** fica na skill: o usuário a informa com `--dados` ou com `ANALISE_OLIST_DADOS`, por isso nada depende da máquina do autor.

## 8. Ambiente e ferramentas

- **Ferramentas necessárias:** leitura de arquivos e execução de comandos no terminal (Bash).
- **Dependências:** Python 3.10+ e pandas (`pip install -r .claude/skills/analise-olist/scripts/requirements.txt`).
- **Execução:** `python .claude/skills/analise-olist/scripts/analise.py <analise> --dados <PASTA> [opções]`. Use `--json` para conferências automáticas.
- **Se o recurso não estiver disponível:** sem terminal, sem Python ou pandas, ou sem acesso à pasta, **diga que não pode executar** e mostre o comando que o usuário pode rodar. Não apresente valores como calculados.

Não descreva uma operação como executada quando ela tiver sido apenas proposta.

## 9. Limites de atuação

- **Preservar:** os arquivos da pasta de dados (somente leitura). O script recusa `--saida` dentro dela.
- **Alterações previstas:** nenhuma nos dados. Arquivos de saída apenas quando pedidos, em `saidas/` ou em outro local indicado pelo usuário.
- **Decisões a esclarecer:** definição de uma métrica nova; uso de outro status que não `delivered`; inclusão de frete ou de `vlPagamento`. Pergunte antes.

## 10. Critérios de conclusão

Considere a tarefa concluída quando:

- o número apresentado vier de uma execução do script (ou de código mostrado e executado) nesta conversa;
- a resposta trouxer métrica, filtros com a convenção de datas, arquivos, comando e saída relevante;
- as exclusões e a cobertura relatadas pelo script tiverem sido comunicadas;
- numa continuação, o que mudou em relação à resposta anterior estiver explícito.

Se um critério não puder ser verificado, informe essa limitação sem apresentá-lo como atendido.

## 11. Exemplos de uso

### Pedido pertinente

> "Quantos pedidos entregues tivemos por mês em 2017?"

**Resultado esperado:** execução de `pedidos_mes --inicio 2017-01 --fim 2017-12`, uma tabela com os 12 meses (meses sem pedidos = 0), o total, "Período: 2017-01-01 a 2017-12-31 (datas inclusivas)", os arquivos (`pedido.csv`), o comando e as exclusões por data inválida, se houver.

### Continuação

> "E só para clientes de SP?"

**Resultado esperado:** o mesmo período anterior, agora com `--uf SP`. A resposta diz que só a UF mudou e acrescenta `cliente.csv` aos arquivos.

### Período sem dados

> "Qual o ticket médio em janeiro de 2030?"

**Comportamento esperado:** executar mesmo assim e responder "não aplicável: nenhum pedido entregue no período", sem responder "R$ 0,00".

### Entrada ausente ou inválida

> "Rode o ranking de UFs." (sem pasta informada nem variável de ambiente)

**Comportamento esperado:** perguntar onde estão os CSVs do Olist. Se o caminho estiver errado, repassar o `Impedimento` do script.

### Pedido fora do escopo

> "Qual foi o lucro por categoria?"

**Comportamento esperado:** explicar que a base não tem custo dos produtos, então não há como calcular lucro, e sugerir a alternativa mais próxima (valor de itens vendidos), sem estimar números.
