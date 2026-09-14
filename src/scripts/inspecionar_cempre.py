from src.collectors.cempre import CempreCollector


def main() -> None:
    df = CempreCollector().coletar()

    print("=" * 60)
    print("DADOS DO CEMPRE - JOINVILLE")
    print("=" * 60)

    print("\nShape:")
    print(df.shape)

    print("\nColunas:")
    print(df.columns.tolist())

    print("\nPrimeiras linhas:")
    print(df.head())


if __name__ == "__main__":
    main()