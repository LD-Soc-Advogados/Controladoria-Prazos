# -*- coding: utf-8 -*-
"""
Diz quais audiências de um período ainda estão SEM ata enviada.

Uso:
    python -I atas_cobranca.py <entrada.json> <2026.xlsx> <2027.xlsx> [--texto]

<entrada.json>:
{
  "de": "2026-11-09",          # primeiro dia a conferir (ou use "data" para um dia só)
  "ate": "2026-11-13",         # último dia
  "atas": [                    # uma entrada por e-mail de ata encontrado
    {"assunto": "AUDIENCIA - 12/11/2026 - 09:00 - CIV1756396 - Albano Ribeiro Da Trindade",
     "de": "lucas@lucchesidolabela.com.br",
     "data": "2026-11-12",
     "texto": "corpo/snippet do e-mail, opcional"}
  ]
}

🔴 **POR QUE NÃO BASTA O NÚMERO DO PROCESSO.** Medido em 16/11/2026 na semana de 09 a
13/11: casando só pelo número, 31 das 37 audiências apareciam como "sem ata" — e várias
tinham. O assunto que a equipe escreve quase nunca traz o número do CNJ; traz o **CIV**
("CIV1756396") ou só o **nome do cliente** ("🏛️ Audiência | ERIKA MIGUEL DA COSTA").
Por isso este arquivo casa por TRÊS chaves, com pesos diferentes.

| Chave | Confiança | Vai para |
|---|---|---|
| número do processo (20 dígitos) | certa | `com_ata` |
| CIV | certa | `com_ata` |
| nome do cliente | provável | `provavel` — ela confere |

⚠️ O nome **não** entra em `com_ata` de propósito: há cliente com duas audiências na mesma
semana (a Leidjane Batista Peixoto Aderne, 10 e 12/11, processos diferentes). Casar pelo
nome marcaria as duas como entregues e **esconderia uma ata que falta** — que é justamente
o erro caro. Ruído a mais ela descarta num olhar; ata escondida ninguém recupera.

⚠️ Isto NÃO diz que a pessoa não trabalhou — diz que a ata não foi localizada **no e-mail
dela**. Ata entregue por WhatsApp ou direto no sistema aparece aqui como faltando. O texto
para ela é "não localizei a ata", nunca "fulano não enviou".
"""
import json
import re
import sys
import unicodedata

sys.path.insert(0, r"C:\Users\Usuario\Documents\Claude")
from pauta_emails import ler_pauta
from pauta_pendentes import digitos, como_data

CNJ = re.compile(r"\d{7}[-.\s]?\d{2}[-.\s]?\d{4}[-.\s]?\d[-.\s]?\d{2}[-.\s]?\d{4}")
CNJ_CRU = re.compile(r"\b\d{20}\b")
CIV = re.compile(r"CIV\s?-?\s?(\d{6,8})", re.I)


def chave_nome(n):
    """Nome sem acento, sem pontuação, em maiúsculas — para comparar."""
    n = unicodedata.normalize("NFKD", str(n or ""))
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^A-Z ]", " ", n.upper())


def indexar_atas(atas):
    """Tira do assunto/corpo de cada ata as três chaves possíveis."""
    processos, civs, nomes = {}, {}, []
    for a in atas:
        texto = " ".join([a.get("assunto") or "", a.get("texto") or ""])
        marca = {"assunto": a.get("assunto"), "de": a.get("de"), "data": a.get("data")}
        for p in CNJ.findall(texto) + CNJ_CRU.findall(texto):
            if len(digitos(p)) == 20:
                processos[digitos(p)] = marca
        for c in CIV.findall(texto):
            civs[c.lstrip("0")] = marca
        nomes.append((chave_nome(texto), marca))
    return processos, civs, nomes


# "da/de/do/das/dos/e" não identificam ninguém e atrapalham a comparação
LIGACOES = {"DA", "DE", "DO", "DAS", "DOS", "E", "DI", "DU"}


def partes_do_nome(nome):
    return [p for p in chave_nome(nome).split() if len(p) >= 3 and p not in LIGACOES]


def casa_nome(nome_pauta, nomes):
    """Nome do cliente citado no assunto da ata.

    Exige que **todas** as palavras do nome apareçam no texto da ata, e pelo menos
    duas. Não compara em sequência de propósito: a pauta escreve "Maria Das Gracas
    De Araujo Santos" e o assunto escreve "MARIA DAS GRACAS DE ARAUJO SANTOS" ou
    "Maria Gracas Araujo" — exigir o par colado perdia esses casos.
    Com o mínimo de duas palavras, "Ana Pereira Niz" casa e "Maria" sozinha não."""
    alvo = partes_do_nome(nome_pauta)
    if len(alvo) < 2:
        return None
    for texto, marca in nomes:
        if all(p in texto for p in alvo):
            return marca
    return None


def conferir(entrada, caminhos):
    d1 = como_data(entrada.get("de") or entrada.get("data"))
    d2 = como_data(entrada.get("ate") or entrada.get("data"))
    if not d1 or not d2:
        raise SystemExit("informe 'de' e 'ate' (ou 'data') em entrada.json")

    processos, civs, nomes = indexar_atas(entrada.get("atas", []))
    com, provavel, sem = [], [], []
    vistos = set()

    for caminho in caminhos:
        for r in ler_pauta(caminho):
            if not r["data"] or not (d1 <= r["data"] <= d2):
                continue
            d = digitos(r["processo"])
            if len(d) < 15 or d in vistos:
                continue
            vistos.add(d)
            item = {
                "data": r["data"].strftime("%d/%m/%Y"), "hora": r["hora"],
                "nome": r["nome"], "processo": r["processo"], "civ": r.get("civ", ""),
                "responsavel": r["responsavel_bruto"], "tipo": r["tipo"],
            }
            civ = re.sub(r"\D", "", r.get("civ", "")).lstrip("0")
            marca = processos.get(d) or (civs.get(civ) if civ else None)
            if marca:
                item["ata"] = marca
                com.append(item)
                continue
            marca = casa_nome(r["nome"], nomes)
            if marca:
                item["ata"] = marca
                provavel.append(item)
            else:
                sem.append(item)

    ordem = lambda x: (x["data"][6:] + x["data"][3:5] + x["data"][:2], x["hora"])
    return {
        "periodo": "%s a %s" % (d1.strftime("%d/%m/%Y"), d2.strftime("%d/%m/%Y")),
        "total_na_pauta": len(vistos),
        "atas_lidas": len(entrada.get("atas", [])),
        "com_ata": sorted(com, key=ordem),
        "provavel": sorted(provavel, key=ordem),
        "sem_ata": sorted(sem, key=ordem),
    }


if __name__ == "__main__":
    # O console do Windows é cp1252 e estoura em emoji — e os assuntos da equipe
    # têm 🏛️. `errors="replace"` troca o que não couber em vez de derrubar tudo.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # utf-8-sig: o PowerShell grava JSON com BOM e `utf-8` estouraria.
    with open(sys.argv[1], encoding="utf-8-sig") as f:
        entrada = json.load(f)
    planilhas = [a for a in sys.argv[2:] if not a.startswith("--")]
    res = conferir(entrada, planilhas)
    if "--texto" in sys.argv:
        print("Período:", res["periodo"], "| audiências na pauta:", res["total_na_pauta"],
              "| e-mails de ata lidos:", res["atas_lidas"])
        print("\nSEM ATA (%d):" % len(res["sem_ata"]))
        for a in res["sem_ata"]:
            print("  -", a["data"], a["hora"], "|", a["nome"][:34], "|", a["processo"],
                  "|", a["responsavel"])
        print("\nPROVÁVEL, CONFERIR (%d) — casou pelo nome do cliente:" % len(res["provavel"]))
        for a in res["provavel"]:
            print("  -", a["data"], a["hora"], "|", a["nome"][:34], "|", a["responsavel"],
                  "->", (a["ata"]["assunto"] or "")[:50])
        print("\nCOM ATA (%d)" % len(res["com_ata"]))
        for a in res["com_ata"]:
            print("  -", a["data"], a["hora"], "|", a["nome"][:34], "|", a["responsavel"])
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
