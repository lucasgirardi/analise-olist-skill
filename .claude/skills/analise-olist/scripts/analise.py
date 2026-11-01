#!/usr/bin/env python3
"""Copiloto de analytics: análises reutilizáveis sobre a base Olist (ou Garden Shop, via esquema).

Autor: Lucas Girardi. Regras em ../references/regras-de-negocio.md.

Uso:
    python analise.py {pedidos_mes,top_ufs,ticket_medio,diagnostico} --dados PASTA
                      [--inicio AAAA-MM[-DD]] [--fim AAAA-MM[-DD]] [--uf SP,RJ] [--top 5]
                      [--situacao delivered] [--esquema auto|olist|garden_shop] [--json] [--saida ARQ]

A pasta dos dados também pode vir da variável de ambiente ANALISE_OLIST_DADOS.
O script só LÊ os arquivos de dados; nunca os altera.
"""
from __future__ import annotations

import argparse
import calendar
import io
import json
import os
import shlex
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from esquemas import ESQUEMAS, Esquema  # noqa: E402

ENV_DADOS = "ANALISE_OLIST_DADOS"
ANALISES = ("pedidos_mes", "top_ufs", "ticket_medio", "diagnostico")


class ErroDados(Exception):
    """Problema nos dados ou nos parâmetros, com mensagem pronta para o usuário."""


@dataclass
class Base:
    pasta: Path
    esquema: Esquema
    pedidos: pd.DataFrame   # pedido, cliente, situacao, data (Timestamp/NaT), data_bruta, uf
    clientes: pd.DataFrame  # cliente, uf
    itens: pd.DataFrame     # pedido, valor (float/NaN), frete (float/NaN)
    qualidade: dict
    arquivos_lidos: dict    # nome -> {"linhas": n, "separador": ","}


# ============================================================================ leitura
def _ler_csv(path: Path, colunas: list[str]) -> tuple[pd.DataFrame, str]:
    if not path.exists():
        raise ErroDados(f"{path.name}: arquivo não encontrado em {path.parent}")
    bruto = path.read_bytes()
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    cabecalho = texto.splitlines()[0] if texto.strip() else ""
    sep = max([",", ";", "\t"], key=cabecalho.count)
    df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    faltam = [c for c in colunas if c not in df.columns]
    if faltam:
        raise ErroDados(f"{path.name}: colunas ausentes: {', '.join(faltam)} "
                        f"(encontradas: {', '.join(df.columns)})")
    df = df[colunas].apply(lambda s: s.str.strip())
    return df.replace("", pd.NA), sep


def _detectar_esquema(pasta: Path, nome: str) -> Esquema:
    if nome != "auto":
        if nome not in ESQUEMAS:
            raise ErroDados(f"Esquema desconhecido: {nome}. Opções: auto, {', '.join(ESQUEMAS)}")
        return ESQUEMAS[nome]
    for esq in ESQUEMAS.values():
        if (pasta / esq.arq_pedido).exists():
            return esq
    encontrados = sorted(p.name for p in pasta.iterdir()) or ["(pasta vazia)"]
    raise ErroDados(f"Nenhum arquivo de pedidos reconhecido em {pasta}: esperado pedido.csv (Olist) "
                    f"ou orders.csv (Garden Shop). Arquivos encontrados: {', '.join(encontrados)}")


def carregar(pasta, esquema: str = "auto") -> Base:
    """Lê e valida pedidos, clientes e itens. Não altera nenhum arquivo."""
    pasta = Path(pasta).expanduser()
    if not pasta.is_dir():
        raise ErroDados(f"Pasta de dados não encontrada: {pasta}")
    e = _detectar_esquema(pasta, esquema)
    lidos = {}

    ped, sep = _ler_csv(pasta / e.arq_pedido, [e.col_pedido, e.col_cliente_pedido, e.col_situacao, e.col_data])
    lidos[e.arq_pedido] = {"linhas": len(ped), "separador": sep}
    ped.columns = ["pedido", "cliente", "situacao", "data_bruta"]
    ped["situacao"] = ped["situacao"].str.lower()
    ped["data"] = pd.to_datetime(ped["data_bruta"], format="ISO8601", errors="coerce")

    cli, sep = _ler_csv(pasta / e.arq_cliente, [e.col_cliente, e.col_uf])
    lidos[e.arq_cliente] = {"linhas": len(cli), "separador": sep}
    cli.columns = ["cliente", "uf"]
    cli["uf"] = cli["uf"].str.upper()
    cli_dup = int(cli["cliente"].duplicated().sum())
    cli = cli.drop_duplicates("cliente", keep="first")

    cols_item = [e.col_pedido_item, e.col_valor_item] + [c for c in (e.col_quantidade, e.col_frete) if c]
    it, sep = _ler_csv(pasta / e.arq_item, cols_item)
    lidos[e.arq_item] = {"linhas": len(it), "separador": sep}
    itens = pd.DataFrame({"pedido": it[e.col_pedido_item]})
    valor = pd.to_numeric(it[e.col_valor_item], errors="coerce")
    if e.col_quantidade:
        valor = valor * pd.to_numeric(it[e.col_quantidade], errors="coerce")
    itens["valor"] = valor
    itens["frete"] = pd.to_numeric(it[e.col_frete], errors="coerce") if e.col_frete else float("nan")

    ped = ped.merge(cli, on="cliente", how="left", validate="many_to_one")
    datas_validas = ped["data"].dropna()
    qualidade = {
        "pedidos_total": int(ped["pedido"].nunique()),
        "ids_pedido_duplicados": int(ped["pedido"].duplicated().sum()),
        "pedidos_data_invalida_ou_ausente": int(ped["data"].isna().sum()),
        "pedidos_sem_cliente_correspondente": int((~ped["cliente"].isin(cli["cliente"])).sum()),
        "clientes_duplicados": cli_dup,
        "clientes_uf_vazia": int(cli["uf"].isna().sum()),
        "itens_total": len(itens),
        "itens_sem_pedido_correspondente": int((~itens["pedido"].isin(ped["pedido"])).sum()),
        "itens_valor_invalido": int(itens["valor"].isna().sum()),
        "situacoes": {k: int(v) for k, v in ped["situacao"].value_counts(dropna=False).items()},
        "datas_min": None if datas_validas.empty else str(datas_validas.min().date()),
        "datas_max": None if datas_validas.empty else str(datas_validas.max().date()),
    }
    return Base(pasta, e, ped, cli, itens, qualidade, lidos)


# ============================================================================ seleção (regras R1-R5)
def _data_param(texto: Optional[str], fim: bool) -> Optional[date]:
    if texto is None:
        return None
    t = str(texto).strip()
    try:
        if len(t) == 7:
            d = datetime.strptime(t, "%Y-%m").date()
            return d.replace(day=calendar.monthrange(d.year, d.month)[1]) if fim else d
        return datetime.strptime(t, "%Y-%m-%d").date()
    except ValueError:
        raise ErroDados(f"Data inválida: '{texto}'. Use AAAA-MM-DD ou AAAA-MM.") from None


def _selecionar(base: Base, inicio, fim, ufs, situacao):
    ini, fi = _data_param(inicio, False), _data_param(fim, True)
    if ini and fi and ini > fi:
        raise ErroDados(f"Período inválido: início {ini} depois do fim {fi}.")
    sit = (situacao or base.esquema.situacao_entregue).strip().lower()
    ufs = [u.strip().upper() for u in ufs] if ufs else None

    p = base.pedidos[base.pedidos["situacao"] == sit].drop_duplicates("pedido")
    sem_data = int(p["data"].isna().sum())
    p = p[p["data"].notna()]
    dia = p["data"].dt.date
    if ini:
        p = p[dia >= ini]
    if fi:
        p = p[p["data"].dt.date <= fi]
    if ufs:
        p = p[p["uf"].isin(ufs)]
    ctx = {"situacao": sit, "inicio": ini, "fim": fi, "ufs": ufs, "excluidos_sem_data": sem_data}
    return p, ctx


def _envelope(base: Base, analise: str, metrica: str, ctx: dict, arquivos: list[str], resultado: dict,
              observacoes: list[str], extra_filtros: Optional[dict] = None) -> dict:
    e = base.esquema
    if ctx["inicio"] or ctx["fim"]:
        periodo = (f"{ctx['inicio'] or 'início da base'} a {ctx['fim'] or 'fim da base'} "
                   f"(datas inclusivas, por {e.col_data}, horário ignorado)")
    else:
        periodo = (f"toda a base ({base.qualidade['datas_min']} a {base.qualidade['datas_max']} com datas válidas; "
                   f"datas inclusivas, por {e.col_data})")
    obs = list(observacoes)
    if ctx["excluidos_sem_data"]:
        obs.insert(0, f"{ctx['excluidos_sem_data']} pedido(s) '{ctx['situacao']}' com {e.col_data} inválida ou "
                      f"ausente foram excluídos (não há mês para atribuir).")
    if e.nome == "garden_shop":
        obs.append("Base Garden Shop: 'shipped' usado como equivalente de 'delivered'; "
                   "'state' são estados dos EUA (ver references/esquemas-de-dados.md).")
    filtros = {"situacao": ctx["situacao"], "inicio": str(ctx["inicio"]) if ctx["inicio"] else None,
               "fim": str(ctx["fim"]) if ctx["fim"] else None, "ufs": ctx["ufs"], **(extra_filtros or {})}
    return {"analise": analise, "metrica": metrica, "esquema": e.nome, "pasta": str(base.pasta),
            "filtros": filtros, "periodo": periodo, "arquivos": arquivos, "resultado": resultado,
            "observacoes": obs, "moeda": e.moeda, "rotulo_uf": e.rotulo_uf}


# ============================================================================ métricas
def pedidos_por_mes(base: Base, inicio=None, fim=None, ufs=None, situacao=None) -> dict:
    """M1: COUNT(DISTINCT pedido) por mês da data do pedido. Meses sem pedidos no período = 0."""
    e = base.esquema
    sel, ctx = _selecionar(base, inicio, fim, ufs, situacao)
    meses_sel = sel["data"].dt.to_period("M")
    ini = pd.Period(ctx["inicio"], "M") if ctx["inicio"] else (meses_sel.min() if len(sel) else None)
    fi = pd.Period(ctx["fim"], "M") if ctx["fim"] else (meses_sel.max() if len(sel) else None)
    contagem = sel.groupby(meses_sel)["pedido"].nunique()
    meses = {}
    if ini is not None and fi is not None:
        meses = {str(m): int(contagem.get(m, 0)) for m in pd.period_range(ini, fi, freq="M")}
    arquivos = [e.arq_pedido] + ([e.arq_cliente] if ctx["ufs"] else [])
    obs = [] if meses else ["Nenhum pedido no período/filtros: contagem = 0."]
    return _envelope(base, "pedidos_mes",
                     f"Pedidos entregues por mês = COUNT(DISTINCT {e.col_pedido}) por mês de {e.col_data}",
                     ctx, arquivos, {"meses": meses, "total": int(sel["pedido"].nunique())}, obs)


def top_ufs(base: Base, top: int = 5, inicio=None, fim=None, ufs=None, situacao=None) -> dict:
    """M2: ranking de UFs do cliente por COUNT(DISTINCT pedido); desempate alfabético."""
    e = base.esquema
    sel, ctx = _selecionar(base, inicio, fim, ufs, situacao)
    fora = int(sel["uf"].isna().sum())
    cont = sel.dropna(subset=["uf"]).groupby("uf")["pedido"].nunique()
    completo = sorted(((u, int(n)) for u, n in cont.items()), key=lambda x: (-x[1], x[0]))
    ranking = [list(x) for x in completo[:top]]
    empate = len(completo) > top and top > 0 and completo[top][1] == completo[top - 1][1]
    obs = []
    if fora:
        obs.append(f"{fora} pedido(s) sem cliente correspondente ou sem {e.col_uf} ficaram fora do ranking.")
    if empate:
        empatadas = [u for u, n in completo[top:] if n == completo[top - 1][1]]
        obs.append(f"Empate no corte: {', '.join(empatadas)} também tem(têm) {completo[top - 1][1]} pedido(s).")
    if 0 < len(completo) < top:
        obs.append(f"Só existem {len(completo)} {e.rotulo_uf}(s) com pedidos nos filtros (pedido: top {top}).")
    if not completo:
        obs.append("Nenhum pedido no período/filtros: ranking vazio.")
    return _envelope(base, "top_ufs",
                     f"Top {top} {e.rotulo_uf} do cliente por COUNT(DISTINCT {e.col_pedido}) entregues "
                     f"({e.arq_pedido} ⨝ {e.arq_cliente} por {e.col_cliente})",
                     ctx, [e.arq_pedido, e.arq_cliente],
                     {"ranking": ranking, "total_pedidos": int(sel["pedido"].nunique()),
                      "pedidos_fora_do_ranking": fora, "ufs_disponiveis": len(completo), "empate_no_corte": empate},
                     obs, {"top": top})


def ticket_medio(base: Base, inicio=None, fim=None, ufs=None, situacao=None) -> dict:
    """M3: Σ valor dos itens (sem frete) ÷ nº de pedidos selecionados. Sem pedidos -> None (não aplicável)."""
    e = base.esquema
    sel, ctx = _selecionar(base, inicio, fim, ufs, situacao)
    ids = set(sel["pedido"])
    itens = base.itens[base.itens["pedido"].isin(ids)]
    por_pedido = itens.groupby("pedido").agg(valor=("valor", "sum"), frete=("frete", "sum"))  # agrega ANTES
    n = len(ids)
    com_itens = int(len(por_pedido))
    soma = float(itens["valor"].sum())
    sem_valor = int(itens["valor"].isna().sum())
    valor_desc = f"{e.col_valor_item} × {e.col_quantidade}" if e.col_quantidade else e.col_valor_item
    res = {
        "ticket": soma / n if n else None,
        "soma_itens": soma,
        "pedidos": n,
        "pedidos_com_itens": com_itens,
        "pedidos_sem_itens": n - com_itens,
        "ticket_pedidos_com_itens": soma / com_itens if com_itens else None,
        "itens_considerados": int(len(itens)),
        "itens_sem_valor": sem_valor,
        "frete_informativo": float(itens["frete"].sum()) if e.col_frete else None,
    }
    obs = []
    if n == 0:
        obs.append("Nenhum pedido selecionado: o ticket médio é não aplicável (não é zero).")
    if res["pedidos_sem_itens"]:
        obs.append(f"Cobertura: {res['pedidos_sem_itens']} de {n} pedido(s) selecionado(s) não têm itens em "
                   f"{e.arq_item}; entram no denominador com valor 0 (regra M3).")
    if sem_valor:
        obs.append(f"{sem_valor} item(ns) com {e.col_valor_item} inválido foram excluídos da soma.")
    obs.append(f"Frete ({e.col_frete}) não incluído no ticket." if e.col_frete
               else "A base não tem frete: o ticket já é sem frete por construção.")
    if e.nome == "olist":
        obs.append("pagamento_pedido.csv (vlPagamento) não foi usado: inclui frete e pode ter vários pagamentos "
                   "por pedido.")
    arquivos = [e.arq_pedido] + ([e.arq_cliente] if ctx["ufs"] else []) + [e.arq_item]
    return _envelope(base, "ticket_medio",
                     f"Ticket médio sem frete = Σ {valor_desc} dos itens ÷ COUNT(DISTINCT {e.col_pedido}) selecionados",
                     ctx, arquivos, res, obs)


def diagnostico(base: Base) -> dict:
    """Estrutura e qualidade da base: arquivos, linhas, separador, status, período e problemas de chave."""
    e = base.esquema
    outros = {a: (base.pasta / a).exists() for a in e.outros_arquivos}
    obs = []
    q = base.qualidade
    if q["pedidos_total"] and q["pedidos_data_invalida_ou_ausente"] > q["pedidos_total"] / 2:
        obs.append(f"Mais da metade das datas em {e.col_data} é inválida: confira o formato no dicionário "
                   f"(o script espera AAAA-MM-DD[ HH:MM:SS]).")
    return {"analise": "diagnostico", "esquema": e.nome, "descricao": e.descricao, "pasta": str(base.pasta),
            "arquivos_lidos": base.arquivos_lidos, "outros_arquivos_presentes": outros,
            "qualidade": q, "observacoes": obs}


# ============================================================================ apresentação
def _num(v: float, casas: int = 2) -> str:
    """Formato brasileiro com arredondamento comercial (63,125 -> 63,13)."""
    v = Decimal(repr(v)).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar(r: dict, comando: Optional[str] = None) -> str:
    L = ["=== Copiloto de analytics · skill analise-olist ===", ""]
    if r["analise"] == "diagnostico":
        L += [f"Diagnóstico da base: {r['descricao']}", f"Pasta: {r['pasta']}", "", "Arquivos lidos:"]
        L += [f"  - {a}: {i['linhas']} linhas (separador '{i['separador']}')" for a, i in r["arquivos_lidos"].items()]
        L += [f"  - {a}: {'presente' if ok else 'ausente'} (não usado nas três análises)"
              for a, ok in r["outros_arquivos_presentes"].items()]
        L += ["", "Qualidade dos dados:"] + [f"  - {k}: {v}" for k, v in r["qualidade"].items()]
    else:
        f, res, m = r["filtros"], r["resultado"], r["moeda"]
        L += [f"Métrica: {r['metrica']}", f"Base: {r['esquema']} ({r['pasta']})", "",
              "Filtros:", f"  - Situação: {f['situacao']}", f"  - Período: {r['periodo']}",
              f"  - {r['rotulo_uf']} do cliente: {', '.join(f['ufs']) if f['ufs'] else 'todas'}"]
        if "top" in f:
            L.append(f"  - Top: {f['top']}")
        L += ["", f"Arquivos utilizados: {', '.join(r['arquivos'])}", "", "Resultado:"]
        if r["analise"] == "pedidos_mes":
            L += ["  | Mês     | Pedidos |", "  |---------|--------:|"]
            L += [f"  | {mes} | {n:>7} |" for mes, n in res["meses"].items()] or ["  | (nenhum mês) |   0 |"]
            L.append(f"  Total do período: {res['total']} pedido(s)")
        elif r["analise"] == "top_ufs":
            L += [f"  | # | {r['rotulo_uf']} | Pedidos |", "  |---|----|--------:|"]
            L += [f"  | {i} | {u} | {n:>7} |" for i, (u, n) in enumerate(res["ranking"], 1)] or ["  (ranking vazio)"]
            L.append(f"  Pedidos considerados: {res['total_pedidos']} · fora do ranking: {res['pedidos_fora_do_ranking']}")
        elif r["analise"] == "ticket_medio":
            t = res["ticket"]
            L += [f"  Ticket médio (sem frete): {m} {_num(t)}" if t is not None else
                  "  Ticket médio (sem frete): não aplicável (nenhum pedido selecionado)",
                  f"  Soma dos itens: {m} {_num(res['soma_itens'])} · Pedidos: {res['pedidos']} "
                  f"(com itens: {res['pedidos_com_itens']}, sem itens: {res['pedidos_sem_itens']})"]
            if res["pedidos_sem_itens"] and res["ticket_pedidos_com_itens"] is not None:
                L.append(f"  Referência: ticket só dos pedidos com itens = {m} {_num(res['ticket_pedidos_com_itens'])}")
            if res["frete_informativo"] is not None:
                L.append(f"  Frete dos mesmos pedidos (NÃO incluído): {m} {_num(res['frete_informativo'])}")
    if r["observacoes"]:
        L += ["", "Qualidade e cobertura:"] + [f"  - {o}" for o in r["observacoes"]]
    if comando:
        L += ["", f"Comando: {comando}"]
    return "\n".join(L) + "\n"


def _json_padrao(o):
    if isinstance(o, (date, Path)):
        return str(o)
    raise TypeError(type(o))


# ============================================================================ linha de comando
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Copiloto de analytics Olist (skill analise-olist).")
    ap.add_argument("analise", choices=ANALISES)
    ap.add_argument("--dados", default=os.environ.get(ENV_DADOS),
                    help=f"Pasta com os CSVs (ou variável de ambiente {ENV_DADOS}).")
    ap.add_argument("--esquema", default="auto", help="auto (padrão), olist ou garden_shop.")
    ap.add_argument("--inicio", help="Data inicial inclusiva: AAAA-MM-DD ou AAAA-MM (1º dia do mês).")
    ap.add_argument("--fim", help="Data final inclusiva: AAAA-MM-DD ou AAAA-MM (último dia do mês).")
    ap.add_argument("--uf", help="UF(s) do cliente, separadas por vírgula. Ex.: SP,RJ")
    ap.add_argument("--top", type=int, default=5, help="Tamanho do ranking em top_ufs (padrão 5).")
    ap.add_argument("--situacao", help="Situação do pedido (padrão: entregue no esquema; delivered no Olist).")
    ap.add_argument("--json", action="store_true", help="Saída em JSON (para conferência automática).")
    ap.add_argument("--saida", help="Também grava a saída neste arquivo (fora da pasta de dados).")
    a = ap.parse_args(argv)

    if not a.dados:
        print(f"Impedimento: informe a pasta dos dados com --dados CAMINHO ou a variável de ambiente {ENV_DADOS}.",
              file=sys.stderr)
        return 2
    try:
        base = carregar(a.dados, a.esquema)
        ufs = a.uf.split(",") if a.uf else None
        if a.analise == "pedidos_mes":
            r = pedidos_por_mes(base, a.inicio, a.fim, ufs, a.situacao)
        elif a.analise == "top_ufs":
            r = top_ufs(base, a.top, a.inicio, a.fim, ufs, a.situacao)
        elif a.analise == "ticket_medio":
            r = ticket_medio(base, a.inicio, a.fim, ufs, a.situacao)
        else:
            r = diagnostico(base)
    except ErroDados as erro:
        print(f"Impedimento: {erro}", file=sys.stderr)
        return 2

    comando = "python " + shlex.join(sys.argv if argv is None else ["analise.py", *argv])
    texto = json.dumps(r, ensure_ascii=False, indent=2, default=_json_padrao) + "\n" if a.json else formatar(r, comando)
    if a.saida:
        destino = Path(a.saida).resolve()
        if Path(a.dados).resolve() in destino.parents:
            print("Impedimento: --saida não pode ficar dentro da pasta de dados (dados originais são preservados).",
                  file=sys.stderr)
            return 2
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
