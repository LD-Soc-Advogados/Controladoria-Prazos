# -*- coding: utf-8 -*-
"""
Extrai o texto de um PDF usando SÓ a biblioteca padrão do Python.

Existe porque, em 16/11/2026, instalar `pypdf` no computador dela foi bloqueado e o
`pdftoppm` (poppler) não está instalado — então nem a leitura por imagem funciona.
Serve para as atas de audiência que chegam em PDF gerado pelo sistema do tribunal.

Uso:
    python -I ler_pdf.py <arquivo.pdf>

⚠️ **Só funciona em PDF com camada de texto.** Ata que é digitalização/print embrulhado
em PDF sai VAZIA — e aí o certo é dizer "não consegui ler, abra o anexo", nunca inventar.
O programa avisa sozinho: imprime `[SEM TEXTO EXTRAÍVEL]` e sai com código 2.
"""
import re
import sys
import zlib


def _fluxos(dados):
    """Devolve o conteúdo descomprimido de cada `stream ... endstream`."""
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", dados, re.S):
        bruto = m.group(1)
        try:
            yield zlib.decompress(bruto)
        except zlib.error:
            try:                                   # alguns vêm com lixo no fim
                yield zlib.decompressobj().decompress(bruto)
            except zlib.error:
                yield bruto                        # pode estar sem compressão


def _texto_de_literal(b):
    """Converte um literal PDF `(...)` em texto, tratando escapes e octais."""
    saida, i = bytearray(), 0
    while i < len(b):
        c = b[i]
        if c == 0x5C and i + 1 < len(b):           # barra invertida
            p = b[i + 1]
            mapa = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}
            if p in mapa:
                saida.append(mapa[p]); i += 2
            elif 0x30 <= p <= 0x37:                # \ddd octal
                j = i + 1
                oct_ = b""
                while j < len(b) and len(oct_) < 3 and 0x30 <= b[j] <= 0x37:
                    oct_ += bytes([b[j]]); j += 1
                saida.append(int(oct_, 8) & 0xFF); i = j
            else:
                saida.append(p); i += 2
        else:
            saida.append(c); i += 1
    # as atas do PJe saem em WinAnsi/Latin-1; utf-8 primeiro por segurança
    for cod in ("utf-8", "cp1252", "latin-1"):
        try:
            return saida.decode(cod)
        except UnicodeDecodeError:
            continue
    return saida.decode("latin-1", "replace")


def extrair(caminho):
    with open(caminho, "rb") as f:
        dados = f.read()
    linhas = []
    for fluxo in _fluxos(dados):
        if b"Tj" not in fluxo and b"TJ" not in fluxo:
            continue
        atual = []
        for m in re.finditer(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>|T[dDJj*]|'|\"",
                             fluxo, re.S):
            t = m.group(0)
            if t.startswith(b"("):
                atual.append(_texto_de_literal(t[1:-1]))
            elif t.startswith(b"<"):               # string hexadecimal
                hexa = re.sub(rb"\s", b"", t[1:-1])
                if len(hexa) % 2 == 0:
                    try:
                        atual.append(bytes.fromhex(hexa.decode()).decode("utf-16-be",
                                                                        "replace"))
                    except ValueError:
                        pass
            elif t in (b"Td", b"TD", b"T*", b"'", b'"'):
                if atual:
                    linhas.append("".join(atual)); atual = []
        if atual:
            linhas.append("".join(atual))
    texto = "\n".join(_sem_lixo(linhas))
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _sem_lixo(linhas):
    """Joga fora as linhas que são ruído e mantém as que são texto.

    ⚠️ Medido em 16/11/2026 e já custou duas atas: um mesmo PDF traz o texto bom
    E fluxos de imagem/fonte que viram caracteres aleatórios. Olhando o arquivo
    inteiro de uma vez, a proporção de lixo derrubava tudo (0,30 e 0,64 de
    caracteres plausíveis) e a ata legível era descartada junto. A limpeza é
    por LINHA: linha ruim sai, linha boa fica."""
    boas = []
    for linha in linhas:
        if not linha.strip():
            continue
        bons = sum(1 for c in linha if c in BONS)
        if bons >= 3 and bons / len(linha) >= 0.70:
            boas.append(linha)
    return boas


BONS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ"
    "0123456789 \n\t.,;:!?()[]{}/\\-–—_'\"°ºª§%$&*+=<>@#\r"
)

# toda ata de audiência tem pelo menos duas destas
PALAVRAS = ("audi", "process", "concilia", "juiz", "parte", "autor", "réu", "reu",
            "advog", "termo", "acordo", "sessão", "sessao", "designad")


# Marcas que só aparecem no CORPO de uma ata, nunca na capa do PJe.
# "audiência" ficou de fora de propósito: a capa traz "Ata de audiência no
# CEJUSC" como nome do documento e passaria por corpo.
CORPO = ("presen", "delibera", "homolog", "acordo", "conciliador", "realizada",
         "designad", "requer", "manifesta", "infrutífer", "infrutifer",
         "logrou", "termo de audi", "aberta a")


def so_a_capa(t):
    """Verdadeiro quando o PDF só tem a FOLHA DE ROSTO do PJe e a ata em si é
    imagem.

    🔴 Medido em 16/11/2026 com as atas da Kawan (Lucineude) e do Clévio
    (Debora): o PDF do PJe traz uma capa em texto — número, classe, partes,
    "Assinado eletronicamente" — e a ata propriamente dita como imagem que não
    é JPEG, logo não dá para recortar. Sem esta checagem o script devolvia a
    CAPA como se fosse a ata, e a rotina concluiria "sem prazo" **sem nunca ter
    visto a ata**. É o pior erro possível aqui: silencioso e tranquilizador."""
    b = t.lower()
    tem_capa = ("assinado eletronicamente" in b or "pje" in b) and "classe:" in b
    tem_corpo = any(p in b for p in CORPO)
    return tem_capa and not tem_corpo


def parece_texto(t):
    """Trava contra lixo. Extrair fluxo de IMAGEM como se fosse texto devolve
    milhares de caracteres aleatórios — e um resumo feito em cima disso seria
    invenção pura. Aconteceu de verdade em 16/11/2026 com o print do Lucas:
    45.470 caracteres de ruído que passariam por ata."""
    if len(t) < 120:
        return False
    bons = sum(1 for c in t if c in BONS) / len(t)
    achadas = sum(1 for p in PALAVRAS if p in t.lower())
    return bons >= 0.90 and achadas >= 2


def extrair_imagens(caminho, destino):
    """Tira as imagens JPEG de dentro do PDF — é nelas que está o 'print da ata'.
    JPEG já vem pronto dentro do PDF (DCTDecode), então é só recortar os bytes."""
    import os
    # cria a pasta se não existir: a rotina roda sozinha e não pode cair por isso
    os.makedirs(destino, exist_ok=True)
    with open(caminho, "rb") as f:
        dados = f.read()
    salvos = []
    for i, m in enumerate(re.finditer(rb"/DCTDecode.*?stream\r?\n", dados, re.S), 1):
        ini = m.end()
        fim = dados.find(b"\xff\xd9", ini)          # fim de JPEG
        if fim == -1:
            continue
        recorte = dados[ini:fim + 2]
        if not recorte.startswith(b"\xff\xd8"):     # começo de JPEG
            p = recorte.find(b"\xff\xd8")
            if p == -1:
                continue
            recorte = recorte[p:]
        nome = os.path.join(destino, "ata_imagem_%d.jpg" % i)
        with open(nome, "wb") as g:
            g.write(recorte)
        salvos.append(nome)
    return salvos


if __name__ == "__main__":
    t = extrair(sys.argv[1])
    if parece_texto(t) and so_a_capa(t):
        # Tem texto, mas é só a folha de rosto do PJe. Tenta a imagem; se não
        # houver, diga que NÃO LEU — nunca resuma a capa como se fosse a ata.
        if "--imagens" in sys.argv:
            destino = sys.argv[sys.argv.index("--imagens") + 1]
            salvos = extrair_imagens(sys.argv[1], destino)
            if salvos:
                print("[ATA EM IMAGEM] leia com os próprios olhos:")
                for s in salvos:
                    print(s)
                sys.exit(3)
        print("[SÓ A CAPA DO PJe] a ata em si é imagem e não deu para recortar — "
              "abra o anexo no e-mail")
        sys.exit(4)
    if not parece_texto(t):
        # Não é PDF de texto: é digitalização ou print. Tenta soltar a imagem
        # para alguém OLHAR — nunca resuma o que saiu da extração.
        if "--imagens" in sys.argv:
            destino = sys.argv[sys.argv.index("--imagens") + 1]
            salvos = extrair_imagens(sys.argv[1], destino)
            if salvos:
                print("[ATA EM IMAGEM] leia com os próprios olhos:")
                for s in salvos:
                    print(s)
                sys.exit(3)
        print("[SEM TEXTO EXTRAÍVEL]")
        sys.exit(2)
    # --saida grava em UTF-8. Prefira isso a ler do console: o console do
    # Windows estraga os acentos, e ata com acento errado vira leitura errada.
    if "--saida" in sys.argv:
        destino = sys.argv[sys.argv.index("--saida") + 1]
        with open(destino, "w", encoding="utf-8") as f:
            f.write(t)
        print("texto gravado em", destino, "(%d caracteres)" % len(t))
    else:
        print(t)
