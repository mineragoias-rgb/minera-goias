# -*- coding: utf-8 -*-
"""MapBiomas: a série anual de cobertura e uso da terra (Coleção 11) recortada para Goiás, na grade do Mapa Mineral.

A fonte é um GeoTIFF de 30 m por ano para o Brasil inteiro (~700 MB cada), no bucket público do MapBiomas no Cloud Storage. O
robô não baixa o arquivo: lê o cabeçalho e, por pedidos de faixa de bytes, só os ladrilhos da caixa de Goiás (~90 MB por ano).
Para cada ano publicado na coleção:
  1. compara a geração e o md5 do arquivo no bucket com os de metadados.json: iguais (e o PNG do ano no lugar), nada a fazer;
  2. confere a forma: TIFF ou BigTIFF em ladrilhos, uma banda de 8 bits, WGS 84 (EPSG:4326), o pixel de 30 m de fontes.json e
     compressão LZW ou deflate;
  3. conta a área de cada classe do MapBiomas dentro do limite de Goiás (IBGE, o mesmo do Mapa Mineral), nos pixels de 30 m:
     pixel com o centro dentro do limite, área na esfera de raio médio;
  4. leva para a grade do mapa, os pixels de Web Mercator do zoom 10 (~150 m), a mesma da vegetação do pacote do Squad 1. Cada
     pixel fica com o grupo que cobre a maior parte da sua área nos pixels de 30 m (um pixel de 30 m conta para o pixel do mapa
     que contém o seu centro): 1 = vegetação nativa florestal ("1. Floresta" da legenda), 2 = vegetação nativa não florestal
     ("2. Vegetação Herbácea e Arbustiva"), 0 = outro uso. Fora de Goiás (centro do pixel fora do limite) também fica 0;
  5. grava vegetacao_nativa_goias_<ano>.png (paleta de 2 bits, o índice 0 transparente) e a linha do ano em metadados.json.

Barra o ano que: muda de forma; tem mais de 0,5% de Goiás sem classe ou em classe fora da legenda; ou perde mais de 10% da
vegetação nativa em relação ao mesmo ano já gravado (republicação), salvo se a queda for aceita. Avisa quando o MapBiomas publica
uma coleção nova no bucket (a troca é no fontes.json).
"""
import hashlib
import json
import re
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

import numpy as np

from comum import AGENTE, FalhaDownload, Resultado

RAIO = 6371008.8  # m, raio médio da Terra (as áreas do mapa usam a mesma esfera)
TIPOS = {1: "B", 2: "B", 3: "H", 4: "I", 5: "II", 6: "b", 7: "B", 8: "h", 9: "i", 10: "ii", 11: "f", 12: "d", 16: "Q", 17: "q", 18: "Q"}


class Leitor:
    """Faixas de bytes de uma URL (cabeçalho Range) ou, no modo espelho, de um arquivo local."""

    def __init__(self, url, espelho=None):
        self.url = url
        local = (espelho or {}).get(url)
        self.local = urllib.request.url2pathname(urllib.parse.urlparse(local).path) if local else None
        self.lidos = 0

    def ler(self, inicio, n, tentativas=4):
        if self.local:
            with open(self.local, "rb") as f:
                f.seek(inicio)
                dados = f.read(n)
        else:
            dados, ultimo = None, None
            for t in range(tentativas):
                try:
                    req = urllib.request.Request(self.url, headers={"User-Agent": AGENTE, "Range": f"bytes={inicio}-{inicio + n - 1}"})
                    with urllib.request.urlopen(req, timeout=300) as r:
                        dados = r.read()
                    break
                except (urllib.error.URLError, OSError, TimeoutError) as e:
                    ultimo = e
                    if isinstance(e, urllib.error.HTTPError) and e.code in (400, 401, 403, 404, 410, 416):
                        break
                    time.sleep(5 * (t + 1))
            if dados is None:
                raise FalhaDownload(f"{type(ultimo).__name__}: {ultimo}")
        if len(dados) != n:
            raise FalhaDownload(f"pedi {n} bytes a partir de {inicio} e vieram {len(dados)}")
        self.lidos += n
        return dados


def ler_cabecalho(leitor):
    """O primeiro IFD (a imagem inteira) de um TIFF ou BigTIFF: {tag: tupla de valores}."""
    cab = leitor.ler(0, 16)
    if cab[:2] not in (b"II", b"MM"):
        raise ValueError("não é TIFF")
    e = "<" if cab[:2] == b"II" else ">"
    versao = struct.unpack(e + "H", cab[2:4])[0]
    if versao not in (42, 43):
        raise ValueError(f"TIFF de versão {versao}")
    big = versao == 43
    off = struct.unpack(e + "Q", cab[8:16])[0] if big else struct.unpack(e + "I", cab[4:8])[0]
    n_tam, ent_tam = (8, 20) if big else (2, 12)
    n = struct.unpack(e + ("Q" if big else "H"), leitor.ler(off, n_tam))[0]
    entradas = leitor.ler(off + n_tam, n * ent_tam)
    tags = {}
    for k in range(n):
        ent = entradas[k * ent_tam:(k + 1) * ent_tam]
        tag, tipo = struct.unpack(e + "HH", ent[:4])
        cont = struct.unpack(e + ("Q" if big else "I"), ent[4:12 if big else 8])[0]
        fmt = TIPOS.get(tipo)
        if fmt is None:
            continue
        total = cont * struct.calcsize(e + fmt)
        valor = ent[12:20] if big else ent[8:12]
        if total > len(valor):
            raw = leitor.ler(struct.unpack(e + ("Q" if big else "I"), valor)[0], total)
        else:
            raw = valor[:total]
        tags[tag] = raw.rstrip(b"\0").decode("latin-1") if tipo == 2 else struct.unpack(e + fmt * cont, raw)
    return tags


def conferir_forma(tags, cfg):
    """Problemas de forma do GeoTIFF (lista vazia = segue)."""
    p = []
    um = lambda t, padrao=None: tags[t][0] if t in tags else padrao  # noqa: E731
    if um(258) != 8 or um(277, 1) != 1 or um(339, 1) != 1 or um(284, 1) != 1:
        p.append("não é uma banda de 8 bits sem sinal")
    if 322 not in tags or 324 not in tags:
        p.append("não é em ladrilhos")
    if um(259) not in (5, 8, 32946):
        p.append(f"compressão {um(259)} (o robô lê LZW e deflate)")
    if um(317, 1) not in (1, 2):
        p.append(f"preditor {um(317)}")
    geo = tags.get(34735, ())
    chaves = {geo[i]: geo[i + 3] for i in range(4, len(geo) - 3, 4)}
    if chaves.get(2048) != 4326:
        p.append(f"sistema de coordenadas {chaves.get(2048)} (esperado EPSG:4326)")
    escala = tags.get(33550, (0, 0))
    if abs(escala[0] - cfg["pixel_graus"]) > 1e-9 or abs(escala[1] - cfg["pixel_graus"]) > 1e-9:
        p.append(f"pixel de {escala[:2]} graus (esperado {cfg['pixel_graus']})")
    return p


def ler_janela(leitor, tags, c0, c1, r0, r1, max_pedido=32 << 20):
    """Pixels das colunas c0..c1 e linhas r0..r1 (inclusive), lendo só os ladrilhos que as cobrem; trechos contíguos de uma
    linha de ladrilhos vão num pedido só. Ladrilho vazio (offset 0) fica 0."""
    T, Tl = tags[322][0], tags[323][0]
    nx = -(-tags[256][0] // T)
    offs, nbs = tags[324], tags[325]
    comp, pred = tags[259][0], tags.get(317, (1,))[0]
    if comp == 5:
        import imagecodecs  # só o LZW precisa (o MapBiomas grava em LZW); os testes usam deflate
        descomprimir = imagecodecs.lzw_decode
    else:
        descomprimir = zlib.decompress
    tc0, tc1, tr0, tr1 = c0 // T, c1 // T, r0 // Tl, r1 // Tl
    img = np.zeros(((tr1 - tr0 + 1) * Tl, (tc1 - tc0 + 1) * T), np.uint8)
    for tr in range(tr0, tr1 + 1):
        cheios = [(tc, offs[tr * nx + tc], nbs[tr * nx + tc]) for tc in range(tc0, tc1 + 1) if nbs[tr * nx + tc]]
        trechos = []
        for tc, o, nb in cheios:
            if trechos and o == trechos[-1][1] and o + nb - trechos[-1][0] <= max_pedido:
                trechos[-1][1] = o + nb
                trechos[-1][2].append((tc, o, nb))
            else:
                trechos.append([o, o + nb, [(tc, o, nb)]])
        for a, b, itens in trechos:
            dados = leitor.ler(a, b - a)
            for tc, o, nb in itens:
                bloco = np.frombuffer(descomprimir(dados[o - a:o - a + nb]), np.uint8)[:T * Tl].reshape(Tl, T)
                if pred == 2:
                    bloco = np.cumsum(bloco, axis=1, dtype=np.uint8)  # diferença horizontal
                img[(tr - tr0) * Tl:(tr - tr0 + 1) * Tl, (tc - tc0) * T:(tc - tc0 + 1) * T] = bloco
    return img[r0 - tr0 * Tl:r1 - tr0 * Tl + 1, c0 - tc0 * T:c1 - tc0 * T + 1]


def limite_goias(raiz, cfg):
    import shapefile
    import shapely
    from shapely.geometry import shape
    with zipfile.ZipFile(raiz / cfg["limite"]) as z:
        nomes = {Path(n).suffix.lower(): n for n in z.namelist()}
        leitor = shapefile.Reader(shp=BytesIO(z.read(nomes[".shp"])), shx=BytesIO(z.read(nomes[".shx"])), dbf=BytesIO(z.read(nomes[".dbf"])))
        return shapely.union_all([shape(s.__geo_interface__) for s in leitor.shapes()])


def intervalos(go, lats, lon_c0, passo, n):
    """Para cada linha (latitude do centro), as faixas [c0, c1) de colunas cujo centro (lon_c0 + c·passo) cai dentro do polígono.
    Varredura: o cruzamento de cada aresta dos anéis com cada linha e a regra par-ímpar (buracos e ilhas se resolvem sozinhos)."""
    aneis = [np.asarray(a.coords) for pg in getattr(go, "geoms", [go]) for a in (pg.exterior, *pg.interiors)]
    E = np.concatenate([np.stack([a[:-1, 0], a[:-1, 1], a[1:, 0], a[1:, 1]], 1) for a in aneis])
    E = E[E[:, 1] != E[:, 3]]
    lats = np.asarray(lats, float)
    ordem_lat = np.argsort(lats)
    lat_ord = lats[ordem_lat]
    ymin, ymax = np.minimum(E[:, 1], E[:, 3]), np.maximum(E[:, 1], E[:, 3])
    i0, i1 = np.searchsorted(lat_ord, ymin, "left"), np.searchsorted(lat_ord, ymax, "left")  # linhas com ymin <= lat < ymax
    k = i1 - i0
    E, i0, k = E[k > 0], i0[k > 0], k[k > 0]
    aresta = np.repeat(np.arange(len(E)), k)
    pos = i0[aresta] + np.arange(int(k.sum())) - np.repeat(np.cumsum(k) - k, k)
    la = lat_ord[pos]
    x0, y0, x1, y1 = E[aresta].T
    x = x0 + (la - y0) * (x1 - x0) / (y1 - y0)
    linha = ordem_lat[pos]
    ordem = np.lexsort((x, linha))
    linha, x = linha[ordem], x[ordem]
    saida = [[] for _ in lats]
    for y, xa, xb in zip(linha[0::2], x[0::2], x[1::2]):
        a = max(0, int(np.ceil((xa - lon_c0) / passo)))
        b = min(n, int(np.floor((xb - lon_c0) / passo)) + 1)
        if b > a:
            saida[y].append((a, b))
    return saida


def mercator_y(lat, n_mundo):
    la = np.radians(np.asarray(lat, float))
    return (1 - np.log(np.tan(la) + 1 / np.cos(la)) / np.pi) / 2 * n_mundo


def lat_mercator(y, n_mundo):
    return np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * np.asarray(y, float) / n_mundo))))


def png_paleta(pixels, paleta):
    """PNG de paleta (2 bits por pixel) com o índice 0 transparente; filtro 0 em toda linha. Só zlib e struct."""
    h, w = pixels.shape
    larg = -(-w // 4) * 4
    p = np.zeros((h, larg), np.uint8)
    p[:, :w] = pixels
    q = p.reshape(h, larg // 4, 4)
    linhas = (q[:, :, 0] << 6) | (q[:, :, 1] << 4) | (q[:, :, 2] << 2) | q[:, :, 3]
    bruto = np.concatenate([np.zeros((h, 1), np.uint8), linhas.astype(np.uint8)], 1).tobytes()

    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 2, 3, 0, 0, 0))
            + bloco(b"PLTE", bytes(c for cor in paleta for c in cor)) + bloco(b"tRNS", b"\x00" + b"\xff" * (len(paleta) - 1))
            + bloco(b"IDAT", zlib.compress(bruto, 9)) + bloco(b"IEND", b""))


def ler_png_paleta(png):
    """Índices de um PNG de paleta sem entrelaçamento e com filtro 0 em toda linha (como png_paleta grava)."""
    o, idat = 8, b""
    while o < len(png):
        n, tipo = struct.unpack(">I", png[o:o + 4])[0], png[o + 4:o + 8]
        if tipo == b"IHDR":
            w, h, bits = struct.unpack(">IIB", png[o + 8:o + 17])
        elif tipo == b"IDAT":
            idat += png[o + 8:o + 8 + n]
        o += 12 + n
    bruto = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, -1)
    if np.any(bruto[:, 0]):
        raise ValueError("PNG com filtro diferente de 0")
    por_byte = 8 // bits
    px = np.stack([(bruto[:, 1:] >> (8 - bits * (k + 1))) & (2 ** bits - 1) for k in range(por_byte)], 2).reshape(h, -1)
    return px[:, :w]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def url_lista(cfg, token=None):
    """Consulta da API JSON do Cloud Storage com os arquivos da coleção (os testes montam a mesma URL no espelho)."""
    q = {"prefix": cfg["prefixo"], "fields": "items(name,size,md5Hash,generation,updated),nextPageToken"}
    if token:
        q["pageToken"] = token
    return cfg["api"] + "?" + urllib.parse.urlencode(q)


def url_colecoes(cfg):
    return cfg["api"] + "?" + urllib.parse.urlencode({"prefix": cfg["prefixo_colecoes"], "delimiter": "/"})


class MapBiomas:
    def __init__(self, raiz, hoje, cfg, gravar=True, espelho=None, aceitar=(), anos=None):
        self.raiz, self.hoje, self.cfg, self.gravar = Path(raiz), hoje, cfg, gravar
        self.anos = anos  # None = todos os anos da coleção
        self.espelho = espelho or {}
        self.aceitar = set(aceitar)
        self.pasta = self.raiz / cfg["pasta"]
        self.meta_path = self.pasta / "metadados.json"
        self.meta = json.loads(self.meta_path.read_text(encoding="utf-8")) if self.meta_path.exists() else {"anos": {}}
        self.mudou = False
        self._go = None

    # ------------------------------------------------------------------------------------------------- bucket
    def _json(self, url):
        local = self.espelho.get(url)
        if local:
            return json.loads(Path(urllib.request.url2pathname(urllib.parse.urlparse(local).path)).read_text(encoding="utf-8"))
        req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def listar(self):
        """{ano: objeto do bucket (name, size, md5Hash, generation, updated)} da coleção configurada."""
        cfg, itens, token = self.cfg, [], None
        while True:
            d = self._json(url_lista(cfg, token))
            itens += d.get("items", [])
            token = d.get("nextPageToken")
            if not token:
                break
        padrao = re.compile(re.escape(cfg["arquivo_fonte"]).replace(r"\{ano\}", r"(\d{4})") + "$")
        return {int(m.group(1)): it for it in itens for m in [padrao.search(it["name"])] if m}

    def colecao_nova(self):
        """Número da coleção mais nova do bucket, se for maior que a configurada."""
        d = self._json(url_colecoes(self.cfg))
        # collection_71 é a Coleção 7.1: número de dois dígitos acima de 50 é versão com ponto
        nums = [n / 10 if n > 50 else n for p in d.get("prefixes", []) for m in [re.search(r"collection_?(\d+)/$", p)] if m for n in [int(m.group(1))]]
        maior = max(nums, default=0)
        return maior if maior > self.cfg["colecao"] else None

    # ------------------------------------------------------------------------------------------------- grade
    @property
    def go(self):
        if self._go is None:
            import shapely
            self._go = limite_goias(self.raiz, self.cfg)
            shapely.prepare(self._go)
        return self._go

    def grade(self):
        """Pixels de Web Mercator do zoom de fontes.json que cobrem o limite de Goiás: origem (X0, Y0), largura e altura."""
        n_mundo = 256 * 2 ** self.cfg["zoom"]
        x0, y0, x1, y1 = self.go.bounds
        X0, X1 = int(np.floor((x0 + 180) / 360 * n_mundo)), int(np.ceil((x1 + 180) / 360 * n_mundo))
        Y0, Y1 = int(np.floor(mercator_y(y1, n_mundo))), int(np.ceil(mercator_y(y0, n_mundo)))
        return {"zoom": self.cfg["zoom"], "origem_px": [X0, Y0], "largura": X1 - X0, "altura": Y1 - Y0}

    # ------------------------------------------------------------------------------------------------- um ano
    def processar(self, ano, objeto):
        """(pixels da grade, contagens, áreas por classe em ha, problemas, avisos, bytes lidos) de um ano."""
        cfg = self.cfg
        url = cfg["bucket"] + objeto["name"]
        leitor = Leitor(url, self.espelho)
        tags = ler_cabecalho(leitor)
        problemas = conferir_forma(tags, cfg)
        if problemas:
            return None, None, None, problemas, [], leitor.lidos
        dx = tags[33550][0]
        lon0, lat0 = tags[33922][3], tags[33922][4]
        W, H = tags[256][0], tags[257][0]
        gx0, gy0, gx1, gy1 = self.go.bounds
        c0, c1 = max(0, int((gx0 - lon0) / dx) - 1), min(W - 1, int((gx1 - lon0) / dx) + 1)
        r0, r1 = max(0, int((lat0 - gy1) / dx) - 1), min(H - 1, int((lat0 - gy0) / dx) + 1)
        src = ler_janela(leitor, tags, c0, c1, r0, r1)
        hs, ws = src.shape
        lon_s = lon0 + (c0 + np.arange(ws) + 0.5) * dx  # centros
        lat_s = lat0 - (r0 + np.arange(hs) + 0.5) * dx

        # áreas por classe dentro de Goiás, nos pixels de 30 m
        area = np.zeros(256)
        ha_linha = np.abs(np.sin(np.radians(lat_s + dx / 2)) - np.sin(np.radians(lat_s - dx / 2))) * RAIO ** 2 * np.radians(dx) / 1e4
        for y, faixas in enumerate(intervalos(self.go, lat_s, lon_s[0], dx, ws)):
            for a, b in faixas:
                area += np.bincount(src[y, a:b], minlength=256) * ha_linha[y]
        areas = {str(c): round(float(area[c]), 1) for c in np.nonzero(area)[0]}

        # grade do mapa: grupo que cobre a maior parte de cada pixel
        g = self.grade()
        n_mundo = 256 * 2 ** g["zoom"]
        X0, Y0, GW, GH = g["origem_px"][0], g["origem_px"][1], g["largura"], g["altura"]
        gx = np.floor((lon_s + 180) / 360 * n_mundo).astype(np.int64) - X0
        gy = np.floor(mercator_y(lat_s, n_mundo)).astype(np.int64) - Y0
        okc, okr = (gx >= 0) & (gx < GW), (gy >= 0) & (gy < GH)
        cols = np.nonzero(okc)[0]
        c_ini = np.r_[0, np.nonzero(np.diff(gx[okc]))[0] + 1]
        dest_c = gx[okc][c_ini]
        lut = np.full(256, 3, np.uint8)  # 3 = outro uso
        lut[0] = 0  # sem dado
        for k, grp in cfg["grupos"].items():
            lut[grp["classes"]] = int(k)
        pix = np.zeros((GH, GW), np.uint8)
        linhas_ok = np.nonzero(okr)[0]
        destinos = gy[linhas_ok]
        for gy_alvo in np.unique(destinos):
            fonte = linhas_ok[destinos == gy_alvo]
            bloco = lut[src[fonte[0]:fonte[-1] + 1, cols[0]:cols[-1] + 1]]
            cont = [np.add.reduceat((bloco == k).sum(0, dtype=np.uint16), c_ini) for k in (1, 2, 3)]
            linha = np.zeros(len(c_ini), np.uint8)
            linha[(cont[0] >= cont[1]) & (cont[0] > cont[2])] = 1
            linha[(cont[1] > cont[0]) & (cont[1] > cont[2])] = 2
            pix[gy_alvo, dest_c] = linha
        # fora de Goiás (centro do pixel do mapa fora do limite) fica vazio
        dentro = np.zeros((GH, GW), bool)
        lat_g = lat_mercator(Y0 + np.arange(GH) + 0.5, n_mundo)
        for y, faixas in enumerate(intervalos(self.go, lat_g, (X0 + 0.5) / n_mundo * 360 - 180, 360 / n_mundo, GW)):
            for a, b in faixas:
                dentro[y, a:b] = True
        pix[~dentro] = 0
        contagens = {k: int(np.count_nonzero(pix == int(k))) for k in cfg["grupos"]}

        avisos = []
        total = sum(area)
        sem = area[0] / total if total else 1
        fora = {c: v for c, v in areas.items() if c != "0" and c not in cfg["legenda"]}
        if sem > cfg["sem_classe_max"]:
            problemas.append(f"{100 * sem:.2f}% de Goiás sem classe (pixel 0)")
        if sum(fora.values()) > cfg["fora_da_legenda_max"] * total:
            problemas.append(f"classes fora da legenda cobrem {100 * sum(fora.values()) / total:.2f}% de Goiás: {sorted(fora)}")
        elif fora:
            avisos.append(f"classe(s) {', '.join(sorted(fora, key=int))} fora da legenda da Coleção 10: {sum(fora.values()):,.1f} ha em Goiás, contadas como outro uso")
        return pix, contagens, areas, problemas, avisos, leitor.lidos

    def rodar(self):
        cfg = self.cfg
        resultados = []
        try:
            objetos = self.listar()
        except (urllib.error.URLError, OSError, ValueError, FalhaDownload) as e:
            return [Resultado("MapBiomas", cfg["nome"], situacao="falhou", motivo=f"lista do bucket: {e}")]
        avisos_gerais = []
        try:
            nova = self.colecao_nova()
            if nova:
                avisos_gerais.append(f"o MapBiomas publicou a coleção {nova}; o repositório usa a {cfg['colecao']} (trocar no fontes.json)")
        except (urllib.error.URLError, OSError, ValueError):
            pass
        sem_mudanca = []
        for ano in sorted(objetos):
            if self.anos and ano not in self.anos:
                continue
            obj = objetos[ano]
            antigo = self.meta["anos"].get(str(ano), {})
            png_path = self.pasta / cfg["arquivo"].format(ano=ano)
            if (antigo.get("geracao") == obj["generation"] and antigo.get("md5_fonte") == obj["md5Hash"] and png_path.exists()
                    and sha256_bytes(png_path.read_bytes()) == antigo.get("sha256")):
                sem_mudanca.append(ano)
                continue
            r = Resultado("MapBiomas", f"{cfg['nome']} — {ano}")
            try:
                pix, contagens, areas, problemas, avisos, lidos = self.processar(ano, obj)
            except (FalhaDownload, urllib.error.URLError, OSError) as e:
                r.situacao, r.motivo = "falhou", str(e)
                resultados.append(r)
                continue
            except ValueError as e:
                r.situacao, r.motivo = "bloqueada", str(e)
                resultados.append(r)
                continue
            r.avisos += avisos
            if not problemas and antigo.get("area_ha_grupos"):
                nativa_antes = sum(antigo["area_ha_grupos"].values())
                nativa = sum(sum(areas.get(str(c), 0) for c in grp["classes"]) for grp in cfg["grupos"].values())
                if nativa < cfg["fracao_minima"] * nativa_antes and str(ano) not in self.aceitar:
                    problemas.append(f"vegetação nativa caiu de {nativa_antes:,.0f} para {nativa:,.0f} ha no mesmo ano")
            if problemas:
                r.situacao, r.motivo = "bloqueada", "; ".join(problemas)
                resultados.append(r)
                continue
            r.situacao, r.motivo = "atualizada", "ano novo" if not antigo else "republicado na fonte"
            r.detalhes = {"bytes_lidos": lidos, "pixels": contagens}
            if self.gravar:
                paleta = [[255, 255, 255]] + [[int(grp["cor"][k:k + 2], 16) for k in (1, 3, 5)] for grp in cfg["grupos"].values()]
                png = png_paleta(pix, paleta)
                self.pasta.mkdir(parents=True, exist_ok=True)
                png_path.write_bytes(png)
                self.meta["anos"][str(ano)] = {
                    "arquivo": png_path.name, "fonte": cfg["bucket"] + obj["name"], "geracao": obj["generation"],
                    "md5_fonte": obj["md5Hash"], "bytes_fonte": int(obj["size"]), "atualizado_na_fonte": obj["updated"][:10],
                    "baixado_em": self.hoje, "bytes_lidos": lidos, "sha256": sha256_bytes(png), "pixels": contagens,
                    "area_ha_grupos": {k: round(sum(areas.get(str(c), 0) for c in grp["classes"]), 1) for k, grp in cfg["grupos"].items()},
                    "area_ha_classes": areas}
                r.arquivos.append(png_path.relative_to(self.raiz).as_posix())
                self.mudou = True
            resultados.append(r)
            print(f"[MapBiomas {ano}] {r.situacao} ({lidos / 1e6:.0f} MB lidos do GeoTIFF)", flush=True)
        if sem_mudanca or not resultados:
            r = Resultado("MapBiomas", cfg["nome"], situacao="sem_mudanca",
                          motivo=f"{len(sem_mudanca)} anos sem mudança na fonte" if sem_mudanca else "nenhum ano na fonte")
            resultados.append(r)
        (resultados[-1].avisos if resultados else []).extend(avisos_gerais)
        return resultados

    def salvar(self):
        if not (self.gravar and self.mudou):
            return []
        g = self.grade()
        cfg = self.cfg
        self.meta = {
            "fonte": f"MapBiomas Brasil — Coleção {cfg['colecao']}, cobertura e uso da terra (GeoTIFF anual de 30 m, bucket público mapbiomas-public)",
            "colecao": cfg["colecao"], "legenda": cfg["legenda_fonte"], "limite": cfg["limite"],
            "grade": {"crs": "pixels de Web Mercator (EPSG:3857)", **g},
            "metodo": ("Cada pixel da grade fica com o grupo que cobre a maior parte da sua área nos pixels de 30 m (o pixel de 30 m conta "
                       "para o pixel da grade que contém o seu centro); fora do limite de Goiás (centro do pixel fora) fica 0. Áreas por "
                       "classe: pixels de 30 m com o centro dentro do limite, na esfera de raio médio."),
            "grupos": {k: {"nome": v["nome"], "legenda": v["legenda"], "classes": v["classes"]} for k, v in cfg["grupos"].items()},
            "anos": dict(sorted(self.meta["anos"].items())),
        }
        self.meta_path.write_text(json.dumps(self.meta, ensure_ascii=False, indent=1), encoding="utf-8")
        return [self.meta_path.relative_to(self.raiz).as_posix()]
