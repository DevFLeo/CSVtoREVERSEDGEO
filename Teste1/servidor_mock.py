# servidor_mock.py - servidor falso que imita a API de Geocoding reverso do Google
# Serve para testar o projeto SEM gastar a API de verdade.
# Roda em http://localhost:8000/maps/api/geocode/json?latlng=LAT,LONG&key=QUALQUER_COISA
#
# Como rodar: python Teste1/servidor_mock.py

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORTA = 8000

# enderecos de mentira (lat, long, rua, bairro, cidade, estado, cep)
ENDERECOS = [
    (-23.561414, -46.655881, "Avenida Paulista", "Bela Vista", "São Paulo", "SP", "01310-100"),
    (-22.906847, -43.172897, "Rua da Assembleia", "Centro", "Rio de Janeiro", "RJ", "20011-000"),
    (-19.919052, -43.938669, "Avenida Afonso Pena", "Centro", "Belo Horizonte", "MG", "30130-003"),
    (-8.763170, -63.889806, "Rua Duque de Caxias", "Nossa Senhora das Graças", "Porto Velho", "RO", "76804-120"),
]


# monta um componente do endereco no mesmo formato do Google
def componente(nome, tipos):
    return {"long_name": nome, "short_name": nome, "types": tipos}


# procura o endereco mais perto da coordenada (tolerancia de 0.01 grau)
def achar_endereco(lat, lng):
    for e in ENDERECOS:
        if abs(e[0] - lat) < 0.01 and abs(e[1] - lng) < 0.01:
            return e
    return None


# monta a resposta no formato do Google
def montar_resposta(lat, lng):
    e = achar_endereco(lat, lng)
    if e is None:
        return {"results": [], "status": "ZERO_RESULTS"}
    _, _, rua, bairro, cidade, estado, cep = e
    componentes = [
        componente("100", ["street_number"]),
        componente(rua, ["route"]),
        componente(bairro, ["sublocality_level_1", "sublocality", "political"]),
        componente(cidade, ["administrative_area_level_2", "political"]),
        componente(estado, ["administrative_area_level_1", "political"]),
        componente("Brasil", ["country", "political"]),
        componente(cep, ["postal_code"]),
    ]
    resultado = {
        "address_components": componentes,
        "formatted_address": rua + ", " + bairro + ", " + cidade + " - " + estado + ", " + cep + ", Brasil",
        "geometry": {"location": {"lat": lat, "lng": lng}},
        "types": ["street_address"],
    }
    return {"results": [resultado], "status": "OK"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)

        if url.path != "/maps/api/geocode/json":
            self.responder(404, {"status": "NOT_FOUND"})
            return

        # o Google recusa pedidos sem chave, entao o mock tambem recusa
        if "key" not in params or params["key"][0] == "":
            self.responder(200, {"results": [], "status": "REQUEST_DENIED",
                                 "error_message": "You must use an API key."})
            return

        try:
            lat, lng = params["latlng"][0].split(",")
            dados = montar_resposta(float(lat), float(lng))
        except (KeyError, ValueError):
            dados = {"results": [], "status": "INVALID_REQUEST"}

        print("pedido:", params.get("latlng"), "->", dados["status"])
        self.responder(200, dados)

    def responder(self, codigo, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    # silencia o log padrao (ja imprimimos o que interessa)
    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Mock da API do Google rodando em http://localhost:%d (Ctrl+C para parar)" % PORTA)
    HTTPServer(("localhost", PORTA), Handler).serve_forever()
