# teste_1.py - primeira versao
# Definições do teste do projeto:
# Le um CSV com id, lat, long e descobre o endereco usando a API do Google (reverse geocoding)
# Gera resultado.csv e resultado.html

import csv
import html as html_lib
import json
import os
import urllib.request

# endereco da API. Por padrao usa o servidor falso local (servidor_mock.py).
# Para usar o Google de verdade: set GEOCODE_URL=https://maps.googleapis.com/maps/api/geocode/json
URL_API = os.environ.get("GEOCODE_URL", "http://localhost:8000/maps/api/geocode/json")

# a chave da API fica numa variavel de ambiente (API_TESTE_1), nunca no codigo
CHAVE = os.environ.get("API_TESTE_1", "")

pasta = os.path.dirname(os.path.abspath(__file__))
arquivo_entrada = os.path.join(pasta, "entrada.csv")
arquivo_csv = os.path.join(pasta, "resultado.csv")
arquivo_html = os.path.join(pasta, "resultado.html")

# no mock qualquer chave serve; no Google de verdade a chave e obrigatoria
if CHAVE == "":
    if "localhost" in URL_API:
        CHAVE = "chave-de-teste"
    else:
        print("Faltou a chave! Use: set API_TESTE_1=sua_chave")
        raise SystemExit


# pega um pedaco do endereco pelo tipo (route, postal_code...)
# olha todos os resultados, porque o Google as vezes so traz o CEP no 2o ou 3o resultado
def pegar_parte(resultados, tipo):
    for r in resultados:
        for c in r["address_components"]:
            if tipo in c["types"]:
                return c["long_name"]
    return ""


# chama a API para uma coordenada
def buscar_endereco(lat, lng):
    url = URL_API + "?latlng=" + lat + "," + lng + "&key=" + CHAVE
    try:
        resposta = urllib.request.urlopen(url)
    except OSError:
        print("Nao consegui falar com a API. O servidor_mock.py esta rodando?")
        raise SystemExit
    dados = json.loads(resposta.read().decode("utf-8"))

    if dados["status"] != "OK":
        print("Erro na API:", dados["status"])
        return "", "", ""

    componentes = dados["results"]
    rua = pegar_parte(componentes, "route")
    bairro = pegar_parte(componentes, "sublocality")
    if bairro == "":
        bairro = pegar_parte(componentes, "neighborhood")
    cep = pegar_parte(componentes, "postal_code")
    return rua, bairro, cep


# primeiro teste: ler o csv de entrada
linhas = []
with open(arquivo_entrada, newline="", encoding="utf-8-sig") as f:
    leitor = csv.DictReader(f)
    for linha in leitor:
        linhas.append(linha)
print("Linhas lidas:", len(linhas))

# Teste 1 para consultar a API para cada linha
resultado = []
for linha in linhas:
    # tira espacos e troca virgula por ponto (a API so entende ponto)
    lat = linha["lat"].strip().replace(",", ".")
    lng = linha["long"].strip().replace(",", ".")
    rua, bairro, cep = buscar_endereco(lat, lng)
    resultado.append([linha["id"], rua, bairro, cep, lat, lng])
    print("ok:", linha["id"], rua)

cabecalho = ["ID", "RUA", "BAIRRO", "CEP", "LAT", "LONG"]

# Função modular para salvar o csv (separador ; para abrir no Excel)
def salvar_csv():
    with open(arquivo_csv, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(cabecalho)
        for linha in resultado:
            # lat/long com virgula, senao o Excel em portugues acha que o ponto e milhar
            escritor.writerow(linha[:4] + [linha[4].replace(".", ","), linha[5].replace(".", ",")])

salvar_csv()

# html simples
html = "<html><head><meta charset='utf-8'><title>Resultado</title></head><body>\n"
html += "<h1>Reverse Geocoding</h1>\n<table border='1' cellpadding='5'>\n<tr>"
for titulo in cabecalho:
    html += "<th>" + titulo + "</th>"
html += "</tr>\n"
for linha in resultado:
    html += "<tr>"
    for valor in linha:
        html += "<td>" + html_lib.escape(str(valor)) + "</td>"  # escape para nao quebrar a tabela
    html += "</tr>\n"
html += "</table>\n</body></html>"

with open(arquivo_html, "w", encoding="utf-8") as f:
    f.write(html)

print("Pronto! Gerei resultado.csv e resultado.html")
