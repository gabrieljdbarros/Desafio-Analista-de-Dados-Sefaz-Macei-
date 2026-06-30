# Desafio Analista de Dados — Sefaz Maceió

Solução do desafio técnico proposto para a vaga de estágio em Análise de Dados da Sefaz Maceió.

## Objetivo

Comparar como as 26 capitais brasileiras gastam dinheiro público por função orçamentária,
analisando a diferença entre **Despesas Empenhadas** e **Despesas Pagas** no período de 2020 a 2025.

## Como rodar

```bash
# 1. Crie um ambiente virtual
python -m venv nome_env
source nome_env/bin/activate  # Linux/Mac
# nome_env\Scripts\activate   # Windows

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Rode os scripts em ordem
python scripts/Descompactar.py
python scripts/Consolidar.py
python scripts/Carregar_DuckDB.py
python scripts/Analise.py
```

Cada script depende do resultado do anterior. Os resultados finais (CSVs com os indicadores)
ficam salvos na pasta `resultados/`.

## Estrutura do projeto

```
.
├── dados_compactos/        # arquivos .zip originais (por ano)
├── dados_extraidos/        # csvs extraídos + consolidado.csv/.parquet
├── resultados/             # CSVs com os indicadores calculados
├── scripts/
│   ├── Descompactar.py  # extrai os .zip por código
│   ├─  Consolidar.py    # consolida os arquivos em DFs únicos
│   ├── Carregar_DuckDB.py  # salva em Parquet + carrega no DuckDB
│   └── Analise.py       # consultas SQL com os indicadores
├── finbra.duckdb           # banco DuckDB gerado
└── requirements.txt
```

## Decisões técnicas

**Por que DuckDB + Parquet?**
DuckDB permite consultar os dados com SQL puro, sem precisar de servidor, e é muito rápido
para agregações em datasets deste tamanho. Parquet garante que os dados consolidados fiquem
em um formato colunar comprimido, portável para outras ferramentas (Power BI, por exemplo).

**Tratamento do formato do CSV**
Os arquivos seguem o padrão Siconfi: encoding `latin-1`, separador `;`, decimal `,`, com 3
linhas de metadados antes do cabeçalho real. Tudo isso é tratado no `02_consolidar.py`.

**Classificação função vs. subfunção vs. agregado**
A coluna `Conta` mistura três tipos de linha: funções (`10 - Saúde`), subfunções
(`10.301 - Atenção Básica`) e totais agregados (`Despesas Exceto Intraorçamentárias`). Cada
linha é classificada em uma coluna nova `tipo_conta`, e as análises de função somam **apenas**
linhas do tipo `funcao`, para evitar duplicar valores.

**Completude dos dados**
2025 está incompleto — nem todas as capitais reportaram ainda. O script `04_analise.py` calcula
quantas capitais existem por ano antes de qualquer comparação, e usa apenas anos com 25+
capitais como "ano de referência" para análises per capita e de subfunção.

## Principais indicadores calculados

1. **Completude por ano** — quantas capitais reportaram dados em cada ano
2. **Taxa de Execução Financeira** (Pago ÷ Empenhado × 100) por capital e função
3. **Ranking de capitais** pela taxa de execução média
4. **Gasto per capita** por função, no último ano completo
5. **Maceió vs. média das capitais** em Saúde e Educação, 2020–2024
6. **Detalhamento por subfunção** dentro de Saúde

---

## Conclusões da Análise

### Completude dos dados

Antes de qualquer comparação entre anos, foi necessário checar quantas capitais reportaram
dados em cada período. 2020 a 2024 estão completos, com as 26 capitais presentes em todos os
anos. Como avisado no README do desafio, **2025 está incompleto**, com apenas 11 capitais tendo
reportado até o momento da coleta — por isso, as análises de evolução temporal e per capita
usaram 2024 como ano de referência, evitando conclusões distorcidas por comparar bases de
tamanhos diferentes.

### Taxa de execução financeira

A taxa de execução média (Pago ÷ Empenhado) das capitais variou de 83,5% (Natal) a 98,1%
(Goiânia), uma diferença relevante: capitais com taxa mais baixa deixam uma fatia maior do
orçamento comprometido como "restos a pagar", ou seja, dívidas que só serão quitadas em anos
seguintes.

Interessantemente, **Maceió aparece em 8º lugar** no ranking, com taxa média de 94,5%, acima da
mediana das 26 capitais — o que indica uma execução orçamentária relativamente consistente
entre o que é prometido e o que efetivamente sai do caixa.

### Maceió frente às demais capitais (Saúde e Educação)

Em valores absolutos, Maceió paga consistentemente menos que a média das capitais em Saúde e
Educação ao longo de 2020-2024, o que faz sentido já que a população de Maceió é menor que a
média do grupo.

- Na Saúde, Maceió gasta **R$ 1.314,67 por habitante**, ficando na 13ª posição entre as 26
  capitais — praticamente no meio da tabela, e acima de nomes como **Manaus (R$ 797)**,
  **Rio Branco (R$ 865)** e **Macapá (R$ 911)**.
- Com a educação, porém, Maceió cai para a **25ª posição**, com apenas **R$ 715,71 por
  habitante**, sendo o segundo menor valor entre todas as capitais, à frente apenas de Belém,
  que gasta **R$ 629,19**.

É necessário trazer atenção a esse contraste. Maceió gasta proporcionalmente bem em Saúde, mas
muito pouco em Educação por habitante — algo que pode dever-se a uma escolha orçamentária
deliberada ou a uma lacuna de investimento.

### Onde se concentra o gasto em Saúde

Olhando as subfunções de Saúde no conjunto das capitais, o gasto se concentra fortemente em
**Assistência Hospitalar e Ambulatorial** (R$ 32,8 bi), quase o dobro do investido em
**Atenção Básica** (R$ 20,6 bi).

### Limitações identificadas

- **Taxas de execução acima de 100%** apareceram em algumas combinações capital/função/ano
  (ex.: Belém em "01 - Legislativa" / 2025, com 102%). É possível que valores de "Despesas
  Pagas" no ano incluam o pagamento de **restos a pagar inscritos em anos anteriores**, sem o
  empenho correspondente registrado no mesmo exercício, o que infla a taxa quando comparada ao
  empenho daquele ano isoladamente. Esse comportamento merece investigação mais aprofundada se
  a análise for continuada no futuro.
- A análise de 2025 deve ser lida com cautela, dado que reflete apenas 11 das 26 capitais —
  como já dito, 2025 ainda está incompleto.
- Não foram tratados possíveis casos de duplicidade entre código IBGE e nome da instituição
  (ex.: pequenas variações de grafia entre anos), embora não tenham sido identificados
  problemas evidentes nos dados consolidados.

### Próximos passos

Com mais tempo, o próximo passo natural seria construir um dashboard interativo (Power BI ou
Streamlit) conectado diretamente ao `finbra_consolidado.parquet`, permitindo explorar os
indicadores por capital, função e ano sem precisar rodar os scripts novamente. Também seria
interessante investigar mais a fundo os casos de taxa de execução acima de 100%, cruzando com
os dados de "Restos a Pagar" disponíveis no próprio Siconfi.
