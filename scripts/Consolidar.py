"""
Lê cada `finbra.csv` extraído (um por ano), trata as particularidades do 
formato (encoding latin-1, separador ';', decimal ',', 3 linhas de metadados),
e consolida tudo em um único DataFrame, salvo como CSV intermediário para
inspeção rápida.

"""

from pathlib import Path
import pandas as pd
import re

RAIZ = Path(__file__).resolve().parent.parent
PASTA_EXTRAIDOS = RAIZ / "dados_extraidos"
SAIDA_CSV = RAIZ / "dados_extraidos" / "finbra_consolidado.csv"

# Colunas que identificam linhas "agregadas" que não devem ser somadas junto
# com as funções individuais (senão duplicamos valores) deixamos para uso posterior na análise, não removemos aqui para manter o dado bruto completo.
CONTAS_AGREGADAS = [
    "Despesas Exceto Intraorçamentárias",
    "Despesas Intraorçamentárias",
]

# Padrão de subfunção: começa com 2 dígitos, ponto, 3 dígitos (ex.: "10.301 - ...")
PADRAO_SUBFUNCAO = re.compile(r"^\d{2}\.\d{3}\s*-")
# Padrão de função: começa com 2 dígitos, espaço, hífen (ex.: "10 - Saúde")
PADRAO_FUNCAO = re.compile(r"^\d{2}\s*-")


def classificar_conta(valor_conta: str) -> str:
    """Classifica a coluna 'Conta' em: funcao, subfuncao, agregado ou outro."""
    valor_conta = str(valor_conta).strip()

    if valor_conta in CONTAS_AGREGADAS:
        return "agregado"
    if valor_conta.startswith("FU") and "Demais Subfunções" in valor_conta:
        return "agregado_subfuncao"
    if PADRAO_SUBFUNCAO.match(valor_conta):
        return "subfuncao"
    if PADRAO_FUNCAO.match(valor_conta):
        return "funcao"
    return "outro"


def ler_csv_finbra(caminho_csv: Path, ano: int) -> pd.DataFrame:
    """Lê um único finbra.csv já tratando as particularidades do formato."""

    df = pd.read_csv(
        caminho_csv,
        sep=";",
        skiprows=3,          # para pular as 3 primeiras linhas
        encoding="latin-1",  # ISO-8859-1, evitar acentos quebrados
        decimal=",",         # vírgula é o separador decimal
        thousands=".",       # ponto como separador de milhar
    )

    # Normaliza nomes de colunas (remove espaços extras, por segurança)
    df.columns = [c.strip() for c in df.columns]

    # Coluna "ano" vem da pasta de origem, não do arquivo
    df["ano"] = ano

    # Classifica cada linha em função / subfunção / agregado / outro
    df["tipo_conta"] = df["Conta"].apply(classificar_conta)

    return df


def consolidar_tudo() -> pd.DataFrame:
    """Percorre todas as pastas de ano em dados_extraidos/ e consolida em um único DataFrame."""

    pastas_ano = sorted(
        [p for p in PASTA_EXTRAIDOS.iterdir() if p.is_dir()],
        key=lambda p: p.name,
    )

    if not pastas_ano:
        raise FileNotFoundError(
            f"Nenhuma pasta de ano encontrada em '{PASTA_EXTRAIDOS}'. "
            "Rode primeiro o script 01_descompactar.py."
        )

    dataframes = []

    for pasta in pastas_ano:
        ano = int(pasta.name)

        # Procura o csv extraído (pode ter nome ligeiramente diferente, então
        # buscamos qualquer .csv dentro da pasta do ano)
        csvs_encontrados = list(pasta.glob("*.csv"))

        if not csvs_encontrados:
            print(f"[AVISO] Nenhum CSV encontrado para o ano {ano}, pulando.")
            continue

        caminho_csv = csvs_encontrados[0]
        print(f"[{ano}] Lendo: {caminho_csv.name}")

        df_ano = ler_csv_finbra(caminho_csv, ano)
        print(f"  -> {len(df_ano):,} linhas | {df_ano['Instituição'].nunique()} capitais")

        dataframes.append(df_ano)

    df_final = pd.concat(dataframes, ignore_index=True)

    # Garante que Valor é numérico (deve já vir tratado pelo read_csv, mas
    # fazemos uma conversão defensiva para capturar eventuais sujeiras e evitar erros futuros)
    df_final["Valor"] = pd.to_numeric(df_final["Valor"], errors="coerce")

    print(f"\nConsolidação concluída: {len(df_final):,} linhas no total.")
    print(f"Anos presentes: {sorted(df_final['ano'].unique())}")
    print(f"Capitais por ano:")
    print(df_final.groupby("ano")["Instituição"].nunique())

    return df_final


if __name__ == "__main__":
    df = consolidar_tudo()
    df.to_csv(SAIDA_CSV, index=False, encoding="utf-8")
    print(f"\nArquivo consolidado salvo em: {SAIDA_CSV}")
