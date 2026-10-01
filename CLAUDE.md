# CSVtoREVERSEGEO

## Ideia do projeto
Sistema em Python que lê um arquivo CSV com coordenadas (ID, latitude, longitude) e consome
uma API de **reverse geocoding** para descobrir o endereço de cada ponto.

## API utilizada
Google Maps – Geocoding reverso
- Exemplo oficial: https://developers.google.com/maps/documentation/javascript/examples/geocoding-reverse#maps_geocoding_reverse-html
- Endpoint web service (o que o Python usa):
  `https://maps.googleapis.com/maps/api/geocode/json?latlng=LAT,LONG&key=SUA_CHAVE`
- A chave fica na variável de ambiente `API_TESTE_1` (nunca colocar no código). A URL vem de `GEOCODE_URL`.

## O que foi pedido
1. Ler um CSV de entrada (colunas: `id`, `lat`, `long`).
2. Para cada linha, chamar a API de reverse geocoding.
3. Gerar uma tabela de saída (CSV, que abre no Excel) com os dados, **em evidência**:
   `ID`, `RUA`, `BAIRRO`, `CEP`, `LAT`, `LONG`.
4. A tabela deve ser **exportada** (arquivo `resultado.csv`).
5. Também deve rodar/ser exibida em um **HTML simples** (`resultado.html`), abrindo direto no navegador.
6. O desenvolvimento em `Teste1/teste_1.py` deve ser feito de forma **bem simples e gradual**,
   como se fosse um estagiário que acabou de começar: sem classes, poucas funções, muitos comentários.

## Estrutura
- `Teste1/teste_1.py` – primeira versão (simples).
- `Teste1/entrada.csv` – CSV de exemplo.
- `Teste1/resultado.csv` e `Teste1/resultado.html` – saídas geradas.
- `Teste1/servidor_mock.py` – "Google de mentira" em `localhost:8000` (mesmo formato JSON, não gasta a API).
- `app.py` – versão final: página web local (estilo anos 2000) para **importar** um CSV, consultar e **exportar** (CSV/HTML).

## Como rodar
```
python app.py                      (abre http://localhost:8080, modo simulado)
```
Com o Google de verdade (a chave fica só na variável de ambiente, nunca no código):
```
set GEOCODE_URL=https://maps.googleapis.com/maps/api/geocode/json
set API_TESTE_1=sua_chave
python app.py
```
Versão simples de linha de comando: `python Teste1/servidor_mock.py` (outro terminal) e `python Teste1/teste_1.py`.

## Convenções
- Python 3, somente biblioteca padrão (sem `pip install`).
- CSV de saída com separador `;` e UTF-8 com BOM, para abrir certo no Excel em português.
- Campos do endereço vêm de `address_components` (`route`, `sublocality`, `postal_code`).
