
<img src="https://raw.githubusercontent.com/Databricks-BR/lab_agosto_2025/main/images/head_lab.png">

## Lab 04 - Criando Aplicativo Avançado de Dados - Apps
</br>

### 4.1 - Manipulando Dados
</br>

#### Passo 02 - Convertendo GeoCode para H3

``` sql

use catalog workshop;

use schema inadimplencia;

create table faturamento_h3
as 
select fat.*,
      h3_longlatash3(longitude,latitude , 10)  as h3_10,
      h3_longlatash3(longitude,latitude , 9)   as h3_09
from faturamento fat;

```

</br></br>

#### Passo 03 - Criação de uma Tabela para o APPs

``` sql

use catalog workshop;

use schema inadimplencia;

CREATE OR REPLACE TABLE gold_faturamento_h3 
AS 
  SELECT
    h3_09  AS h3_09_id,
    genero_cliente,
    bairro,
    faixa_divida,
    COUNT(num_cliente) AS contagem_clientes,
    SUM(val_divida)    AS valor_inadimplencia
  FROM  faturamento_h3
  WHERE ind_inadimplente = 'S'
  GROUP BY 1, 2, 3, 4
;

```


