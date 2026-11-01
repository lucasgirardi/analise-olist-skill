# Tabelas, chaves e relacionamentos (Olist)

Consulte este arquivo **ao decidir quais arquivos ler e como combiná-los**, e sempre que uma pergunta envolver mais de uma tabela.

> Fonte dos nomes: o enunciado da Lista 03 e as consultas SQL do projeto `ativacao-olist-2025` (`silver.olist.*`), que usam o mesmo esquema. **Confira com o `dicionario.xlsx` do professor** quando ele estiver disponível na pasta de dados. Se algum nome divergir, ajuste apenas o esquema em `scripts/esquemas.py` e registre a mudança aqui.

## 1. Arquivos e campos usados pelas análises

| Arquivo | Um registro representa | Chave | Campos usados |
|---|---|---|---|
| `pedido.csv` | um pedido | `idPedido` | `idCliente` (FK), `descSituacao`, `dtPedido` |
| `cliente.csv` | um cliente **de um pedido** (`idCliente`) | `idCliente` | `descUF` (também existe `idClienteUnico`, a pessoa) |
| `item_pedido.csv` | **uma unidade** de produto num pedido | `idPedido` + `idPedidoItem` | `vlPreco`, `vlFrete` |
| `pagamento_pedido.csv` | um pagamento de um pedido | `idPedido` + sequência | `vlPagamento` (**não usado** nas métricas atuais) |
| `produto.csv`, `vendedor.csv`, `avaliacao_pedido.csv` | produto, vendedor, avaliação | `idProduto`, `idVendedor`, `idAvaliacao` | **não usados** nas três análises |

## 2. Cardinalidade e risco de duplicação

```
cliente 1 ── N pedido 1 ── N item_pedido
                  │ 1
                  └──── N pagamento_pedido
```

- **pedido → item_pedido é 1:N:** um pedido com 3 itens vira 3 linhas no join. Contar linhas depois do join infla a contagem de pedidos. **Conte `idPedido` distinto.**
- **pedido → pagamento_pedido é 1:N:** um pedido pago com cartão + voucher tem 2 linhas.
- **Nunca faça join de `item_pedido` com `pagamento_pedido`:** cada item seria repetido para cada pagamento, e cada pagamento para cada item. A soma de `vlPreco` dobraria num pedido com 2 pagamentos.
- **Ordem segura:** (1) filtre `pedido` (situação, período); (2) se precisar de UF, junte com `cliente`, que é N:1 e não multiplica; (3) para valores, **some os itens por `idPedido` primeiro** e só depois junte ao conjunto de pedidos selecionados.
- `cliente` deve ter `idCliente` único. Se houver repetição, o script avisa e usa a primeira ocorrência, para não multiplicar pedidos.

## 3. Valores monetários: não confunda

| Campo | O que é | Usado em |
|---|---|---|
| `item_pedido.vlPreco` | preço da unidade do item, **sem frete** | M3 (ticket médio) |
| `item_pedido.vlFrete` | frete atribuído ao item | Só como informação separada |
| `pagamento_pedido.vlPagamento` | valor pago (inclui frete, pode estar dividido em vários pagamentos) | **Não usado** |

## 4. Status conhecidos de `descSituacao`

No Olist: `delivered`, `shipped`, `canceled`, `unavailable`, `invoiced`, `processing`, `created`, `approved`. As análises usam apenas `delivered` (regra R1). O diagnóstico do script lista os valores reais encontrados.
