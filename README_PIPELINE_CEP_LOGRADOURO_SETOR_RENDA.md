# Pipeline CEP -> logradouro -> setor -> renda

Este script constroi tres saidas a partir dos CSVs do CNEFE e da base de renda por setor:

- `cep_logradouro_setor_renda_completo.csv`
- `cep_logradouro_setor_renda_resolvido.csv`
- `cep_logradouro_setor_renda_completo.parquet`

## Arquivos usados por padrao

- CNEFE: `saida_cnefe_uf/extraido/SEM_UF/*.csv`
- Renda: `Agregados_por_setores_renda_responsavel_BR_csv/Agregados_por_setores_renda_responsavel_BR.csv`
- Saida: `saida_cep_logradouro_setor_renda/`

## Como rodar

Execucao completa:

```powershell
python .\pipeline_cep_logradouro_setor_renda.py
```

Somente uma ou mais UFs:

```powershell
python .\pipeline_cep_logradouro_setor_renda.py --ufs SP RJ MG
```

Teste rapido com limite de linhas:

```powershell
python .\pipeline_cep_logradouro_setor_renda.py --ufs SP --limit-rows-per-file 50000 --limit-files 1
```

Reaproveitar o SQLite de trabalho e refazer apenas os exports:

```powershell
python .\pipeline_cep_logradouro_setor_renda.py --skip-ingest
```

Nao gerar parquet:

```powershell
python .\pipeline_cep_logradouro_setor_renda.py --no-parquet
```

## Regra da saida resolvida

O `csv_resolvido` escolhe 1 linha por CEP com esta ordem de prioridade:

1. maior `qtd_enderecos`
2. se empatar, preferir o candidato com renda encontrada
3. se ainda empatar, desempate alfabetico por `logradouro` e `cd_setor`

Os campos `flag_ambiguidade` e `flag_empate_topo_qtd_enderecos` ajudam a identificar CEPs que nao sao univocos.

## Observacoes

- O campo `cd_setor` e derivado dos 15 primeiros caracteres de `COD_SETOR` do CNEFE.
- Os CSVs de saida usam separador `;`.
- O script cria um SQLite de trabalho para aguentar o volume do CNEFE sem depender de DuckDB.
