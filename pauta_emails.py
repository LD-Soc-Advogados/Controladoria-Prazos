# -*- coding: utf-8 -*-
"""
Monta os e-mails individuais "Sua(s) audiência(s)" a partir da planilha da pauta
semanal (o .xlsx que a Luciana anexa no e-mail "ATENÇÃO A PAUTA DE AUDIÊNCIAS").

Uso:
    python -I pauta_emails.py "<caminho do .xlsx>"            -> JSON na saída
    python -I pauta_emails.py "<caminho do .xlsx>" --texto    -> leitura humana

O formato do e-mail NÃO foi inventado: foi copiado dos e-mails reais que ela
enviou em 13/11/2026 (Kawan, Clévio, Bárbara Orsini, Rebeka...). Qualquer
mudança aqui muda o que a equipe recebe — confira contra um e-mail real antes.
"""
import json
import sys
import unicodedata
from datetime import date, datetime, time

import openpyxl

# ---------------------------------------------------------------------------
# Quem recebe. Nome como aparece na coluna "Responsável" -> e-mail.
# NUNCA deduza endereço por padrão de domínio: a lista real tem sete formatos
# diferentes (barbara@, barbaraorsini@, larissasabrine@, clevio.lustoza@...),
# e a Isabeli se escreve com um L mas o e-mail tem dois.
# Nome fora desta tabela NÃO recebe e-mail — vira aviso para a Luciana.
# ---------------------------------------------------------------------------
DOMINIO = "@lucchesidolabela.com.br"

RESPONSAVEIS = {
    # confirmados pelos e-mails reais de 13/11/2026
    "ludmila": "financeiro" + DOMINIO,
    "rodrigo": "rodrigo.barbosa" + DOMINIO,
    "gabriela reis": "gabrielareis" + DOMINIO,
    "andreza": "andreza" + DOMINIO,
    "kawan": "kawan.lacerda" + DOMINIO,
    "rebeka": "rebeka.viannini" + DOMINIO,
    "lucas": "lucas" + DOMINIO,
    "clevio": "clevio.lustoza" + DOMINIO,
    "barbara orsini": "barbaraorsini" + DOMINIO,
    # incluída a pedido dela em 16/11/2026 (tinha 2 audiências em 17 e 19/11
    # e ficou de fora do disparo manual)
    "barbara b": "barbara" + DOMINIO,
    "barbara": "barbara" + DOMINIO,
    # demais nomes que já apareceram como responsáveis na pauta
    "larissa": "larissasabrine" + DOMINIO,
    "rafaela": "rafaela" + DOMINIO,
    "isabeli": "isabelli" + DOMINIO,
    "nayara": "nayaradias" + DOMINIO,
    "luiza": "luiza" + DOMINIO,
}

# Correspondente externo: recebe a pauta inteira no próprio e-mail "ATENÇÃO A
# PAUTA" e as instruções processo a processo. NÃO entra no disparo individual.
IGNORAR = {"aspin"}

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def chave(txt):
    """minúsculo, sem acento, sem ponto final — para casar nomes."""
    txt = unicodedata.normalize("NFKD", str(txt or ""))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.lower().replace(".", " ").strip().rstrip(",").strip()


def so_texto(v):
    return "" if v is None else str(v).strip()


def como_data(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def como_hora(v):
    if isinstance(v, datetime):
        return v.strftime("%H:%M")
    if isinstance(v, time):
        return v.strftime("%H:%M")
    t = so_texto(v)
    if not t:
        return ""
    # "13:30:00" -> "13:30"
    partes = t.split(":")
    if len(partes) >= 2:
        return "%s:%s" % (partes[0].zfill(2), partes[1][:2])
    return t


def titulo(nome):
    """MARIA DAS GRACAS -> Maria Das Gracas (é assim que ela escreve no e-mail)."""
    return " ".join(p.capitalize() if p.isupper() or p.islower() else p
                    for p in so_texto(nome).split())


def achar_cabecalho(ws):
    """Acha a linha de cabeçalho (a que tem 'Responsável') e mapeia as colunas."""
    for i, linha in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True), start=1):
        valores = [chave(c) for c in linha]
        if any(v.startswith("respons") for v in valores):
            col = {}
            nomes = []
            for j, v in enumerate(valores):
                if not v:
                    continue
                if v == "nome":
                    nomes.append(j)
                elif v == "civ":
                    col["civ"] = j
                elif v == "data":
                    col["data"] = j
                elif v == "hora":
                    col["hora"] = j
                elif v == "processo":
                    col["processo"] = j
                elif v == "tipo":
                    col["tipo"] = j
                elif v.startswith("respons"):
                    col["responsavel"] = j
                elif v.startswith("virtual"):
                    col["modalidade"] = j
            if nomes:
                # quando há duas colunas "Nome", a segunda é a versão em caixa
                # mista que ela usa no e-mail
                col["nome"] = nomes[-1]
                col["nome_alt"] = nomes[0]
            return i, col
    return None, None


def ler_pauta(caminho):
    wb = openpyxl.load_workbook(caminho, data_only=True)
    linhas = []
    for ws in wb.worksheets:
        i_cab, col = achar_cabecalho(ws)
        if not col or "responsavel" not in col:
            continue
        data_corrente = None
        for linha in ws.iter_rows(min_row=i_cab + 1, values_only=True):
            def c(nome):
                j = col.get(nome)
                return linha[j] if j is not None and j < len(linha) else None

            # ⚠️ A data só aparece na PRIMEIRA linha de cada dia (célula
            # mesclada). Sem este "arrasta para baixo" todas as audiências do
            # dia menos a primeira ficam sem data.
            d = como_data(c("data"))
            if d:
                data_corrente = d
            processo = so_texto(c("processo"))
            responsavel = so_texto(c("responsavel"))
            if not processo and not responsavel:
                continue
            linhas.append({
                "data": data_corrente,
                "civ": so_texto(c("civ")),
                "hora": como_hora(c("hora")),
                "tipo": so_texto(c("tipo")),
                "nome": titulo(so_texto(c("nome")) or so_texto(c("nome_alt"))),
                "processo": processo,
                "modalidade": so_texto(c("modalidade")),
                "responsavel_bruto": responsavel,
            })
    return linhas


def formata_linha(r, outros):
    d = r["data"]
    dia = "%02d/%02d (%s)" % (d.day, d.month, DIAS[d.weekday()]) if d else "(sem data)"
    partes = [dia, r["hora"], r["tipo"], r["nome"], r["processo"], r["modalidade"]]
    texto = " – ".join(p for p in partes[2:] if p)
    cabeca = " ".join(p for p in partes[:2] if p)
    linha = "- %s – %s" % (cabeca, texto) if texto else "- %s" % cabeca
    if outros:
        linha += " (com %s)" % ", ".join(outros)
    return linha


def monta(caminho):
    linhas = ler_pauta(caminho)
    datas = sorted({r["data"] for r in linhas if r["data"]})
    por_pessoa = {}
    sem_email = {}
    sem_responsavel = []

    for r in linhas:
        nomes = [n.strip() for n in r["responsavel_bruto"].split(",") if n.strip()]
        if not nomes:
            sem_responsavel.append(r)
            continue
        for n in nomes:
            k = chave(n)
            if k in IGNORAR:
                continue
            outros = [o.strip() for o in nomes if chave(o) != k]
            if k not in RESPONSAVEIS:
                sem_email.setdefault(n, []).append(formata_linha(r, outros))
                continue
            por_pessoa.setdefault(k, {"nome": n, "email": RESPONSAVEIS[k], "itens": []})
            por_pessoa[k]["itens"].append((r["data"], r["hora"], formata_linha(r, outros)))

    if datas:
        d1, d2 = datas[0], datas[-1]
        if d1.month == d2.month:
            faixa = "%02d a %02d/%02d" % (d1.day, d2.day, d1.month)
        else:
            faixa = "%02d/%02d a %02d/%02d" % (d1.day, d1.month, d2.day, d2.month)
    else:
        faixa = ""

    saida = []
    for k in sorted(por_pessoa):
        p = por_pessoa[k]
        itens = [t for _, _, t in sorted(p["itens"], key=lambda x: (x[0] or date.max, x[1]))]
        primeiro = p["nome"].split()[0]
        if len(itens) == 1:
            d = sorted(p["itens"])[0][0]
            assunto = "Sua audiência – %02d/%02d" % (d.day, d.month) if d else "Sua audiência"
            abre = ("Segue a audiência da semana em que você está como responsável "
                    "(o convite também está no Google Agenda):")
        else:
            assunto = "Suas audiências – %s" % faixa
            abre = ("Seguem as audiências da semana em que você está como responsável "
                    "(os convites também estão no Google Agenda):")
        corpo = "Oi, %s!\n\n%s\n\n%s\n\nQualquer dúvida, me chama.\n\nLuciana" % (
            primeiro, abre, "\n".join(itens))
        saida.append({"nome": p["nome"], "email": p["email"],
                      "assunto": assunto, "corpo": corpo, "qtd": len(itens)})

    return {
        "semana": faixa,
        "total_linhas": len(linhas),
        "emails": saida,
        "sem_email": sem_email,
        "sem_responsavel": [formata_linha(r, []) for r in sem_responsavel],
    }


if __name__ == "__main__":
    res = monta(sys.argv[1])
    if "--texto" in sys.argv:
        print("SEMANA:", res["semana"], "| linhas:", res["total_linhas"])
        for e in res["emails"]:
            print("\n" + "=" * 70)
            print("Para:", e["email"])
            print("Assunto:", e["assunto"])
            print("-" * 70)
            print(e["corpo"])
        if res["sem_email"]:
            print("\n### SEM E-MAIL CADASTRADO (não enviar, avisar a Luciana):")
            for n, itens in res["sem_email"].items():
                print(" -", n, "->", len(itens), "audiência(s)")
        if res["sem_responsavel"]:
            print("\n### SEM RESPONSÁVEL NA PAUTA:")
            for t in res["sem_responsavel"]:
                print(" ", t)
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))
