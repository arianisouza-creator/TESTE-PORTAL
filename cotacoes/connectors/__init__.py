from cotacoes.connectors.sandbox import SandboxConnector
from cotacoes.connectors.azul import AzulConnector
from cotacoes.connectors.gol import GolConnector
from cotacoes.connectors.latam import LatamConnector


def get_connector(companhia: str):
    normalized = (companhia or "").strip().lower()
    if "latam" in normalized:
        return LatamConnector(companhia=companhia or "LATAM")
    if "azul" in normalized:
        return AzulConnector(companhia=companhia or "Azul")
    if "gol" in normalized:
        return GolConnector(companhia=companhia or "GOL")
    return SandboxConnector(companhia=companhia or "LATAM")
