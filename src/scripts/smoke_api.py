import sys

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def main() -> int:
    api = httpx.Client(base_url=BASE_URL, timeout=30)
    spec = api.get("/openapi.json").json()

    ok = falha = 0
    for rota, metodos in sorted(spec["paths"].items()):
        if "get" not in metodos:
            continue

        resposta = api.get(rota.replace("{registro_id}", "1"))
        bom = resposta.status_code == 200 or (
            resposta.status_code == 404 and "{" in rota
        )
        ok += bom
        falha += not bom
        print("✅" if bom else "❌", resposta.status_code, rota)

    secoes = sorted(
        {
            tag
            for metodos in spec["paths"].values()
            for operacao in metodos.values()
            for tag in operacao.get("tags", [])
        }
    )

    print(f"\n{ok} ok, {falha} com problema")
    print("Swagger:", api.get("/docs").status_code, "| Seções:", secoes)

    return 1 if falha else 0


if __name__ == "__main__":
    sys.exit(main())
