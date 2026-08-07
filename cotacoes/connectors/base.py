from abc import ABC, abstractmethod

from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult


class QuoteConnector(ABC):
    def __init__(self, companhia: str):
        self.companhia = companhia

    @abstractmethod
    def quote(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        raise NotImplementedError
