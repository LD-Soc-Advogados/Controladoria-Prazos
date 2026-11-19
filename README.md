# Controladoria de Prazos — Lucchesi Dolabela

Sistema interno de controle de prazos judiciais e de pauta de audiências.
Operado pela **controladoria do escritório**.

> ⚠️ **Repositório privado.** Os arquivos aqui citam nome de parte, número de
> processo e os e-mails da equipe. Não torne este repositório público.

## O que o sistema resolve

A dor original: *"eu perco o controle de quem não me respondeu, porque é tudo pelo
e-mail."* O sistema fecha esse ciclo em quatro etapas:

1. **Busca** as publicações do dia (DJEN/CNJ e o clipping do webjur).
2. **Classifica** cada uma e estima o prazo fatal pelo CPC.
3. **Distribui** para o responsável, por e-mail, no modelo do escritório.
4. **Cobra** quem não respondeu e **dá baixa** em quem já cumpriu.

## As peças

| Arquivo | O que é |
|---|---|
| `painel-prazos.html` | O painel. É publicado como **Artifact do Claude** (não é site comum): triagem, prazos, cobrança, equipe, memória de teses e agenda. |
| `CLAUDE.md` | **O arquivo mais importante do repositório.** Arquitetura, decisões, e cada armadilha já encontrada — com a medição que a comprovou. Leia antes de mexer em qualquer coisa. |
| `pauta_emails.py` | Monta o e-mail individual de cada responsável a partir da planilha da pauta da semana. |
| `pauta_emails_teste.py` | Compara a saída com e-mails reais, caractere por caractere. Rode antes e depois de mexer no texto. |
| `pauta_pendentes.py` | Cruza as audiências que chegam por e-mail com a pauta do Drive: o que falta lançar e o que foi cancelado e continua na pauta. |
| `pauta_pendentes_teste.json` | Casos de teste do script acima. |
| `atas_cobranca.py` | Quais audiências ficaram sem ata — casando por processo, CIV e nome do cliente. |
| `ler_pdf.py` | Lê a ata em PDF. Extrai texto quando há; quando a ata é print, recorta o JPEG de dentro do PDF. Só com biblioteca padrão. |

As **rotinas agendadas** (seis) não ficam aqui: vivem em
`%USERPROFILE%\.claude\scheduled-tasks\`. O `CLAUDE.md` lista todas, com horário e
motivo de cada horário.

## Duas coisas que não são óbvias

**O painel não consulta o DJEN.** Ele roda num domínio cuja política de segurança
(CSP) proíbe chamar qualquer site externo — e a falha aparece como um erro de rede
genérico, o que já custou meio dia de diagnóstico errado. Quem busca é a rotina
agendada; o painel só lê o banco. Não reintroduza `fetch` ao DJEN no painel.

**Tarefa agendada só roda com o aplicativo do Claude aberto.** Computador desligado
no horário = não roda. Não prometa a ninguém que algo roda de madrugada sozinho.

## Antes de mexer

- **Leia o `CLAUDE.md` inteiro.** Quase tudo que parece estranho no código está
  explicado lá, com a medição que motivou a escolha.
- **Todo script tem teste, e todo teste usa dado real.** Rode antes e depois.
- **Errar para mais é o erro caro.** Em todo lugar onde há dúvida — se a região é a
  dela, se o advogado cumpriu, se a audiência foi cancelada — o sistema escolhe
  mostrar a mais, nunca esconder. Nunca inverta esse padrão: ver um caso a mais
  custa um clique, não ver um prazo custa o prazo.
