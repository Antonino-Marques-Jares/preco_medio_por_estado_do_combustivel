# Preço médio do combustível por Estado e eventos relevantes 
  Gráfico exibe informações dos preços médios dos combustíveis e eventos relevantes

## Passo 1: 
  Crie as pastas csv e csv_resumo

## Passo 2:
  Baixe os dataset's  
  1º e 2º Semestre dos anos 2004 a 2024 (total de 40 arquivos csv) e salvando todos na pasta csv.

## Passo 3:
  Execute o Jupyter.
  
  Primeiro o código simplifica as informações restringindo as colunas e cria na pasta csv_resumo planilhas com menos colunas.
  
  Em seguida criamos uma tabela combustivel do sqlite3.
  
  Com a base de dados sqlite podemos executar que nos traz o preço médio em VL_VENDA:
  
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
  
  Em seguida criamos resumo_gasolina.csv, resumo_etanol.csv e resumo_diesel.csv
  
  Com estes resumos criamos ao final um html que exibe o gráfico do preço médio.


