"""Testes da skill analise-olist (escritos antes de scripts/analise.py).

Recorte Olist (tests/fixtures/olist_recorte) — resultados esperados calculados à mão:

  pedido  cliente  situação   dtPedido              itens (vlPreco)        observação
  p01     c1/SP    delivered  2017-01-05            100 + 100              2 itens iguais, 2 pagamentos
  p02     c2/SP    delivered  2017-01-31 23:59:59   50                     borda de fim de mês
  p03     c3/RJ    delivered  2017-02-01 00:00:00   80                     borda de início de mês
  p04     c1/SP    canceled   2017-02-10            50                     fora (cancelado)
  p05     c4/MG    delivered  2017-02-15            30 + 20
  p06     c5/RS    shipped    2017-02-20            100                    fora (não entregue)
  p07     c3/RJ    delivered  2017-03-03            60
  p08     c6/PR    delivered  2017-03-10            —                      pedido sem itens
  p09     c7/BA    delivered  2017-13-45            70                     data inválida → excluído
  p10     c9/—     delivered  2017-03-20            40                     cliente sem correspondência
  p11     c2/SP    delivered  2017-03-25            25
  p12     c4/MG    delivered  (vazia)               90                     data ausente → excluído
  p99     —        —          —                     10                     item órfão (pedido inexistente)

  M1: jan=2 (p01,p02) · fev=2 (p03,p05) · mar=4 (p07,p08,p10,p11) · total=8
  M2: SP=3 · RJ=2 · MG=1 · PR=1 · fora do ranking: p10 (sem cliente)
  M3: (200+50+80+50+60+0+40+25)=505 / 8 pedidos = 63,125 · 1 pedido sem itens (p08) · frete 50,50
"""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date

import pytest

import calculo_independente as ind
from analise import ErroDados, carregar, diagnostico, pedidos_por_mes, ticket_medio, top_ufs


# --------------------------------------------------------------------------- carga e qualidade
def test_detecta_esquema(olist_dir, garden_dir):
    assert carregar(olist_dir).esquema.nome == "olist"
    assert carregar(garden_dir).esquema.nome == "garden_shop"


def test_qualidade_dos_dados_recorte(olist_dir):
    d = diagnostico(carregar(olist_dir))["qualidade"]
    assert d["pedidos_data_invalida_ou_ausente"] == 2          # p09, p12
    assert d["pedidos_sem_cliente_correspondente"] == 1         # p10
    assert d["itens_sem_pedido_correspondente"] == 1            # p99
    assert d["ids_pedido_duplicados"] == 0


def test_pasta_inexistente(tmp_path):
    with pytest.raises(ErroDados, match="Pasta de dados não encontrada"):
        carregar(tmp_path / "nao_existe")


def test_pasta_sem_arquivos_conhecidos(tmp_path):
    with pytest.raises(ErroDados, match="pedido.csv.*orders.csv"):
        carregar(tmp_path)


def test_coluna_ausente(olist_dir, tmp_path):
    shutil.copytree(olist_dir, tmp_path / "d")
    p = tmp_path / "d" / "pedido.csv"
    p.write_text(p.read_text().replace("descSituacao", "situacao"))
    with pytest.raises(ErroDados, match="pedido.csv: colunas ausentes: descSituacao"):
        carregar(tmp_path / "d")


def test_separador_ponto_e_virgula(olist_dir, tmp_path):
    destino = tmp_path / "pv"
    destino.mkdir()
    for arq in olist_dir.glob("*.csv"):
        (destino / arq.name).write_text(arq.read_text().replace(",", ";"))
    r = ticket_medio(carregar(destino))["resultado"]
    assert r["soma_itens"] == pytest.approx(505.0) and r["pedidos"] == 8


def test_arquivos_originais_nao_mudam(olist_dir, garden_dir):
    def h():
        return {f: hashlib.md5(f.read_bytes()).hexdigest() for d in (olist_dir, garden_dir) for f in d.iterdir()}
    antes = h()
    for pasta in (olist_dir, garden_dir):
        b = carregar(pasta)
        pedidos_por_mes(b), top_ufs(b), ticket_medio(b), diagnostico(b)
    assert h() == antes


# --------------------------------------------------------------------------- M1 pedidos por mês
def test_m1_recorte_valores_a_mao(olist_dir):
    r = pedidos_por_mes(carregar(olist_dir))["resultado"]
    assert r["meses"] == {"2017-01": 2, "2017-02": 2, "2017-03": 4}
    assert r["total"] == 8


def test_m1_confere_com_calculo_independente(olist_dir):
    assert pedidos_por_mes(carregar(olist_dir))["resultado"]["meses"] == ind.pedidos_por_mes(olist_dir)


def test_m1_bordas_do_periodo_sao_inclusivas(olist_dir):
    b = carregar(olist_dir)
    assert pedidos_por_mes(b, inicio="2017-01-01", fim="2017-01-31")["resultado"]["total"] == 2   # p02 23:59:59
    assert pedidos_por_mes(b, inicio="2017-02", fim="2017-02")["resultado"]["meses"] == {"2017-02": 2}  # p03 00:00


def test_m1_periodo_sem_dados_retorna_zero(olist_dir):
    r = pedidos_por_mes(carregar(olist_dir), inicio="2018-01", fim="2018-02")["resultado"]
    assert r["meses"] == {"2018-01": 0, "2018-02": 0} and r["total"] == 0


def test_m1_continuacao_filtro_uf(olist_dir):
    r = pedidos_por_mes(carregar(olist_dir), ufs=["sp"])["resultado"]
    assert r["meses"] == {"2017-01": 2, "2017-02": 0, "2017-03": 1} and r["total"] == 3


def test_m1_periodo_invalido(olist_dir):
    with pytest.raises(ErroDados, match="Data inválida"):
        pedidos_por_mes(carregar(olist_dir), inicio="31/01/2017")
    with pytest.raises(ErroDados, match="início .* depois do fim"):
        pedidos_por_mes(carregar(olist_dir), inicio="2017-03", fim="2017-01")


# --------------------------------------------------------------------------- M2 ranking de UFs
def test_m2_ranking_recorte(olist_dir):
    r = top_ufs(carregar(olist_dir))["resultado"]
    assert r["ranking"] == [["SP", 3], ["RJ", 2], ["MG", 1], ["PR", 1]]
    assert r["pedidos_fora_do_ranking"] == 1   # p10 sem cliente
    assert r["ufs_disponiveis"] == 4


def test_m2_empate_no_corte_e_avisado(olist_dir):
    b = carregar(olist_dir)
    assert top_ufs(b, top=2)["resultado"]["empate_no_corte"] is False
    r = top_ufs(b, top=3)["resultado"]
    assert r["ranking"] == [["SP", 3], ["RJ", 2], ["MG", 1]] and r["empate_no_corte"] is True


def test_m2_continuacao_periodo(olist_dir):
    r = top_ufs(carregar(olist_dir), inicio="2017-03", fim="2017-03")["resultado"]
    assert r["ranking"] == [["PR", 1], ["RJ", 1], ["SP", 1]] and r["pedidos_fora_do_ranking"] == 1


def test_m2_periodo_sem_dados(olist_dir):
    r = top_ufs(carregar(olist_dir), inicio="2019-01", fim="2019-12")["resultado"]
    assert r["ranking"] == [] and r["total_pedidos"] == 0


# --------------------------------------------------------------------------- M3 ticket médio
def test_m3_recorte_valores_a_mao(olist_dir):
    r = ticket_medio(carregar(olist_dir))["resultado"]
    assert r["soma_itens"] == pytest.approx(505.0)
    assert r["pedidos"] == 8
    assert r["ticket"] == pytest.approx(63.125)
    assert r["pedidos_sem_itens"] == 1
    assert r["ticket_pedidos_com_itens"] == pytest.approx(505 / 7)
    assert r["frete_informativo"] == pytest.approx(50.5)


def test_m3_confere_com_calculo_independente(olist_dir):
    assert ticket_medio(carregar(olist_dir))["resultado"]["ticket"] == pytest.approx(ind.ticket_medio(olist_dir))
    assert ticket_medio(carregar(olist_dir), inicio="2017-02", fim="2017-03")["resultado"]["ticket"] == \
        pytest.approx(ind.ticket_medio(olist_dir, date(2017, 2, 1), date(2017, 3, 31)))


def test_m3_continuacao_periodo_e_uf(olist_dir):
    b = carregar(olist_dir)
    assert ticket_medio(b, inicio="2017-02", fim="2017-03")["resultado"]["ticket"] == pytest.approx(255 / 6)
    assert ticket_medio(b, ufs=["SP"])["resultado"]["ticket"] == pytest.approx(275 / 3)


def test_m3_sem_pedidos_e_nao_aplicavel(olist_dir):
    r = ticket_medio(carregar(olist_dir), inicio="2018-01", fim="2018-12")["resultado"]
    assert r["ticket"] is None and r["pedidos"] == 0


def test_m3_pagamentos_nao_multiplicam(olist_dir, tmp_path):
    shutil.copytree(olist_dir, tmp_path / "sem_pag")
    (tmp_path / "sem_pag" / "pagamento_pedido.csv").unlink()
    com = ticket_medio(carregar(olist_dir))["resultado"]
    sem = ticket_medio(carregar(tmp_path / "sem_pag"))["resultado"]
    assert com["soma_itens"] == sem["soma_itens"] == pytest.approx(505.0)  # p01 = 200, não 400


# --------------------------------------------------------------------------- Garden Shop (base disponível)
def _gs_enviados(garden_dir):
    with open(garden_dir / "orders.csv", newline="") as f:
        return {o["order_id"]: o for o in csv.DictReader(f) if o["status"] == "shipped"}


def test_gs_m1_confere_com_contagem_direta(garden_dir):
    esperado = {}
    for o in _gs_enviados(garden_dir).values():
        esperado[o["order_date"][:7]] = esperado.get(o["order_date"][:7], 0) + 1
    r = pedidos_por_mes(carregar(garden_dir))["resultado"]
    assert r["meses"] == dict(sorted(esperado.items())) and r["total"] == 17


def test_gs_m3_valor_do_item_usa_quantidade(garden_dir):
    sel = _gs_enviados(garden_dir)
    with open(garden_dir / "order_items.csv", newline="") as f:
        soma = sum(float(i["unit_price"]) * int(i["quantity"]) for i in csv.DictReader(f) if i["order_id"] in sel)
    r = ticket_medio(carregar(garden_dir))["resultado"]
    assert r["soma_itens"] == pytest.approx(soma) and r["ticket"] == pytest.approx(soma / len(sel))
    assert r["frete_informativo"] is None     # Garden Shop não tem frete


def test_gs_m2_confere_com_contagem_direta(garden_dir):
    with open(garden_dir / "customers.csv", newline="") as f:
        uf = {c["customer_id"]: c["state"] for c in csv.DictReader(f)}
    cont = {}
    for o in _gs_enviados(garden_dir).values():
        cont[uf[o["customer_id"]]] = cont.get(uf[o["customer_id"]], 0) + 1
    esperado = sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    assert top_ufs(carregar(garden_dir))["resultado"]["ranking"] == [list(x) for x in esperado]


# --------------------------------------------------------------------------- linha de comando
def _cli(script, *args, env=None):
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, env=env)


def test_cli_texto_tem_evidencias(script, olist_dir):
    r = _cli(script, "ticket_medio", "--dados", str(olist_dir), "--inicio", "2017-02", "--fim", "2017-03")
    assert r.returncode == 0
    for trecho in ("Métrica", "Filtros", "Período: 2017-02-01 a 2017-03-31 (datas inclusivas", "Arquivos utilizados",
                   "pedido.csv", "item_pedido.csv", "Qualidade", "Resultado", "42,50", "Comando"):
        assert trecho in r.stdout, trecho
    assert "pagamento_pedido.csv" not in r.stdout.split("Arquivos utilizados")[1].split("\n\n")[0]


def test_cli_json(script, olist_dir):
    r = _cli(script, "pedidos_mes", "--dados", str(olist_dir), "--json")
    assert json.loads(r.stdout)["resultado"]["total"] == 8


def test_cli_media_sem_pedidos_mostra_nao_aplicavel(script, olist_dir):
    r = _cli(script, "ticket_medio", "--dados", str(olist_dir), "--inicio", "2018-01", "--fim", "2018-01")
    assert r.returncode == 0 and "não aplicável" in r.stdout


def test_cli_variavel_de_ambiente(script, olist_dir):
    import os
    env = {**os.environ, "ANALISE_OLIST_DADOS": str(olist_dir)}
    assert json.loads(_cli(script, "top_ufs", "--json", env=env).stdout)["resultado"]["ranking"][0] == ["SP", 3]


def test_cli_sem_pasta_explica_impedimento(script):
    import os
    env = {k: v for k, v in os.environ.items() if k != "ANALISE_OLIST_DADOS"}
    r = _cli(script, "pedidos_mes", env=env)
    assert r.returncode == 2 and "--dados" in r.stderr and "ANALISE_OLIST_DADOS" in r.stderr


def test_cli_salva_saida_sem_tocar_nos_dados(script, olist_dir, tmp_path):
    destino = tmp_path / "saida.txt"
    r = _cli(script, "top_ufs", "--dados", str(olist_dir), "--saida", str(destino))
    assert r.returncode == 0 and destino.read_text() == r.stdout


def test_arredondamento_comercial_na_saida(script, olist_dir):
    r = _cli(script, "ticket_medio", "--dados", str(olist_dir))
    assert "R$ 63,13" in r.stdout          # 505 / 8 = 63,125
