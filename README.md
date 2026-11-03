![Posto de Gasolina](posto_de_gasolina.jpg)

# Instale as bibliotecas
 pip install -r requirements.txt

## Passo 1: 
  Crie diretorios D:\ETL\BRONZE e D:\ETL\PRATA

## Passo 2:
  Baixe os dataset's  **Combustíveis Automotivos** que estão em [Dados Abertos](https://dados.gov.br/dados/conjuntos-dados/serie-historica-de-precos-de-combustiveis-e-de-glp)
  1º e 2º Semestre todos eles salvando em D:\ETL\BRONZE.

## Passo 3:
  Execute o etl_combustivel_automotivo.py.
  
  Será gerando planilhas csv provisórias em D:\ETL\PRATA e uma BD SQLite também provisória.
  
  Será executado uma SQL:
  
  **SELECT 
          ESTADO,
          PRODUTO,
          MES_ANO,
          AVG(VL_VENDA) AS VL_VENDA
      FROM 
          combustivel
      WHERE 
          MES_ANO IS NOT NULL 
          AND VL_VENDA IS NOT NULL
          AND VL_VENDA > 0
      GROUP BY 
          ESTADO, PRODUTO, MES_ANO
      ORDER BY 
          ESTADO, PRODUTO, MES_ANO;**
  
  O resultado da consulta SQL gerará um json

## Passo 4:
arquivo JSON salvo no diretorio etl do projeto

## Passo 5:
É apagado arquivos temporários em D:\ETL\PRATA e a BD SQLite

# Fonte:

[![Gov Br](govbr.webp)](https://dados.gov.br/dados/conjuntos-dados/serie-historica-de-precos-de-combustiveis-e-de-glp)

[Ativo - Área de Trampo](https://www.areadetrampo.com.br/ativo/)
