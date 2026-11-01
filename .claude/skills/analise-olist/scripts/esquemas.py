"""Mapeamento entre nomes lógicos usados nas análises e os arquivos/colunas de cada base.

Para suportar outra base, acrescente um Esquema aqui e documente-o em
references/esquemas-de-dados.md. As regras em analise.py não mudam.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Esquema:
    nome: str
    descricao: str
    # pedidos
    arq_pedido: str
    col_pedido: str
    col_cliente_pedido: str
    col_situacao: str
    col_data: str
    situacao_entregue: str
    # clientes
    arq_cliente: str
    col_cliente: str
    col_uf: str
    rotulo_uf: str
    moeda: str
    # itens
    arq_item: str
    col_pedido_item: str
    col_valor_item: str
    col_quantidade: Optional[str]   # None: cada linha é 1 unidade (Olist)
    col_frete: Optional[str]        # None: a base não tem frete
    # arquivos que existem mas não entram nas três análises (listados no diagnóstico)
    outros_arquivos: tuple = ()


OLIST = Esquema(
    nome="olist",
    descricao="Olist (nomes em português: pedido.csv, cliente.csv, item_pedido.csv...)",
    arq_pedido="pedido.csv", col_pedido="idPedido", col_cliente_pedido="idCliente",
    col_situacao="descSituacao", col_data="dtPedido", situacao_entregue="delivered",
    arq_cliente="cliente.csv", col_cliente="idCliente", col_uf="descUF", rotulo_uf="UF", moeda="R$",
    arq_item="item_pedido.csv", col_pedido_item="idPedido", col_valor_item="vlPreco",
    col_quantidade=None, col_frete="vlFrete",
    outros_arquivos=("pagamento_pedido.csv", "produto.csv", "vendedor.csv", "avaliacao_pedido.csv"),
)

GARDEN_SHOP = Esquema(
    nome="garden_shop",
    descricao="Garden Shop (orders.csv, customers.csv, order_items.csv) — equivalências em references/esquemas-de-dados.md",
    arq_pedido="orders.csv", col_pedido="order_id", col_cliente_pedido="customer_id",
    col_situacao="status", col_data="order_date", situacao_entregue="shipped",
    arq_cliente="customers.csv", col_cliente="customer_id", col_uf="state", rotulo_uf="estado (EUA)", moeda="US$",
    arq_item="order_items.csv", col_pedido_item="order_id", col_valor_item="unit_price",
    col_quantidade="quantity", col_frete=None,
    outros_arquivos=("products.csv", "categories.csv", "suppliers.csv"),
)

ESQUEMAS = {e.nome: e for e in (OLIST, GARDEN_SHOP)}
