import os

from cotacoes.models import QuoteRequest
from cotacoes.service import quote


def main() -> None:
    os.environ["COTACOES_LATAM_MODE"] = "browser"
    os.environ["COTACOES_LATAM_HEADLESS"] = "false"
    os.environ["COTACOES_LATAM_PROFILE_DIR"] = ".playwright-latam-profile"
    request = QuoteRequest(
        companhia="LATAM",
        origem="LDB",
        destino="MOC",
        dataIda="2026-11-24",
        dataVolta="2026-11-26",
        adultos=1,
        cabine="Economica",
    )
    result = quote(request)
    print(f"STATUS={result.status}", flush=True)
    print(f"TOTAL_OPCOES={len(result.detalhes)}", flush=True)
    for item in result.detalhes[:8]:
        print(
            f"{item.get('tipo')} {item.get('origem')}-{item.get('destino')} "
            f"{item.get('saida')}-{item.get('chegada')} R$ {item.get('preco')}",
            flush=True,
        )


if __name__ == "__main__":
    main()
