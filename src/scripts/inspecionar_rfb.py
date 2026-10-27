"""
Script de reconhecimento da RFB (roda à mão, uma vez).

Objetivo: descobrir o código dentro ca Receita Federal Brasileira de Joinville.
Não é o collector, mas as funções de listar e baixar
serão reaproveitadas nele depois.


"""

import re
import time
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import requests

from src.core.settings import settings


# ─────────────── Constantes montadas a partir do settings ───────────────

WEBDAV_URL = settings.RFB_BASE_URL + settings.RFB_WEBDAV_PATH
# -> "https://arquivos.receitafederal.gov.br/public.php/webdav"

AUTENTICACAO = (settings.RFB_SHARE_TOKEN, "")
# -> usuário = token, senha = vazia (padrão do Nextcloud público)

PASTA_TEMP = Path(settings.RFB_PASTA_TEMP)

TAMANHO_PEDACO = 1024 * 1024  # 1 MB

# Qual o motivo de montar aqui em cima: as funções usam os mesmos valores.
# Montando uma vez só, não tem como uma montar diferente da outra.


# ════════════════════════════════════════════════════════════════
#  1. LISTAR COMPETÊNCIAS
# ════════════════════════════════════════════════════════════════

def listar_competencias():
    resposta = requests.request(
        method="PROPFIND",
        url=WEBDAV_URL + "/",
        auth=AUTENTICACAO,
        headers={"Depth": "1"},
        timeout=settings.RFB_TIMEOUT_SEGUNDOS,
    )

    if resposta.status_code != 207:
        raise RuntimeError(
            f"Listagem falhou: status {resposta.status_code}\n{resposta.text[:500]}"
        )

    encontrados = re.findall(r"/(\d{4}-\d{2})/", resposta.text)
    competencias = sorted(set(encontrados))

    if not competencias:
        raise RuntimeError(
            "Nenhuma pasta AAAA-MM encontrada. A estrutura do servidor mudou?"
        )

    return competencias

# Motivo de "PROPFIND": no WebDAV, é o comando "me diz o que tem nessa pasta",
# pois assim não existe requests.propfind(), por isso usa requests.request() com o nome.
# "Depth: 1": lista só o primeiro nível (as pastas AAAA-MM).
# 207: "Multi-Status" é o sucesso do PROPFIND, não 200.
# A resposta.text[:500] no erro: mostra o começo da resposta do
# servidor, ajuda a entender o que deu errado sem lotar o terminal.
# A regex tem "/" dos dois lados: pega só o que aparece como
# PASTA no caminho ("/2026-09/"), evitando falso positivo em datas
# que possam aparecer em outros pontos do XML.
# sorted(set(...)): tira repetidos e ordena. "AAAA-MM" em ordem
# alfabética = ordem cronológica -> a mais recente fica no FIM.


# ════════════════════════════════════════════════════════════════
#  2. BAIXAR ARQUIVO
# ════════════════════════════════════════════════════════════════

def baixar_arquivo(competencia, nome_arquivo):
    url = f"{WEBDAV_URL}/{competencia}/{nome_arquivo}"
    PASTA_TEMP.mkdir(parents=True, exist_ok=True)
    destino = PASTA_TEMP / nome_arquivo

    for tentativa in range(1, settings.RFB_TENTATIVAS + 1):
        try:
            with requests.get(
                    url,
                    auth=AUTENTICACAO,
                    stream=True,
                    timeout=settings.RFB_TIMEOUT_SEGUNDOS,
            ) as resposta:
                resposta.raise_for_status()

                with open(destino, "wb") as arquivo:
                    for pedaco in resposta.iter_content(chunk_size=TAMANHO_PEDACO):
                        arquivo.write(pedaco)

            return destino

        except requests.RequestException as erro:
            if destino.exists():
                destino.unlink()  # arquivo pela metade

            print(f"Tentativa {tentativa}/{settings.RFB_TENTATIVAS} falhou: {erro}")

            if tentativa < settings.RFB_TENTATIVAS:
                espera = tentativa * 10
                print(f"Aguardando {espera}s antes de tentar de novo...")
                time.sleep(espera)

    raise RuntimeError(
        f"Download falhou após {settings.RFB_TENTATIVAS} tentativas: {url}"
    )

# Assim funciona o auth aqui também: sem o token, o Nextcloud responde 401.
# Motivo de stream=True + pedaços de 1 MB: vai para o disco aos poucos.
# Sem isso, o arquivo inteiro vai para memória antes de salvar.
# Municipios aguenta, já estabelecimentos (GBs) derruba o processo.
# Motivo deraise_for_status(): sem isso, uma página de erro 404 seria
# salva como "Municipios.zip" e o erro só apareceria ao abrir o zip.
# Porque "wb": escrita binária. Zip não é texto.
# Motivo de apagar o arquivo pela metade: zip cortado parece válido.
# Aqui o range(1, N + 1): range não inclui o último número.
# range(1, 4) gera 1, 2, 3.
# Aqui a espera crescente: servidor sobrecarregado precisa de fôlego.


# ════════════════════════════════════════════════════════════════
#  3. PROCURAR JOINVILLE
# ════════════════════════════════════════════════════════════════

def procurar_joinville(caminho_zip):
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        nomes = arquivo_zip.namelist()

        if len(nomes) != 1:
            print(f"⚠️  Esperava 1 arquivo no zip, achei {len(nomes)}: {nomes}")

        nome_interno = nomes[0]
        print(f"Arquivo dentro do zip: {nome_interno}")

        with arquivo_zip.open(nome_interno) as arquivo_csv:
            tabela = pd.read_csv(
                arquivo_csv,
                sep=";",
                header=None,
                encoding="latin-1",
                dtype=str,
                names=["codigo", "nome"],
            )

    print("\nPrimeiras linhas:")
    print(tabela.head(3))
    print(f"\nTotal de municípios: {len(tabela)}")

    achados = tabela[tabela["nome"].str.contains("JOINVILLE", na=False)]

    if achados.empty:
        print("\n❌ Joinville não encontrado. Conferir o layout.")
    elif len(achados) > 1:
        print("\n⚠️  Mais de um resultado. Confira qual é o de SC:")
        print(achados)
    else:
        codigo = achados.iloc[0]["codigo"]
        print(f"\n✅ Código RFB de Joinville: {codigo}")

    return achados

# Aqui o "arquivo_zip" e não "zip": zip já é uma função do Python.
# Usar o mesmo nome "esconde" a original dentro da função.
# Assim nomes[0]: o nome interno é estranho e muda a cada competência.
# Pois ler direto do zip: não precisa descompactar no disco.
# Porque header=None: o CSV da RFB NÃO tem cabeçalho.
# Porque latin-1: a Receita usa ISO-8859-1. Com utf-8, acentos quebram.
# Pois dtype=str: preserva zeros à esquerda do código.
# Aqui head(3) + total: primeira prova do layout. Total esperado ~5.570.
# Pois na=False: se alguma linha tiver nome vazio, conta como
# "não contém" em vez de dar erro.
# Porque iloc[0]: pega a primeira linha pela POSIÇÃO, independente
# do número de índice que ela tinha na tabela original.



# ════════════════════════════════════════════════════════════════
#  4. INSPECIONAR ESTABELECIMENTOS
# ════════════════════════════════════════════════════════════════

# Posição da coluna no CSV (começando em 0) -> nome que vamos usar.
# Fonte: layout oficial dos dados abertos do CNPJ (PDF da Receita).
COLUNAS_ESTABELECIMENTOS = {
    0: "cnpj_basico",
    5: "situacao_cadastral",
    6: "data_situacao_cadastral",
    10: "data_inicio_atividade",
    11: "cnae_fiscal_principal",
    19: "uf",
    20: "municipio",
}

TAMANHO_BLOCO = 500_000  # linhas por vez


def inspecionar_estabelecimentos(caminho_zip):
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        nome_interno = arquivo_zip.namelist()[0]
        print(f"Arquivo dentro do zip: {nome_interno}")

        # Parte 1: só 5 linhas, todas as colunas -> conferir o layout
        with arquivo_zip.open(nome_interno) as arquivo_csv:
            amostra = pd.read_csv(
                arquivo_csv,
                sep=";",
                header=None,
                encoding="latin-1",
                dtype=str,
                nrows=5,
            )

        print(f"\nQuantidade de colunas: {amostra.shape[1]} (esperado: 30)")
        print("\nColunas que vamos usar (primeira linha do arquivo):")
        for posicao, nome in COLUNAS_ESTABELECIMENTOS.items():
            print(f"  [{posicao:>2}] {nome:<25} = {amostra.iloc[0, posicao]}")

        # Parte 2: arquivo inteiro, em blocos, só as colunas úteis
        total_linhas = 0
        blocos_joinville = []

        with arquivo_zip.open(nome_interno) as arquivo_csv:
            leitor = pd.read_csv(
                arquivo_csv,
                sep=";",
                header=None,
                encoding="latin-1",
                dtype=str,
                usecols=list(COLUNAS_ESTABELECIMENTOS),
                chunksize=TAMANHO_BLOCO,
            )

            for bloco in leitor:
                total_linhas += len(bloco)
                bloco = bloco.rename(columns=COLUNAS_ESTABELECIMENTOS)
                filtro = bloco["municipio"] == settings.RFB_MUNICIPIO_JOINVILLE
                blocos_joinville.append(bloco[filtro])
                print(f"  ... {total_linhas:,} linhas lidas")

    joinville = pd.concat(blocos_joinville, ignore_index=True)

    print(f"\nTotal de linhas no arquivo: {total_linhas:,}")
    print(f"Estabelecimentos de Joinville neste arquivo: {len(joinville):,}")

    print("\nUF dos estabelecimentos de Joinville (esperado: só SC):")
    print(joinville["uf"].value_counts())

    print("\nSituação cadastral em Joinville:")
    print(joinville["situacao_cadastral"].value_counts())

    print("\nExemplos de data de abertura e CNAE:")
    print(joinville[["data_inicio_atividade", "cnae_fiscal_principal"]].head(3))

    return joinville

# Porque nrows=5 na parte 1: pra ver o layout não precisa ler 2 GB.
# Porque abrir o zip duas vezes: o arquivo é lido em sequência, como uma fita.
# Depois de ler as 5 linhas, o jeito simples de voltar ao começo é abrir de novo.
# Porque usecols: lê só 7 das 30 colunas. Menos memória, e dados como
# nome fantasia, endereço, telefone e e-mail nem passam pelo programa.
# Porque chunksize: o pandas entrega o arquivo em pedaços de 500 mil linhas.
# Cada pedaço é filtrado e descartado, então a memória não explode.
# Porque a coluna "uf": prova cruzada. Se o código 8179 estiver certo,
# todos os estabelecimentos achados têm que ser de SC.

# ════════════════════════════════════════════════════════════════
#  PROGRAMA PRINCIPAL
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    competencias = listar_competencias()
    mais_recente = competencias[-1]
    print(f"Usando: {mais_recente}\n")

    caminho = PASTA_TEMP / "Estabelecimentos0.zip"

    if caminho.exists():
        print("Arquivo já baixado antes, reaproveitando.\n")
    else:
        inicio = time.time()
        caminho = baixar_arquivo(mais_recente, "Estabelecimentos0.zip")
        duracao = time.time() - inicio
        tamanho_mb = caminho.stat().st_size / 1024 / 1024
        print(f"Baixado: {tamanho_mb:.1f} MB em {duracao / 60:.1f} min\n")

    inicio = time.time()
    inspecionar_estabelecimentos(caminho)
    print(f"\nTempo de leitura: {(time.time() - inicio) / 60:.1f} min")

