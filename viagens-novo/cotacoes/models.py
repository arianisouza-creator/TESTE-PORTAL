from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ConnectorConfig(BaseModel):
    companhia: str = Field(default="LATAM")
    siteUrl: str = Field(default="")
    usuario: str = Field(default="")
    senha: Optional[str] = None
    senhaMask: str = Field(default="")
    ambiente: str = Field(default="Teste")
    status: str = Field(default="Configurado")
    observacao: str = Field(default="")
    updatedAt: str = Field(default="")


class QuoteRequest(BaseModel):
    companhia: str = Field(default="")
    origem: str
    destino: str
    dataIda: str
    dataVolta: str = Field(default="")
    adultos: int = Field(default=1, ge=1)
    cabine: str = Field(default="Economica")
    comando: str = Field(default="")


class QuoteResult(BaseModel):
    id: int
    createdAt: str
    modo: str
    companhia: str
    origem: str
    destino: str
    dataIda: str
    dataVolta: str = Field(default="")
    adultos: int
    cabine: str
    comando: str = Field(default="")
    moeda: str = Field(default="BRL")
    menorPreco: float
    localizadorTeste: str = Field(default="")
    detalhes: list[dict] = Field(default_factory=list)
    status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def model_to_dict(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
