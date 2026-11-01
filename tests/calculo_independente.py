"""Cálculo independente de M1 (pedidos por mês) e M3 (ticket médio), só com a biblioteca padrão.

Não importa nada de scripts/analise.py nem usa pandas: serve para conferir o script por um
caminho de código diferente (exigência da lista: resultados esperados calculados independentemente).
"""
import csv
from datetime import datetime
from pathlib import Path


def _ler(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _data(texto: str):
    try:
        return datetime.strptime(texto.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def pedidos_entregues(pasta: Path, inicio=None, fim=None):
    """ids dos pedidos 'delivered' com data válida dentro de [inicio, fim] (datas inclusivas)."""
    ids = {}
    for p in _ler(pasta / "pedido.csv"):
        d = _data(p["dtPedido"])
        if p["descSituacao"].strip().lower() != "delivered" or d is None:
            continue
        if (inicio and d < inicio) or (fim and d > fim):
            continue
        ids[p["idPedido"]] = d
    return ids


def pedidos_por_mes(pasta: Path, inicio=None, fim=None):
    meses = {}
    for d in pedidos_entregues(pasta, inicio, fim).values():
        chave = f"{d.year}-{d.month:02d}"
        meses[chave] = meses.get(chave, 0) + 1
    return meses


def ticket_medio(pasta: Path, inicio=None, fim=None):
    sel = pedidos_entregues(pasta, inicio, fim)
    soma = sum(float(i["vlPreco"]) for i in _ler(pasta / "item_pedido.csv") if i["idPedido"] in sel)
    return None if not sel else soma / len(sel)
