"""

Consulta o banco DuckDB gerado na etapa 3 e calcula os principais indicadores:

1. Checagem de completude por ano (quantas capitais reportaram)
2. Taxa de Execução Financeira (Pago / Empenhado) por capital e função
3. Ranking de capitais por taxa de execução
4. Gasto per capita por função
5. Posição de Maceió frente às demais capitais
6. Detalhamento por subfunção (ex.: dentro de Saúde)

Os resultados são impressos no console e também salvos em CSVs na pasta
"resultados/" para facilitar a escrita das conclusões (e, se quiser, para
importar no Power BI depois).

"""

from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
DUCKDB_PATH = RAIZ / "finbra.duckdb"
PASTA_RESULTADOS = RAIZ / "resultados"
PASTA_RESULTADOS.mkdir(exist_ok=True)


def rodar_analises():
    con = duckdb.connect(str(DUCKDB_PATH))

    # ------------------------------------------------------------------
    # 1) Completude por ano, quantas capitais reportaram cada ano
    # ------------------------------------------------------------------
    print("=" * 70)
    print("1) COMPLETUDE DOS DADOS POR ANO")
    print("=" * 70)

    completude = con.execute("""
        SELECT ano, COUNT(DISTINCT "Instituição") AS qtd_capitais
        FROM despesas
        GROUP BY ano
        ORDER BY ano
    """).fetchdf()
    print(completude)
    completude.to_csv(PASTA_RESULTADOS / "01_completude_por_ano.csv", index=False)

    # Anos considerados "completos" (26 ou 27 capitais — DF entra como capital)
    # Ajuste o limiar conforme o que você observar nos seus dados reais.
    anos_completos = completude[completude["qtd_capitais"] >= 25]["ano"].tolist()
    print(f"\nAnos considerados completos para comparação: {anos_completos}")

    # ------------------------------------------------------------------
    # 2) Taxa de Execução Financeira por capital e função
    #    Taxa = Pago / Empenhado * 100
    #    Filtra apenas linhas de 'funcao' (exclui agregados e subfunções)
    #    para não contar valores duplicados.
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("2) TAXA DE EXECUÇÃO FINANCEIRA POR CAPITAL E FUNÇÃO")
    print("=" * 70)

    taxa_execucao = con.execute("""
        WITH empenhado AS (
            SELECT "Instituição", "Conta", ano, SUM("Valor") AS valor_empenhado
            FROM despesas
            WHERE "Coluna" = 'Despesas Empenhadas'
              AND tipo_conta = 'funcao'
            GROUP BY "Instituição", "Conta", ano
        ),
        pago AS (
            SELECT "Instituição", "Conta", ano, SUM("Valor") AS valor_pago
            FROM despesas
            WHERE "Coluna" = 'Despesas Pagas'
              AND tipo_conta = 'funcao'
            GROUP BY "Instituição", "Conta", ano
        )
        SELECT
            e."Instituição" AS capital,
            e."Conta" AS funcao,
            e.ano,
            e.valor_empenhado,
            p.valor_pago,
            ROUND(p.valor_pago / NULLIF(e.valor_empenhado, 0) * 100, 1) AS taxa_execucao_pct
        FROM empenhado e
        JOIN pago p
          ON e."Instituição" = p."Instituição"
         AND e."Conta" = p."Conta"
         AND e.ano = p.ano
        ORDER BY e.ano DESC, e."Conta", taxa_execucao_pct DESC
    """).fetchdf()

    print(taxa_execucao.head(20))
    taxa_execucao.to_csv(PASTA_RESULTADOS / "02_taxa_execucao_por_capital_funcao.csv", index=False)
    print(f"\n-> {len(taxa_execucao):,} linhas salvas em resultados/02_taxa_execucao_por_capital_funcao.csv")

    # ------------------------------------------------------------------
    # 3) Ranking médio de execução por capital (média entre todas as funções)
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("3) RANKING DE CAPITAIS POR TAXA DE EXECUÇÃO MÉDIA")
    print("=" * 70)

    ranking = con.execute("""
        WITH empenhado AS (
            SELECT "Instituição", ano, SUM("Valor") AS valor_empenhado
            FROM despesas
            WHERE "Coluna" = 'Despesas Empenhadas' AND tipo_conta = 'funcao'
            GROUP BY "Instituição", ano
        ),
        pago AS (
            SELECT "Instituição", ano, SUM("Valor") AS valor_pago
            FROM despesas
            WHERE "Coluna" = 'Despesas Pagas' AND tipo_conta = 'funcao'
            GROUP BY "Instituição", ano
        )
        SELECT
            e."Instituição" AS capital,
            ROUND(AVG(p.valor_pago / NULLIF(e.valor_empenhado, 0) * 100), 1) AS taxa_execucao_media_pct
        FROM empenhado e
        JOIN pago p ON e."Instituição" = p."Instituição" AND e.ano = p.ano
        GROUP BY e."Instituição"
        ORDER BY taxa_execucao_media_pct DESC
    """).fetchdf()

    print(ranking)
    ranking.to_csv(PASTA_RESULTADOS / "03_ranking_capitais_execucao.csv", index=False)

    # ------------------------------------------------------------------
    # 4) Gasto per capita por função (usa o ano mais recente completo)
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("4) GASTO PER CAPITA POR FUNÇÃO (último ano completo)")
    print("=" * 70)

    if anos_completos:
        ano_referencia = max(anos_completos)
        print(f"Usando ano de referência: {ano_referencia}")

        per_capita = con.execute(f"""
            SELECT
                "Instituição" AS capital,
                "Conta" AS funcao,
                "População" AS populacao,
                SUM("Valor") AS total_pago,
                ROUND(SUM("Valor") / NULLIF("População", 0), 2) AS gasto_per_capita
            FROM despesas
            WHERE "Coluna" = 'Despesas Pagas'
              AND tipo_conta = 'funcao'
              AND ano = {ano_referencia}
            GROUP BY "Instituição", "Conta", "População"
            ORDER BY "Conta", gasto_per_capita DESC
        """).fetchdf()

        print(per_capita.head(20))
        per_capita.to_csv(PASTA_RESULTADOS / "04_gasto_per_capita.csv", index=False)
    else:
        print("Nenhum ano completo identificado — pulando análise per capita.")

    # ------------------------------------------------------------------
    # 5) Maceió frente às demais capitais (evolução 2020-2024 em Saúde e Educação)
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("5) MACEIÓ x MÉDIA DAS CAPITAIS — SAÚDE E EDUCAÇÃO (2020-2024)")
    print("=" * 70)

    maceio_vs_media = con.execute("""
        SELECT
            ano,
            "Conta" AS funcao,
            SUM(CASE WHEN "Instituição" LIKE '%Maceió%' THEN "Valor" ELSE 0 END) AS maceio_pago,
            ROUND(AVG("Valor"), 2) AS media_capitais_pago
        FROM despesas
        WHERE "Coluna" = 'Despesas Pagas'
          AND tipo_conta = 'funcao'
          AND ("Conta" LIKE '10 -%' OR "Conta" LIKE '12 -%')  -- Saúde e Educação
          AND ano BETWEEN 2020 AND 2024
        GROUP BY ano, "Conta"
        ORDER BY "Conta", ano
    """).fetchdf()

    print(maceio_vs_media)
    maceio_vs_media.to_csv(PASTA_RESULTADOS / "05_maceio_vs_media_saude_educacao.csv", index=False)

    # ------------------------------------------------------------------
    # 6) Detalhamento por subfunção dentro de Saúde (último ano completo)
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("6) SUBFUNÇÕES DE SAÚDE — ONDE SE CONCENTRA O GASTO")
    print("=" * 70)

    if anos_completos:
        subfuncoes_saude = con.execute(f"""
            SELECT
                "Conta" AS subfuncao,
                SUM("Valor") AS total_pago
            FROM despesas
            WHERE "Coluna" = 'Despesas Pagas'
              AND tipo_conta = 'subfuncao'
              AND "Conta" LIKE '10.%'
              AND ano = {ano_referencia}
            GROUP BY "Conta"
            ORDER BY total_pago DESC
        """).fetchdf()

        print(subfuncoes_saude)
        subfuncoes_saude.to_csv(PASTA_RESULTADOS / "06_subfuncoes_saude.csv", index=False)

    con.close()
    print(f"\nTodos os resultados foram salvos em: {PASTA_RESULTADOS}/")


if __name__ == "__main__":
    rodar_analises()
