# Esquemas de dados suportados

Consulte este arquivo **quando a pasta de dados não seguir os nomes do Olist** ou quando o usuário perguntar por que um campo tem outro nome. O script detecta o esquema sozinho (`--esquema auto`) a partir dos arquivos presentes na pasta.

## Por que existe uma camada de esquema

A lista pede a base Olist (`pedido.csv`, `cliente.csv`, …), mas os arquivos disponíveis no momento da construção eram da **Garden Shop** (`orders.csv`, `customers.csv`, …). Para não amarrar o código a uma base só, as análises usam **nomes lógicos** (pedido, cliente, situação, data, UF, valor do item). O arquivo `scripts/esquemas.py` diz a qual arquivo e coluna cada nome lógico corresponde em cada base. Para trocar de base, troque a pasta (`--dados`): **as regras e o código das análises não mudam.**

## Mapeamento

| Nome lógico | Olist (`--esquema olist`) | Garden Shop (`--esquema garden_shop`) |
|---|---|---|
| Arquivo de pedidos | `pedido.csv` | `orders.csv` |
| Id do pedido | `idPedido` | `order_id` |
| Id do cliente no pedido | `idCliente` | `customer_id` |
| Situação | `descSituacao` | `status` |
| Situação "entregue" | `delivered` | `shipped` ⚠️ |
| Data de referência | `dtPedido` | `order_date` |
| Arquivo de clientes | `cliente.csv` | `customers.csv` |
| UF do cliente | `descUF` (UF brasileira) | `state` (estado dos EUA) ⚠️ |
| Arquivo de itens | `item_pedido.csv` | `order_items.csv` |
| Valor do item (sem frete) | `vlPreco` (1 linha = 1 unidade) | `unit_price × quantity` ⚠️ |
| Frete do item | `vlFrete` | não existe ⚠️ |

## Diferenças que o agente deve declarar ao usar a Garden Shop

1. **Não existe o status "delivered".** O mais próximo é `shipped` (pedido enviado). Os status são `shipped`, `pending`, `processing` e `cancelled`. A resposta deve dizer "pedidos enviados (`shipped`), usados como equivalente de entregues".
2. **`state` são estados dos EUA** (PA, CA, OH…), não UFs brasileiras. Chame de "estado" na resposta.
3. **Itens têm quantidade:** o valor do item é `unit_price × quantity`. No Olist cada linha já é uma unidade.
4. **Não há frete nem pagamentos:** o ticket já é "sem frete" por construção. Perguntas sobre frete ou pagamento não podem ser respondidas.
5. Datas em `AAAA-MM-DD`, de jan/2024 a jun/2024.

## Detecção automática

| Arquivo presente na pasta | Esquema escolhido |
|---|---|
| `pedido.csv` | `olist` |
| `orders.csv` | `garden_shop` |
| nenhum dos dois | erro com a lista de arquivos encontrados |

Separador (`,` `;` ou tabulação) e codificação (UTF-8 ou Latin-1) também são detectados, porque exportações do Olist em português costumam vir com `;`.
