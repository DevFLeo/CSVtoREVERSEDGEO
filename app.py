# app.py - versao final: pagina web local para IMPORTAR um CSV, consultar os enderecos e EXPORTAR o resultado
#
# Como rodar:
#   python app.py                  -> abre em http://localhost:8080 usando o mock (nao gasta a API)
#
# Para usar o Google de verdade:
#   set GEOCODE_URL=https://maps.googleapis.com/maps/api/geocode/json
#   set API_TESTE_1=sua_chave
#   python app.py

import csv
import html
import io
import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# reaproveita o "Google de mentira" que ja existe em Teste1/
pasta = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(pasta, "Teste1"))
from servidor_mock import montar_resposta

PORTA = 8080
URL_API = os.environ.get("GEOCODE_URL", "")  # vazio = usa o mock dentro do proprio programa
CHAVE = os.environ.get("API_TESTE_1", "")
LIMITE_LINHAS = 500          # protege a cota da API
LIMITE_BYTES = 1000000       # tamanho maximo do CSV enviado

CABECALHO = ["ID", "RUA", "BAIRRO", "CEP", "LAT", "LONG"]
EXEMPLO = "id,lat,long\n1,-23.561414,-46.655881\n2,-22.906847,-43.172897\n3,-19.919052,-43.938669\n"

# guarda o ultimo resultado na memoria (lista de listas + status de cada linha)
resultado = []
status_linhas = []
visitas = 0

if URL_API != "" and CHAVE == "":
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


# numero com virgula decimal, para o Excel em portugues nao estragar a coordenada
def numero_br(valor):
    return str(valor).replace(".", ",")


# consulta uma coordenada (no mock ou no Google) e devolve rua, bairro, cep, status
def buscar_endereco(lat, lng):
    if URL_API == "":
        dados = montar_resposta(lat, lng)
    else:
        url = URL_API + "?latlng=" + str(lat) + "," + str(lng) + "&key=" + CHAVE
        try:
            dados = json.loads(urllib.request.urlopen(url, timeout=15).read().decode("utf-8"))
        except OSError:
            return "", "", "", "ERRO_DE_REDE"

    if dados["status"] != "OK":
        return "", "", "", dados["status"]

    componentes = dados["results"]
    rua = pegar_parte(componentes, "route")
    bairro = pegar_parte(componentes, "sublocality")
    if bairro == "":
        bairro = pegar_parte(componentes, "neighborhood")
    cep = pegar_parte(componentes, "postal_code")
    return rua, bairro, cep, "OK"


# le o texto do CSV (aceita , ou ;) e devolve lista de (id, lat, long)
def ler_csv(texto):
    primeira = texto.split("\n")[0]
    separador = ";" if primeira.count(";") > primeira.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=separador)
    if leitor.fieldnames is None:
        raise ValueError("Arquivo vazio.")

    # descobre quais colunas sao id, lat e long (maiusculas/minusculas tanto faz)
    nomes = {}
    for nome in leitor.fieldnames:
        n = (nome or "").strip().lower()
        if n == "id":
            nomes["id"] = nome
        elif n in ("lat", "latitude"):
            nomes["lat"] = nome
        elif n in ("long", "lng", "lon", "longitude"):
            nomes["long"] = nome
    if len(nomes) < 3:
        raise ValueError("O CSV precisa ter as colunas: id, lat, long.")

    linhas = []
    for numero, linha in enumerate(leitor, start=2):
        try:
            lat = float(linha[nomes["lat"]].replace(",", "."))
            lng = float(linha[nomes["long"]].replace(",", "."))
        except (ValueError, AttributeError):
            raise ValueError("Linha %d: lat/long invalidos." % numero)
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError("Linha %d: coordenada fora do mundo." % numero)
        linhas.append((linha[nomes["id"]], lat, lng))
    if len(linhas) > LIMITE_LINHAS:
        raise ValueError("Maximo de %d linhas por arquivo." % LIMITE_LINHAS)
    return linhas


# consulta todas as linhas e guarda o resultado
def processar(linhas):
    resultado.clear()
    status_linhas.clear()
    for id_, lat, lng in linhas:
        rua, bairro, cep, status = buscar_endereco(lat, lng)
        resultado.append([id_, rua, bairro, cep, lat, lng])
        status_linhas.append(status)
        print("consulta:", id_, status)


# gera o csv para exportar (separador ; e BOM para abrir certo no Excel)
def gerar_csv():
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(CABECALHO)
    for id_, rua, bairro, cep, lat, lng in resultado:
        escritor.writerow([id_, rua, bairro, cep, numero_br(lat), numero_br(lng)])
    return saida.getvalue().encode("utf-8-sig")  # utf-8-sig = utf-8 com BOM


# gera o html para exportar (tabela simples, com escape para nao quebrar)
def gerar_html():
    h = "<html><head><meta charset='utf-8'><title>Resultado</title></head><body>\n"
    h += "<h1>Reverse Geocoding</h1>\n<table border='1' cellpadding='5'>\n<tr>"
    for titulo in CABECALHO:
        h += "<th>" + titulo + "</th>"
    h += "</tr>\n"
    for linha in resultado:
        h += "<tr>" + "".join("<td>" + html.escape(str(v)) + "</td>" for v in linha) + "</tr>\n"
    h += "</table>\n</body></html>"
    return h.encode("utf-8")


def dados_json():
    modo = "SIMULADO (mock)" if URL_API == "" else "REAL (Google)"
    return {"modo": modo, "cabecalho": CABECALHO, "linhas": resultado, "status": status_linhas}


PAGINA = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Geo Busca 2000 - Reverse Geocoding</title>
<style>
  body {
    margin: 0; padding: 10px;
    background-color: #000066;
    background-image: radial-gradient(#ffffff 1px, transparent 1px), radial-gradient(#9999ff 1px, transparent 1px);
    background-size: 40px 40px, 70px 70px;
    background-position: 0 0, 20px 25px;
    color: #ffff00;
    font-family: "Comic Sans MS", "Comic Sans", "Trebuchet MS", Verdana, sans-serif;
    font-size: 14px;
  }
  #miolo { max-width: 860px; margin: 0 auto; background: #c0c0c0; color: #000;
           border: 4px outset #ffffff; padding: 12px; }
  h1 { margin: 0; text-align: center; font-size: 34px; color: #ff0000;
       text-shadow: 2px 2px #ffff00, 4px 4px #0000ff; font-family: Impact, "Arial Black", sans-serif; }
  .sub { text-align: center; color: #000080; font-weight: bold; }
  .arco { height: 6px; border: 0; margin: 10px 0;
          background: linear-gradient(90deg, red, orange, yellow, lime, cyan, blue, magenta); }
  .pisca { animation: pisca 1s steps(2, start) infinite; color: #ff0000; font-weight: bold; }
  @keyframes pisca { to { visibility: hidden; } }
  .caixa { background: #ffffcc; border: 3px ridge #808080; padding: 10px; margin: 8px 0; }
  .marquee { background: #000; color: #00ff00; font-family: "Courier New", monospace;
             border: 2px inset #808080; padding: 3px; }
  button, .botao {
    font-family: inherit; font-size: 14px; font-weight: bold; color: #000;
    background: #c0c0c0; border: 3px outset #ffffff; padding: 4px 14px;
    cursor: pointer; text-decoration: none; display: inline-block;
  }
  button:active, .botao:active { border-style: inset; }
  input[type=file] { font-family: inherit; }
  a { color: #0000ee; }
  a:visited { color: #551a8b; }
  table { border-collapse: separate; border: 4px ridge #808080; background: #ffffff; width: 100%; }
  th { background: #000080; color: #ffffff; padding: 4px; border: 2px outset #ffffff; }
  td { border: 1px solid #808080; padding: 3px 6px; }
  tr:nth-child(even) td { background: #e6e6ff; }
  .erro { color: #ff0000; font-weight: bold; }
  .contador { font-family: "Courier New", monospace; background: #000; color: #ff0000;
              border: 2px inset #808080; padding: 1px 6px; letter-spacing: 3px; }
  .rodape { text-align: center; font-size: 11px; color: #000080; }
</style>
</head>
<body>
<div id="miolo">
  <div class="marquee"><marquee scrollamount="5">*** Bem-vindo ao GEO BUSCA 2000 *** Descubra o endereco de qualquer coordenada *** Importe seu CSV e exporte para o Excel! ***</marquee></div>
  <h1>GEO BUSCA 2000</h1>
  <div class="sub">Transformando Latitude e Longitude em Endereco desde 2026!</div>
  <hr class="arco">

  <div class="caixa">
    <b>PASSO 1 - Importar:</b><br><br>
    Escolha um arquivo <b>.csv</b> com as colunas <b>id, lat, long</b>
    (<a href="/exemplo.csv">baixar arquivo de exemplo</a>):<br><br>
    <input type="file" id="arquivo" accept=".csv,text/csv">
    <button onclick="importar()">Importar e Consultar &raquo;</button>
    <p id="msg"></p>
  </div>

  <div class="caixa">
    <b>PASSO 2 - Exportar:</b><br><br>
    <a class="botao" href="/exportar.csv">Baixar CSV (Excel)</a>
    <a class="botao" href="/exportar.html">Baixar HTML</a>
  </div>

  <div class="sub">Modo da API: <span class="pisca" id="modo">...</span></div>
  <hr class="arco">

  <table>
    <thead><tr id="cab"></tr></thead>
    <tbody id="corpo"></tbody>
  </table>
  <p id="vazio" class="sub">(nenhum resultado ainda - importe um arquivo acima)</p>

  <hr class="arco">
  <p class="sub">Voce e o visitante numero <span class="contador">__VISITAS__</span></p>
  <p class="rodape">Melhor visualizado no Internet Explorer 6 em 800x600.<br>
  <span class="pisca">:: SITE EM CONSTRUCAO ::</span></p>
</div>

<script>
  function msg(texto, erro) {
    var m = document.getElementById("msg");
    m.textContent = texto;
    m.className = erro ? "erro" : "";
  }

  // desenha a tabela (textContent evita injetar html vindo do csv)
  function mostrar(d) {
    document.getElementById("modo").textContent = d.modo;
    var cab = document.getElementById("cab");
    cab.innerHTML = "";
    d.cabecalho.concat(["STATUS"]).forEach(function (t) {
      var th = document.createElement("th"); th.textContent = t; cab.appendChild(th);
    });
    var corpo = document.getElementById("corpo");
    corpo.innerHTML = "";
    d.linhas.forEach(function (linha, i) {
      var tr = document.createElement("tr");
      linha.concat([d.status[i]]).forEach(function (v) {
        var td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
      });
      corpo.appendChild(tr);
    });
    document.getElementById("vazio").style.display = d.linhas.length ? "none" : "block";
  }

  async function importar() {
    var arq = document.getElementById("arquivo").files[0];
    if (!arq) { msg("Escolha um arquivo primeiro!", true); return; }
    msg("Consultando enderecos, aguarde...", false);
    var texto = await arq.text();
    var r = await fetch("/importar", {method: "POST", body: texto,
                                       headers: {"Content-Type": "text/plain; charset=utf-8"}});
    var d = await r.json();
    if (!r.ok) { msg("Erro: " + d.erro, true); return; }
    mostrar(d);
    msg("Pronto! " + d.linhas.length + " linha(s) consultada(s).", false);
  }

  fetch("/dados").then(function (r) { return r.json(); }).then(mostrar);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def enviar(self, codigo, tipo, corpo, arquivo=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        if arquivo:
            self.send_header("Content-Disposition", 'attachment; filename="' + arquivo + '"')
        self.end_headers()
        self.wfile.write(corpo)

    def enviar_json(self, codigo, dados):
        self.enviar(codigo, "application/json; charset=utf-8", json.dumps(dados, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        global visitas
        if self.path == "/":
            visitas += 1
            pagina = PAGINA.replace("__VISITAS__", "%06d" % visitas)
            self.enviar(200, "text/html; charset=utf-8", pagina.encode("utf-8"))
        elif self.path == "/dados":
            self.enviar_json(200, dados_json())
        elif self.path == "/exportar.csv":
            self.enviar(200, "text/csv; charset=utf-8", gerar_csv(), "resultado.csv")
        elif self.path == "/exportar.html":
            self.enviar(200, "text/html; charset=utf-8", gerar_html(), "resultado.html")
        elif self.path == "/exemplo.csv":
            self.enviar(200, "text/csv; charset=utf-8", EXEMPLO.encode("utf-8"), "entrada.csv")
        else:
            self.enviar(404, "text/plain; charset=utf-8", b"404 - pagina nao encontrada")

    def do_POST(self):
        if self.path != "/importar":
            self.enviar(404, "text/plain; charset=utf-8", b"404")
            return
        tamanho = int(self.headers.get("Content-Length", 0))
        if tamanho > LIMITE_BYTES:
            self.enviar_json(413, {"erro": "Arquivo grande demais."})
            return
        try:
            texto = self.rfile.read(tamanho).decode("utf-8-sig")
            processar(ler_csv(texto))
        except (ValueError, UnicodeDecodeError) as erro:
            self.enviar_json(400, {"erro": str(erro)})
            return
        self.enviar_json(200, dados_json())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    modo = "SIMULADO (mock)" if URL_API == "" else "REAL (Google)"
    print("GEO BUSCA 2000 rodando em http://localhost:%d  modo: %s  (Ctrl+C para parar)" % (PORTA, modo))
    HTTPServer(("localhost", PORTA), Handler).serve_forever()
