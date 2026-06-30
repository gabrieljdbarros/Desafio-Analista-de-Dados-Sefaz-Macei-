"""
Etapa 1 — Descompactação dos arquivos FINBRA
==============================================
Percorre a pasta "dados_compactos/", encontra todos os arquivos .zip e extrai o conteúdo para "dados_extraidos/<ano>/".

"""

from pathlib import Path
import zipfile

# Pasta raiz
RAIZ = Path(__file__).resolve().parent.parent
PASTA_COMPACTADOS = RAIZ / "dados_compactos"
PASTA_EXTRAIDOS = RAIZ / "dados_extraidos"


def descompactar_todos():
    """Percorre dados_compactos/<ano>/*.zip e extrai para dados_extraidos/<ano>/."""

    if not PASTA_COMPACTADOS.exists():
        raise FileNotFoundError(
            f"Pasta '{PASTA_COMPACTADOS}' não encontrada. "
            "Confirme que está rodando o script a partir da raiz do projeto."
        )

    # glob recursivo: serve para pegar qualquer .zip dentro de qualquer subpasta de ano
    arquivos_zip = sorted(PASTA_COMPACTADOS.glob("*/*.zip"))

    if not arquivos_zip:
        print("Nenhum arquivo .zip encontrado em dados_compactos/.")
        return

    print(f"Encontrados {len(arquivos_zip)} arquivos .zip.\n")

    for caminho_zip in arquivos_zip:
        # O nome da pasta-pai é o ano (ex.: dados_compactos/2020/arquivo.zip -> "2020")
        ano = caminho_zip.parent.name

        destino = PASTA_EXTRAIDOS / ano
        destino.mkdir(parents=True, exist_ok=True)

        print(f"[{ano}] Extraindo: {caminho_zip.name}")

        with zipfile.ZipFile(caminho_zip, "r") as zf:
            zf.extractall(destino)

        # Lista o que foi extraído
        extraidos = list(destino.glob("*"))
        print(f"  -> {len(extraidos)} arquivo(s) extraído(s) em {destino}\n")

    print("Descompactação concluída.")


if __name__ == "__main__":
    descompactar_todos()
