"""
Carrega o CSV consolidado em um banco DuckDB local,
salvando também uma cópia em Parquet (formato colunar, comprimido).

DuckDB permite consultar os dados com SQL puro, sem precisar de servidor,
servindo para buscas rápidas e exploração de dados e o Parquet garante portabilidade: qualquer ferramenta (pandas, Spark, Power BI)
consegue ler o arquivo de forma eficiente, sem precisar do DuckDB.

"""

from pathlib import Path
import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CSV_CONSOLIDADO = RAIZ / "dados_extraidos" / "finbra_consolidado.csv"
PARQUET_SAIDA = RAIZ / "dados_extraidos" / "finbra_consolidado.parquet"
DUCKDB_SAIDA = RAIZ / "finbra.duckdb"


def carregar():
    if not CSV_CONSOLIDADO.exists():
        raise FileNotFoundError(
            f"'{CSV_CONSOLIDADO}' não encontrado. Rode primeiro o script 02_consolidar.py."
        )

    df = pd.read_csv(CSV_CONSOLIDADO)

    # Salva em Parquet (formato colunar, comprimido, leitura rápida)
    df.to_parquet(PARQUET_SAIDA, index=False)
    print(f"Parquet salvo em: {PARQUET_SAIDA}")

    # Cria/conecta a um banco DuckDB local em arquivo
    con = duckdb.connect(str(DUCKDB_SAIDA))

    # Cria a tabela 'despesas' diretamente a partir do Parquet
    con.execute(f"""
        CREATE OR REPLACE TABLE despesas AS
        SELECT * FROM read_parquet('{PARQUET_SAIDA}')
    """)

    total_linhas = con.execute("SELECT COUNT(*) FROM despesas").fetchone()[0]
    print(f"Tabela 'despesas' criada no DuckDB com {total_linhas:,} linhas.")

    # Pequena checagem: quantas capitais por ano
    print("\nCapitais por ano (checagem de completude):")
    resultado = con.execute("""
        SELECT ano, COUNT(DISTINCT "Instituição") AS qtd_capitais
        FROM despesas
        GROUP BY ano
        ORDER BY ano
    """).fetchdf()
    print(resultado)

    con.close()
    print(f"\nBanco DuckDB salvo em: {DUCKDB_SAIDA}")
    print("Para consultar depois, basta: duckdb.connect('finbra.duckdb')")


if __name__ == "__main__":
    carregar()
