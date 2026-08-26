import time

from cotacoes.connectors.base import QuoteConnector
from cotacoes.models import ConnectorConfig, QuoteRequest, QuoteResult, utc_now


class SandboxConnector(QuoteConnector):
    def quote(self, config: ConnectorConfig, request: QuoteRequest) -> QuoteResult:
        base = "|".join([
            request.origem.upper(),
            request.destino.upper(),
            request.dataIda,
            request.dataVolta,
            str(request.adultos),
            config.companhia or self.companhia,
        ])
        seed = sum((index + 1) * ord(char) for index, char in enumerate(base))
        total = 650 + (seed % 1800) + (request.adultos - 1) * 420
        return QuoteResult(
            id=int(time.time() * 1000),
            createdAt=utc_now(),
            modo="sandbox",
            companhia=config.companhia or self.companhia,
            origem=request.origem.upper(),
            destino=request.destino.upper(),
            dataIda=request.dataIda,
            dataVolta=request.dataVolta,
            adultos=request.adultos,
            cabine=request.cabine,
            comando=request.comando,
            menorPreco=round(float(total), 2),
            localizadorTeste=f"TST{str(seed)[-5:].zfill(5)}",
            status="Motor sandbox funcionando",
        )
