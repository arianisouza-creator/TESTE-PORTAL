from abc import ABC, abstractmethod

from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult


class CotacaoStageError(RuntimeError):
    """Erro com a etapa exata onde o fluxo de automacao parou."""

    def __init__(self, etapa: str, mensagem: str):
        super().__init__(mensagem)
        self.etapa = etapa
        self.mensagem = mensagem


class QuoteConnector(ABC):
    def __init__(self, companhia: str):
        self.companhia = companhia

    @abstractmethod
    def quote(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        raise NotImplementedError
