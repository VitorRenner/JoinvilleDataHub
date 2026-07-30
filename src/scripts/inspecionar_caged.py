from pathlib import Path

import pandas as pd


def main():
    arquivo = Path(
        "data/raw/caged/202606/202606/CAGEDMOV202606.txt"
    )

    print("=" * 60)
    print("ARQUIVO ENCONTRADO")
    print("=" * 60)
    print(arquivo)

    df = pd.read_csv(
        arquivo,
        sep=";",
        encoding="UTF-8",
        low_memory=False,
    )

    print("\nShape:")
    print(df.shape)

    print("\nColunas:")
    print(df.columns.tolist())

    print("\nPrimeiras linhas:")
    print(df.head())

    print("\nTipos das colunas:")
    print(df.dtypes)


if __name__ == "__main__":
    main()