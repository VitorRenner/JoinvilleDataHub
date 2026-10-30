from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RfbBase(BaseModel):
    """
    Campos compartilhados dos registros agregados da RFB.
    """

    competencia: str
    setor: str
    #Contagens feitas automaticamente pelo projeto, sendo ausência é 0, nunca None.
    ativas: int = 0
    aberturas: int = 0
    encerramentos: int = 0
    ativas_mei: int = 0
    ativas_simples: int = 0


class RfbCreate(RfbBase):
    """
    Schema utilizado para a criação da RFB.
    """

    pass


class RfbResponse(RfbBase):
    """
    Schema utilizado para as respostas da API.
    """

    id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
