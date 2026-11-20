"""
Seções da CNAE 2.0, a classificação de setores usada pelas três fontes.

O CAGED grava só a letra ("C"); CEMPRE e RFB gravam letra + nome
("C Indústrias de transformação"). O agente padroniza tudo pela letra.
"""

SECOES_CNAE: dict[str, str] = {
    "A": "Agricultura, pecuária, produção florestal, pesca e aquicultura",
    "B": "Indústrias extrativas",
    "C": "Indústrias de transformação",
    "D": "Eletricidade e gás",
    "E": "Água, esgoto, atividades de gestão de resíduos e descontaminação",
    "F": "Construção",
    "G": "Comércio; reparação de veículos automotores e motocicletas",
    "H": "Transporte, armazenagem e correio",
    "I": "Alojamento e alimentação",
    "J": "Informação e comunicação",
    "K": "Atividades financeiras, de seguros e serviços relacionados",
    "L": "Atividades imobiliárias",
    "M": "Atividades profissionais, científicas e técnicas",
    "N": "Atividades administrativas e serviços complementares",
    "O": "Administração pública, defesa e seguridade social",
    "P": "Educação",
    "Q": "Saúde humana e serviços sociais",
    "R": "Artes, cultura, esporte e recreação",
    "S": "Outras atividades de serviços",
    "T": "Serviços domésticos",
    "U": "Organismos internacionais e outras instituições extraterritoriais",
}


def secao_do_setor(setor: str) -> str | None:
    """
    Extrai a letra da seção de "C" ou "C Indústrias de transformação".
    Devolve None para linhas que não são seção (ex.: "Total").
    """

    letra = setor.strip()[:1].upper()
    resto = setor.strip()[1:2]

    if letra in SECOES_CNAE and resto in ("", " "):
        return letra

    return None
