from src.core.settings import settings

# Começa importando a config, não repete a URL por aqui


def listar_competencias():
    # 1. Fazer um GET na RFB_BASE_URL (é uma página HTML de listagem de pastas)
    # 2. Procurar na página por todos os textos no formato AAAA-MM
    # -> Expressão regular: 4 dígitos, hífen, 2 dígitos
    # 3. Excluir duplicados e ordenar
    # 4. Retornar a lista
    #
    # A RFB não tem API que diga qual é a competência mais recente.
    # A única forma é ler a lista de pastas. Essa mesma lógica
    # vira o descobrir_competencia_mais_recente() do collector.
    ...


def baixar_arquivo(competencia, nome_arquivo):
    # 1. Montar a URL: RFB_BASE_URL / competencia / nome_arquivo
    # 2. Criar a RFB_PASTA_TEMP caso não exista
    # 3. Para tentativa de 1 até RFB_TENTATIVAS:
    #        tentar:
    #            abrir a requisição em modo STREAMING (stream=True)
    #            abrir o arquivo de destino em modo binário
    #            para cada pedaço de ~1 MB que chegar:
    #                escrever o pedaço no arquivo
    #            retornar o caminho do arquivo
    #        se der erro de rede/timeout:
    #            logar "tentativa X falhou"
    #            esperar (tentativa * 10) segundos <- espera crescente
    # 4. Se todas falharem: levantar erro
    #
    # Streaming: sem ele, o requests guarda o arquivo
    # INTEIRO na RAM antes de salvar. Com Municipios (pequeno) não faz
    # diferença, mas com Estabelecimentos (GBs) o processo morre.
    # Já escreve do jeito certo hoje pra reaproveitar no collector.
    #
    # Espera crescente: se o servidor da Receita está
    # sobrecarregado, bater de novo na hora só piora. É dar tempo
    # para o defensor voltar antes de atacar de novo.
    ...


def procurar_joinville(caminho_zip):
    # 1. Abrir o zip (zipfile) e pegar o ÚNICO arquivo de dentro
    #      (o nome interno é estranho, tipo F.K03200$Z.D...MUNICCSV;
    #       por isso pegar "o primeiro da lista", não pelo nome)
    #
    # 2. Ler com pandas usando EXATAMENTE estas opções:
    #      sep=";" -> separador da RFB
    #      header=None -> o CSV NÃO tem cabeçalho
    #      encoding="latin-1" -> ISO-8859-1; sem isso, nomes com acento
    #                            (ex.: SÃO JOSÉ) quebram ou dão erro
    #      dtype=str -> tudo como texto (zeros à esquerda!)
    #      names=["codigo", "nome"]
    #
    # 3. Filtrar linhas onde nome contém "JOINVILLE"
    # 4. Imprimir o resultado
    #
    # 5. CHECAGEM: se vier mais de uma linha, imprimir todas e avisar.
    #    Se vier zero, avisar que a busca falhou.
    #
    # Checar "mais de uma linha": existe a chance de haver
    # mais de um município com nome parecido no Brasil. Você confirma
    # olhando, não confiando no primeiro resultado.
    ...


if __name__ == "__main__":
    # 1. Chamar listar_competencias()
    #    -> imprimir as 3 últimas e quantas existem no total
    #
    # 2. Pegar a mais recente (a última da lista)
    # 3. Chamar baixar_arquivo(mais_recente, "Municipios.zip")
    #    -> imprimir o tamanho do arquivo e quanto tempo levou
    #
    # 4. Chamar procurar_joinville(caminho)
    #
    # 5. Apagar a pasta RFB_PASTA_TEMP
    #    -> regra de ouro: o vestiário é limpo no fim do jogo, sempre
    ...