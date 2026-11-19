# Melhorias prontas que ainda NÃO foram publicadas

Cada `.patch` aqui é uma mudança do painel que ficou **escrita e conferida no
estático, mas nunca executada**. Não publique nenhuma delas sem rodar o teste no
navegador: o painel inteiro vive num `<script>` só, então **um erro de sintaxe
derruba a tela toda**, não apenas o botão novo.

## Como aplicar e testar

```bash
git apply melhorias-pendentes/<arquivo>.patch
```

Depois sirva o painel e abra no navegador (o procedimento está no `CLAUDE.md`,
em "Aba Prazos agrupada por responsável"): copie `painel-prazos.html` para a
pasta temporária com `<!doctype html><meta charset="utf-8">` na frente e sirva
com `python -m http.server` pelo `preview_start`. **Não sirva a pasta do
projeto** — ela tem o `CLAUDE.md` e os dados da equipe.

⚠️ `preview_start` **pede aprovação da Luciana**. Numa rodada agendada, sem
ninguém na frente do computador, ela é recusada e o teste não roda — foi
exatamente o que aconteceu em 17/11/2026. Arquivo em `file://` **não serve**: o
painel abre como instantâneo estático e o JavaScript não executa.

Testado e publicado, apague o `.patch`.

---

## `2026-11-17-ficou-algo-para-tras.patch`

**Botão "Ficou algo para trás?" na aba Triagem.**

O painel abre no período de hoje (`periodoPadrao`). Está certo no dia a dia, mas
esconde dois casos medidos na rodada de 17/11/2026:

- **02/11 tinha 27 publicações do Nordeste sem nenhum prazo lançado.** Entraram
  no banco na recuperação histórica das três OAB do Louis e nunca passaram pela
  triagem. Como o painel nunca abre naquele dia, ninguém ia olhar.
- **156 publicações de 16/11 foram acrescentadas depois** que ela já tinha
  trabalhado o dia, quando o DJEN se recuperou. Dia já trabalhado pode receber
  publicação nova — a triagem de ontem não é definitiva.

O botão varre os dias guardados e diz, por dia, quantas publicações da região
escolhida continuam sem prazo lançado, com um botão para abrir o período.
Não grava nada e não decide nada.

É **sob demanda de propósito**: varrer os 15 dias custa dezenas de leituras no
banco, e pendurar isso na abertura deixaria a tela lenta todo dia para responder
uma pergunta ocasional.

### O que ainda precisa ser conferido no navegador

1. O botão aparece na barra da Triagem e a caixa `#atrasadasBox` renderiza
   acima da lista.
2. `listarDiasGuardados()` — **este é o ponto incerto.** Ele chama
   `S.db.collection("publicacoes").get()` para listar a coleção de primeiro
   nível. O resto do painel só lista **subcoleção**
   (`publicacoes/<data>/itens`), então essa chamada nunca foi exercitada aqui.
   Se o wrapper do banco não suportar, o `try/catch` mostra o erro na caixa e
   nada mais quebra — mas o botão não serve para nada até ser trocado por um
   laço de datas com `lerDia`.
3. A contagem bate com o medido em 17/11/2026: **02/11 → 27** publicações do
   Nordeste sem prazo lançado.
4. O botão "Abrir DD/MM a DD/MM" preenche as duas datas e carrega o período.
5. Com o filtro em "Nordeste", pré-processual de outro estado continua contando
   (é a exceção de sempre).
