# -*- coding: utf-8 -*-
"""
Compara as audiências achadas nos e-mails com o que JÁ ESTÁ na pauta e diz o
que falta lançar.

Uso:
    python -I pauta_pendentes.py <achados.json> <2026.xlsx> <2027.xlsx>

⚠️ Passe SEMPRE as duas planilhas, 2026 e 2027: audiência marcada para janeiro é lançada
na de 2027, e procurar só na de 2026 faria o sistema dizer "não consta" para uma audiência
que está lançada — ou pior, deixar passar um cancelamento.

<achados.json> pode ser uma lista (só audiências) ou um objeto com as duas chaves:
{"audiencias": [...], "cancelamentos": [...]}

`audiencias` — o que foi marcado, montado por quem leu os e-mails:
[
  {"data": "2026-11-18", "hora": "10:00",
   "processo": "1106272-21.2025.8.26.0100",
   "nome": "JOSE ANGELO DA COSTA",
   "jec_vc": "Pré - Processual",        # só se o e-mail disser; senão ""
   "tipo": "Conciliação",               # só se o e-mail disser; senão ""
   "modalidade": "virtual, link no e-mail",
   "obs": "https://teams.microsoft.com/...",
   "origem": "assunto do e-mail"}
]

⚠️ Campo que o e-mail não disser fica VAZIO. Não invente CIV, responsável nem
instrução — isso é decisão da Luciana e vai em branco para ela preencher.

`cancelamentos` — e-mails que falam em cancelar ou redesignar. O caminho contrário:
audiência que caiu e continua na pauta.
[
  {"processo": "1004462-98.2026.8.13.0271",
   "situacao": "confirmado",      # "confirmado" = a vara disse que cancelou/redesignou
                                   # "pedido"     = só pedimos, ou a vara só acusou
   "trecho": "Bom dia! Foi cancelada a audiência.",   # a frase que justifica, literal
   "origem": "assunto do e-mail", "data_email": "2026-11-12"}
]

🔴 A diferença entre "confirmado" e "pedido" é a parte mais perigosa deste arquivo.
Tratar um "acuso recebimento" ou "repassamos ao setor responsável" como cancelamento faz
a audiência sair da pauta e **ninguém comparecer a uma audiência que continua de pé**.
Na dúvida, é "pedido". E o sistema **nunca** manda tirar da pauta — ele manda CONFERIR.

Saída: JSON com `nao_consta`, `data_diferente` (possível redesignação — é o
caso mais perigoso, porque a pauta fica com a data velha) e `ja_consta`,
mais `bloco`, que é o texto pronto para colar na planilha: as colunas vão
separadas por TAB, que é o que faz o Google Sheets distribuir em colunas.
"""
import json
import sys
from datetime import date, datetime

sys.path.insert(0, r"C:\Users\Usuario\Documents\Claude")
from pauta_emails import ler_pauta, titulo  # reaproveita o leitor da pauta

# ordem das colunas da pauta — não mude sem olhar a planilha
COLUNAS = ["Data", "Hora", "CIV", "Nome", "Processo", "JEC/VC", "Tipo",
           "Instrução", "Responsável", "Virtual/Presencial", "Obs"]


def digitos(processo):
    """Só os números. O e-mail manda com máscara, a planilha ora sim ora não."""
    return "".join(c for c in str(processo or "") if c.isdigit())


def como_data(txt):
    if isinstance(txt, date):
        return txt
    t = str(txt or "").strip()
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            pass
    return None


def indexar(caminhos):
    """processo (só dígitos) -> lista de (data, nome) já lançados na pauta."""
    idx = {}
    for c in caminhos:
        for r in ler_pauta(c):
            d = digitos(r["processo"])
            if len(d) >= 15:          # número de processo do CNJ tem 20
                idx.setdefault(d, []).append((r["data"], r["nome"]))
    return idx


def linha_para_colar(a):
    d = como_data(a.get("data"))
    campos = {
        "Data": d.strftime("%d/%m/%y") if d else "",
        "Hora": a.get("hora", ""),
        "CIV": "",
        "Nome": titulo(a.get("nome", "")),
        "Processo": a.get("processo", ""),
        "JEC/VC": a.get("jec_vc", ""),
        "Tipo": a.get("tipo", ""),
        "Instrução": "",
        "Responsável": "",
        "Virtual/Presencial": a.get("modalidade", ""),
        "Obs": a.get("obs", ""),
    }
    return "\t".join(campos[c] for c in COLUNAS)


def checar_cancelamentos(cancelamentos, idx, hoje):
    """Caminho contrário: o e-mail fala em cancelar/redesignar e a audiência
    continua na pauta, com data de hoje em diante."""
    ainda_na_pauta, ja_saiu = [], []
    for c in cancelamentos or []:
        d = digitos(c.get("processo"))
        if len(d) < 15:
            c["motivo"] = "número de processo incompleto no e-mail"
            ja_saiu.append(c)
            continue
        futuras = [dt for dt, _ in idx.get(d, []) if dt and dt >= hoje]
        if futuras:
            c["na_pauta"] = [dt.strftime("%d/%m/%Y") for dt in sorted(futuras)]
            ainda_na_pauta.append(c)
        else:
            ja_saiu.append(c)
    # confirmado primeiro: é o que ela resolve em um minuto
    ainda_na_pauta.sort(key=lambda x: (x.get("situacao") != "confirmado",
                                       x.get("na_pauta", [""])[0]))
    return ainda_na_pauta, ja_saiu


def comparar(achados, caminhos, cancelamentos=None, hoje=None):
    hoje = hoje or date.today()
    idx = indexar(caminhos)
    nao_consta, data_diferente, ja_consta, conferir = [], [], [], []

    for a in achados:
        d = digitos(a.get("processo"))
        alvo = como_data(a.get("data"))
        if len(d) < 15 or not alvo:
            a["motivo"] = ("número de processo incompleto no e-mail"
                           if len(d) < 15 else "sem data no e-mail")
            conferir.append(a)
            continue
        lancamentos = idx.get(d)
        if not lancamentos:
            nao_consta.append(a)
        elif any(dt == alvo for dt, _ in lancamentos):
            ja_consta.append(a)
        else:
            a["na_pauta"] = [dt.strftime("%d/%m/%Y") for dt, _ in lancamentos if dt]
            data_diferente.append(a)

    # ⚠️ Só o que NÃO CONSTA vai para o bloco de colar. Redesignação não se
    # cola: a linha já existe com a data velha e tem que ser CORRIGIDA, senão
    # a audiência fica duplicada na pauta. E processo incompleto nunca entra —
    # número errado na pauta é pior que linha faltando.
    bloco = "\n".join(linha_para_colar(a) for a in sorted(
        nao_consta, key=lambda x: (como_data(x.get("data")) or date.max, x.get("hora", ""))))

    cancel_na_pauta, cancel_ja_saiu = checar_cancelamentos(cancelamentos, idx, hoje)

    return {
        "processos_na_pauta": len(idx),
        "nao_consta": nao_consta,
        "data_diferente": data_diferente,
        "ja_consta": ja_consta,
        "conferir": conferir,
        "cancelada_ainda_na_pauta": cancel_na_pauta,
        "cancelada_ja_fora": cancel_ja_saiu,
        "bloco": bloco,
        "colunas": COLUNAS,
    }


if __name__ == "__main__":
    # utf-8-sig e não utf-8: o PowerShell grava JSON com BOM, e com `utf-8`
    # o json estoura em "Unexpected UTF-8 BOM". Medido em 16/11/2026.
    with open(sys.argv[1], encoding="utf-8-sig") as f:
        entrada = json.load(f)
    if isinstance(entrada, dict):
        achados = entrada.get("audiencias", [])
        cancelamentos = entrada.get("cancelamentos", [])
    else:
        achados, cancelamentos = entrada, []
    planilhas = [a for a in sys.argv[2:] if not a.startswith("--")]
    res = comparar(achados, planilhas, cancelamentos)
    if "--texto" in sys.argv:
        print("processos indexados na pauta:", res["processos_na_pauta"])
        print("\nNÃO CONSTA (%d):" % len(res["nao_consta"]))
        for a in res["nao_consta"]:
            print("  -", a.get("data"), a.get("hora"), a.get("processo"), "|", a.get("nome"))
        print("\nCONFERIR À MÃO (%d):" % len(res["conferir"]))
        for a in res["conferir"]:
            print("  -", a.get("origem"), "|", a.get("motivo"))
        print("\nCONSTA COM OUTRA DATA (%d):" % len(res["data_diferente"]))
        for a in res["data_diferente"]:
            print("  -", a.get("processo"), "| e-mail:", a.get("data"),
                  "| pauta:", ", ".join(a.get("na_pauta", [])))
        print("\nCANCELADA E AINDA NA PAUTA (%d):" % len(res["cancelada_ainda_na_pauta"]))
        for c in res["cancelada_ainda_na_pauta"]:
            print("  -", c.get("processo"), "| na pauta:", ", ".join(c.get("na_pauta", [])),
                  "|", c.get("situacao"), "|", (c.get("trecho") or "")[:60])
        print("\nCANCELAMENTO SEM REFLEXO NA PAUTA (%d)" % len(res["cancelada_ja_fora"]))
        print("\nJÁ CONSTA (%d)" % len(res["ja_consta"]))
        print("\n--- bloco para colar ---")
        print(res["bloco"])
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
