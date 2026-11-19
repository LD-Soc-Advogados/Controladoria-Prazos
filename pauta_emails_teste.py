# -*- coding: utf-8 -*-
"""Compara o que o motor gera com os e-mails REAIS enviados em 13/11/2026."""
import sys
sys.path.insert(0, r"C:\Users\Usuario\Documents\Claude")
import pauta_emails

REAIS = {
    "kawan.lacerda@lucchesidolabela.com.br": (
        "Sua audi\u00eancia \u2013 16/11",
        "Oi, Kawan!\n\nSegue a audi\u00eancia da semana em que voc\u00ea est\u00e1 como respons\u00e1vel "
        "(o convite tamb\u00e9m est\u00e1 no Google Agenda):\n\n"
        "- 16/11 (seg) 13:30 \u2013 Concilia\u00e7\u00e3o \u2013 Dalva Lucia Dos Santos Bevilaqua \u2013 "
        "4001354-61.2026.8.26.0137 \u2013 virtual, link nos autos\n\n"
        "Qualquer d\u00favida, me chama.\n\nLuciana"),
    "barbaraorsini@lucchesidolabela.com.br": (
        "Sua audi\u00eancia \u2013 19/11",
        "Oi, B\u00e1rbara!\n\nSegue a audi\u00eancia da semana em que voc\u00ea est\u00e1 como respons\u00e1vel "
        "(o convite tamb\u00e9m est\u00e1 no Google Agenda):\n\n"
        "- 19/11 (qui) 14:00 \u2013 AIJ \u2013 Luciana De Oliveira \u2013 "
        "1001295-84.2026.8.13.0720 \u2013 virtual, link nos autos (com Ludmila)\n\n"
        "Qualquer d\u00favida, me chama.\n\nLuciana"),
    "clevio.lustoza@lucchesidolabela.com.br": (
        "Suas audi\u00eancias \u2013 16 a 19/11",
        "Oi, Cl\u00e9vio!\n\nSeguem as audi\u00eancias da semana em que voc\u00ea est\u00e1 como respons\u00e1vel "
        "(os convites tamb\u00e9m est\u00e3o no Google Agenda):\n\n"
        "- 17/11 (ter) 16:00 \u2013 Concilia\u00e7\u00e3o \u2013 Denise Gave De Melo \u2013 "
        "5040082-73.2026.8.08.0035 \u2013 fizemos requerimento virtual\n"
        "- 18/11 (qua) 14:00 \u2013 Concilia\u00e7\u00e3o \u2013 Claudia Maria Sant Anna Das Neves \u2013 "
        "5000333-25.2026.8.08.0043 \u2013 virtual, verificar link\n\n"
        "Qualquer d\u00favida, me chama.\n\nLuciana"),
}

res = pauta_emails.monta(sys.argv[1])
gerados = {e["email"]: e for e in res["emails"]}
falhas = 0
for email, (assunto, corpo) in REAIS.items():
    g = gerados.get(email)
    if not g:
        print("FALHA: nao gerou e-mail para", email); falhas += 1; continue
    if g["assunto"] != assunto:
        print("FALHA assunto", email); print("  real:", repr(assunto)); print("  gerado:", repr(g["assunto"])); falhas += 1
    if g["corpo"] != corpo:
        print("FALHA corpo", email)
        for a, b in zip(corpo.split("\n"), g["corpo"].split("\n")):
            if a != b:
                print("  real  :", repr(a)); print("  gerado:", repr(b))
        falhas += 1
    if g["assunto"] == assunto and g["corpo"] == corpo:
        print("OK identico:", email)
print("\n%d/%d identicos" % (len(REAIS) - falhas, len(REAIS)))
print("destinatarios gerados:", len(gerados))
print("sem e-mail cadastrado:", list(res["sem_email"]))
print("sem responsavel:", len(res["sem_responsavel"]))
