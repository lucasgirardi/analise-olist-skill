# Regras de negócio e métricas

Consulte este arquivo **antes de calcular qualquer métrica** e sempre que o usuário pedir uma variação (outro período, outra UF, outro status). Os nomes de campo seguem o esquema Olist. Para a Garden Shop, veja as equivalências em [esquemas-de-dados.md](esquemas-de-dados.md).

## 1. Seleção de pedidos (vale para todas as métricas)

| Regra | Definição |
|---|---|
| R1. Pedido entregue | `pedido.descSituacao = "delivered"` (sem diferenciar maiúsculas e ignorando espaços). Outros status (`shipped`, `canceled`, `invoiced`…) ficam de fora, salvo pedido explícito do usuário (`--situacao`) |
| R2. Data de referência | `pedido.dtPedido`, a data em que o pedido foi feito. Não use `dtAprovado` nem `dtEntregue` para o período |
| R3. Unidade de contagem | `idPedido` **distinto**. Nunca conte linhas depois de um join |
| R4. Período | `--inicio` e `--fim` são **inclusivos**, comparados pela data (horário ignorado). `--fim 2017-03-31` inclui um pedido de 2017-03-31 23:59:59. Também é aceito `AAAA-MM`: o início vira o 1º dia do mês e o fim, o último dia. Sem período, vale toda a base |
| R5. Filtro de UF | `cliente.descUF` do cliente do pedido (join por `idCliente`). Aceita uma ou mais UFs (`--uf SP,RJ`). Não é a UF do vendedor |

## 2. Métricas

### M1. Pedidos entregues por mês
- **Fórmula:** `COUNT(DISTINCT idPedido)` por `AAAA-MM` de `dtPedido`, após R1, R4 e R5.
- **Meses sem pedidos dentro do período aparecem com 0** (contagem sem pedidos é zero).
- Também informar o total do período.

### M2. Ranking das UFs dos clientes com mais pedidos entregues
- **Fórmula:** `COUNT(DISTINCT idPedido)` por `cliente.descUF`, após R1 e R4 (e R5, se pedido), em ordem decrescente. Padrão: as 5 primeiras (`--top`).
- **Desempate:** maior contagem primeiro e, em caso de empate, a UF em ordem alfabética. Se houver empate na última posição do ranking, **avise** que outras UFs têm a mesma contagem.
- Se existirem menos UFs que o `--top`, mostre as que existem e diga isso.
- Pedidos sem cliente correspondente ou com UF vazia **não entram no ranking** e são informados na cobertura.

### M3. Ticket médio do preço dos itens por pedido entregue (sem frete)
- **Fórmula:** `Σ item_pedido.vlPreco` dos itens dos pedidos selecionados ÷ `COUNT(DISTINCT idPedido)` selecionados.
- **Sem frete:** `vlFrete` **não** entra. **Não use `pagamento_pedido.vlPagamento`**: ele inclui frete e pode estar dividido em várias linhas (vários pagamentos).
- Cada linha de `item_pedido` é **uma unidade vendida** (o Olist repete a linha para itens iguais, com `idPedidoItem` = 1, 2, …). Some `vlPreco` de todas as linhas. Não existe coluna de quantidade.
- **Cobertura:** se algum pedido selecionado não tiver itens, ele entra no denominador com 0 de valor (conforme o enunciado: divide-se pelo número de pedidos selecionados). Informe quantos são e mostre também, como referência, o ticket só dos pedidos com itens.
- **Sem pedidos selecionados:** o resultado é **"não aplicável"**, não 0.
- Informe, como contexto separado e sem somar ao ticket, o frete total dos mesmos pedidos.

## 3. Dados ausentes, inválidos e sem correspondência

| Situação | Tratamento | Onde aparece |
|---|---|---|
| `dtPedido` vazia ou inválida (ex.: `2017-13-45`) | Pedido **excluído** das análises com período (não há mês para atribuir) | Contagem em "Qualidade dos dados" |
| `descSituacao` vazia | Não é "delivered": excluído | Diagnóstico |
| `idPedido` repetido em `pedido.csv` | Contado uma vez (distinto) | Diagnóstico (alerta) |
| Pedido com `idCliente` sem cliente | Entra em M1 e M3 (sem filtro de UF). Fica fora de M2 e de qualquer filtro de UF | Cobertura de M2 |
| Cliente com UF vazia | Fica fora de M2 e de filtros de UF | Cobertura de M2 |
| Item com `idPedido` inexistente em `pedido.csv` | Ignorado (não pertence a nenhum pedido selecionado) | Diagnóstico |
| Item com `vlPreco` vazio ou não numérico | Excluído da soma | Cobertura de M3 |
| Pedido selecionado sem itens | Entra no denominador de M3 com valor 0 | Cobertura de M3 |

Arquivos originais **nunca** são alterados: o script só lê.

## 4. Perguntas que a base não responde

Antes de responder, confira se os campos necessários existem ([relacionamentos.md](relacionamentos.md) e o diagnóstico do script). Exemplos fora do alcance:

- **Lucro e margem:** não há custo dos produtos no Olist.
- **Estoque:** não há tabela de estoque.
- **Motivo de cancelamento:** não há campo de motivo.
- **Dados pessoais do cliente** (nome, e-mail): não existem na base e não devem ser buscados.
- **Na Garden Shop:** frete e pagamentos não existem, e `state` são estados dos EUA, não UFs brasileiras.

Nesses casos, diga o que falta, sugira a pergunta mais próxima que a base responde e **não estime números**.
