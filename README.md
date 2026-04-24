# Base CEP x Logradouro x Setor Censitario x Renda

Este repositorio organiza uma pipeline de enriquecimento territorial a partir de bases oficiais do IBGE.

O foco principal aqui e publicar com seguranca:

- o notebook "do zero"
- o script da pipeline
- as instrucoes de uso
- uma amostra leve de saida

sem tentar versionar dezenas de gigabytes de dados brutos dentro do Git.

## O que existe neste projeto

- notebook principal do fluxo "do zero":
  - `notebooks/pipeline_do_zero_cnefe_setor_cep_renda.ipynb`
- pipeline em script para a visao `CEP -> logradouro -> setor -> renda`:
  - `pipeline_cep_logradouro_setor_renda.py`
- downloader dos arquivos CNEFE por UF:
  - `ibge_cnefe_uf_playwright_edge.py`
- notebooks de analise exploratoria:
  - `notebooks/analise_exploratoria_setor_cep_renda.ipynb`
  - `notebooks/analise_exploratoria_setor_cep_renda_v2.ipynb`
- amostra leve de saida para demonstracao:
  - `sample_data/`
- guia de publicacao:
  - `PUBLISH_TO_GITHUB.md`

## Estrutura local esperada

O notebook principal usa esta estrutura de pastas:

```text
Base CEP_LOG_RENDA/
  Agregados_por_setores_renda_responsavel_BR_csv/
    Agregados_por_setores_renda_responsavel_BR.csv
  BR_setores_CD2022/
    BR_setores_CD2022.shp
    BR_setores_CD2022.shx
    BR_setores_CD2022.dbf
    BR_setores_CD2022.prj
    BR_setores_CD2022.cpg
  saida_cnefe_uf/
    extraido/
      SEM_UF/
        11_RO.csv
        12_AC.csv
        ...
        35_SP.csv
        ...
  notebooks/
    pipeline_do_zero_cnefe_setor_cep_renda.ipynb
```

Entradas principais:

- `saida_cnefe_uf/extraido/SEM_UF/*.csv`
- `BR_setores_CD2022/BR_setores_CD2022.shp`
- `Agregados_por_setores_renda_responsavel_BR_csv/Agregados_por_setores_renda_responsavel_BR.csv`

## Por que os dados brutos nao devem ir para o GitHub

No workspace atual, os principais volumes sao aproximadamente:

- `saida_cnefe_uf/`: mais de 21 GB
- `BR_setores_CD2022/`: mais de 2 GB
- `saida_setor_cep_renda_do_zero/`: centenas de MB

Isso significa que o caminho certo para publicar o projeto e:

- versionar codigo, notebooks, README e amostras leves
- manter os dados brutos fora do Git
- apontar no README onde baixar os insumos oficiais
- se necessario, publicar artefatos grandes em GitHub Releases, Git LFS ou armazenamento externo

## Ambiente

Dependencias principais:

- Python 3.11+ recomendado
- pandas
- pyarrow
- geopandas
- matplotlib
- requests
- playwright
- jupyterlab

Instalacao sugerida:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se voce quiser usar o downloader com Playwright:

```powershell
playwright install
```

## Notebook do zero

Notebook principal:

- `notebooks/pipeline_do_zero_cnefe_setor_cep_renda.ipynb`

Esse notebook:

1. carrega renda por setor
2. carrega atributos dos setores a partir do shapefile
3. processa o CNEFE bruto por chunks
4. agrega no grao `setor + CEP + logradouro`
5. exporta a base final `setor + CEP + renda`

Saidas padrao:

- `saida_setor_cep_renda_do_zero/setor_censitario_cep_renda_do_zero.csv`
- `saida_setor_cep_renda_do_zero/setor_censitario_cep_renda_do_zero.parquet`
- `saida_setor_cep_renda_do_zero/setor_cep_renda_do_zero_work.sqlite`
- `saida_setor_cep_renda_do_zero/setor_censitario_cep_renda_do_zero_resumo.json`

O notebook aceita tambem:

- `UF_FILTER`
- `SETOR_FILTER`
- `LIMIT_FILES`
- `LIMIT_ROWS_PER_FILE`

Isso facilita smoke tests pequenos antes de rodar Brasil inteiro.

## Smoke test recomendado

Exemplo pequeno para validar a pipeline:

```python
UF_FILTER = ["SP"]
SETOR_FILTER = ["350010505000017"]

LIMIT_FILES = 1
LIMIT_ROWS_PER_FILE = 1000

CHUNKSIZE = 500
SQL_CHUNKSIZE = 500

REBUILD_SQLITE = True
EXPORT_CSV = True
EXPORT_PARQUET = True
```

As amostras dessa execucao ficam em:

- `sample_data/setor_censitario_cep_renda_do_zero_setor_smoke.csv`
- `sample_data/setor_censitario_cep_renda_do_zero_setor_smoke_resumo.json`

## Configuracao para Brasil inteiro

Ponto de partida recomendado:

```python
UF_FILTER = None
SETOR_FILTER = None

LIMIT_FILES = None
LIMIT_ROWS_PER_FILE = None

CHUNKSIZE = 250_000
SQL_CHUNKSIZE = 100_000

REBUILD_SQLITE = True
EXPORT_CSV = True
EXPORT_PARQUET = True
```

Se a maquina tiver menos memoria, comece com:

```python
CHUNKSIZE = 100_000
SQL_CHUNKSIZE = 50_000
```

## O que deve entrar no repositorio Git

Recomendado versionar:

- `notebooks/`
- `pipeline_cep_logradouro_setor_renda.py`
- `ibge_cnefe_uf_playwright_edge.py`
- `README.md`
- `README_PIPELINE_CEP_LOGRADOURO_SETOR_RENDA.md`
- `PUBLISH_TO_GITHUB.md`
- `requirements.txt`
- `sample_data/`
- `.gitignore`

Recomendado nao versionar:

- `Agregados_por_setores_renda_responsavel_BR_csv/`
- `BR_setores_CD2022/`
- `saida_cnefe_uf/`
- `saida_cep_logradouro_setor_renda/`
- `saida_setor_cep_renda_do_zero/`
- `saida_setor_cep_renda_do_zero_smoke/`
- `saida_setor_cep_renda_do_zero_setor_smoke/`
- qualquer `*.zip`, `*.sqlite`, `*.parquet`, `*.shp`, `*.dbf`

## Como publicar no GitHub do zero

Resumo rapido:

1. instale o Git
2. rode `git init`
3. confira `git status`
4. adicione apenas codigo, notebooks, docs e `sample_data`
5. faca o commit inicial
6. crie um repositorio vazio no GitHub
7. conecte o remoto e faca `git push`

O passo a passo completo esta em:

- `PUBLISH_TO_GITHUB.md`

## Observacoes

- O repositorio foi preparado para reproduzir o processo, nao para espelhar todos os dados brutos.
- O notebook principal esta pronto para publicacao porque usa caminhos relativos ao projeto.
- Se o objetivo for compartilhar as bases nacionais completas, o melhor caminho e usar armazenamento externo e documentar os links no README.
- O README especializado da pipeline em script continua disponivel em `README_PIPELINE_CEP_LOGRADOURO_SETOR_RENDA.md`.
