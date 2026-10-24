"""Robô de atualização das bases (robo/): checagem de forma, recortes e execuções completas contra um portal falso, sem rede."""
import csv
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "robo"))
import anm_recorte  # noqa: E402
import checagem  # noqa: E402
import forma  # noqa: E402
import formato_csv  # noqa: E402
from comum import digital_zip  # noqa: E402

BRUTOS = ROOT / "Squad 1" / "Dados brutos"
P3M = ROOT / "Squad 1" / "P3M"
REC = P3M / "Recortado pelo polígono de Goiás"
CFEM = BRUTOS / "ANM - CFEM" / "CFEM_Arrecadacao_2022_2026_GO.csv"
ALVARA = BRUTOS / "ANM - Cadastro Mineiro" / "Alvara_de_Pesquisa.csv"
SIGMINE = BRUTOS / "ANM - SIGMINE" / "GO.zip"
MALHA = BRUTOS / "IBGE - Malha municipal 2025" / "GO_Municipios_2025.zip"
MINAS = "Minas Ativas (mvw_minas_ativas_grp).zip"
TEM_GEO = all(importlib.util.find_spec(m) for m in ("geopandas", "pyogrio", "shapely"))


def achar(pasta, nome):
    return next(z for z in pasta.glob("*/*.zip") if z.name == nome)


def rezipar(origem, destino, troca=None, data_dbf=b"\x7e\x01\x01"):
    """Copia um zip de shapefile com outra data nos membros e no cabeçalho do .dbf (como o GeoServer faz a cada pedido);
    `troca(nome, bytes)` altera o conteúdo de um membro."""
    with zipfile.ZipFile(origem) as zi, zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            dados = zi.read(info.filename)
            if info.filename.lower().endswith(".dbf"):
                dados = dados[:1] + data_dbf + dados[4:]
            if troca:
                dados = troca(info.filename, dados)
            zo.writestr(zipfile.ZipInfo(info.filename, date_time=(2030, 1, 2, 3, 4, 5)), dados)


class CsvFormaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfem = CFEM.read_bytes()

    def bloqueios(self, novo, sep=";"):
        return forma.checar_csv(novo, self.cfem, "cp1252", sep)[0]

    def test_o_proprio_arquivo_passa(self):
        self.assertEqual(self.bloqueios(self.cfem), [])

    def test_linha_nova_entra_com_aviso(self):
        b, a = forma.checar_csv(self.cfem + self.cfem.splitlines(keepends=True)[1], self.cfem, "cp1252", ";")
        self.assertEqual(b, [])
        self.assertTrue(any("+1 linhas" in x for x in a), a)

    def test_pagina_html_no_lugar_do_csv(self):
        self.assertIn("HTML", self.bloqueios(b"<!DOCTYPE html><html><body>Servico indisponivel</body></html>")[0])

    def test_coluna_renomeada_ou_removida(self):
        cab, resto = self.cfem.split(b"\r\n", 1)
        self.assertIn("saíram", self.bloqueios(cab.replace(b"ValorRecolhido", b"Valor") + b"\r\n" + resto)[0])
        linhas = [ln.rsplit(b";", 1)[0] for ln in self.cfem.split(b"\r\n")]
        self.assertIn("saíram: ['DataCriacao']", self.bloqueios(b"\r\n".join(linhas))[0])

    def test_separador_trocado(self):
        self.assertIn("separador", self.bloqueios(self.cfem.replace(b";", b"|"))[0])

    def test_codificacao_errada(self):
        self.assertIn("não decodifica", self.bloqueios(self.cfem + b"2026;8;1;2020;PJ;\x81;X;GO;1;Y;1;t;1;01/01/2026 00:00\r\n")[0])

    def test_queda_grande_de_linhas(self):
        linhas = self.cfem.split(b"\r\n")
        self.assertIn("menos de 90%", self.bloqueios(b"\r\n".join(linhas[: len(linhas) // 2]))[0])

    def test_coluna_numerica_vira_texto_ou_esvazia(self):
        linhas = self.cfem.decode("cp1252").split("\r\n")
        cab = linhas[0].split(";")
        i = cab.index("ValorRecolhido")
        def mexe(f):
            out = [linhas[0]]
            for ln in linhas[1:]:
                c = ln.split(";")
                if len(c) == len(cab):
                    c[i] = f(c[i])
                out.append(";".join(c))
            return "\r\n".join(out).encode("cp1252")
        self.assertIn("deixou de ser decimal", " ".join(self.bloqueios(mexe(lambda v: "R$ " + v))))
        self.assertIn("esvaziou", " ".join(self.bloqueios(mexe(lambda v: ""))))


class ShapefileFormaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.atual = achar(REC, MINAS)
        self.exig = {"ds_process", "nm_substan"}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def checa(self, troca=None, bruto=None):
        novo = self.tmp / "novo.zip"
        if bruto is not None:
            novo.write_bytes(bruto)
        else:
            rezipar(self.atual, novo, troca)
        return forma.checar_shapefile(novo, self.atual, exigidos=self.exig)

    def test_mesmo_conteudo_passa_e_tem_a_mesma_digital(self):
        self.assertEqual(self.checa()[0], [])
        rezipar(self.atual, self.tmp / "b.zip")
        self.assertEqual(digital_zip(self.tmp / "b.zip"), digital_zip(self.atual))

    def test_digital_acusa_mudanca_de_registro(self):
        def troca(nome, d):
            return d[:-20] + b"X" * 19 + d[-1:] if nome.endswith(".dbf") else d
        rezipar(self.atual, self.tmp / "b.zip", troca)
        self.assertNotEqual(digital_zip(self.tmp / "b.zip"), digital_zip(self.atual))

    def test_xml_de_erro_do_geoserver(self):
        b = self.checa(bruto=b'<?xml version="1.0"?><ServiceExceptionReport>Feature type unknown</ServiceExceptionReport>')[0]
        self.assertIn("não é um zip", b[0])
        # o texto do erro vem no resumo, nas duas formas que o GeoServer usa (WFS 1.0 e 2.0)
        wfs1 = (b'<?xml version="1.0" ?>\n<ServiceExceptionReport version="1.2.0">\n   <ServiceException code="InvalidParameterValue" '
                b'locator="typeName">\n      Feature type geosgb:vw_xpto unknown\n</ServiceException></ServiceExceptionReport>')
        wfs2 = (b'<ows:ExceptionReport version="2.0.0"><ows:Exception exceptionCode="NoApplicableCode"><ows:ExceptionText>'
                b'java.lang.RuntimeException: Unable to find feature type</ows:ExceptionText></ows:Exception></ows:ExceptionReport>')
        self.assertEqual(self.checa(bruto=wfs1)[0], ["o GeoServer devolveu um erro em vez do zip: Feature type geosgb:vw_xpto unknown"])
        self.assertEqual(self.checa(bruto=wfs2)[0],
                         ["o GeoServer devolveu um erro em vez do zip: java.lang.RuntimeException: Unable to find feature type"])

    def test_campo_que_o_site_usa_some(self):
        b = self.checa(lambda n, d: d.replace(b"ds_process", b"ds_procxxx", 1) if n.endswith(".dbf") else d)[0]
        self.assertTrue(any("ds_process" in x and "o site usa" in x for x in b), b)

    def test_geometria_mudou(self):
        def troca(n, d):
            return d[:32] + struct.pack("<i", 1) + d[36:] if n.endswith((".shp", ".shx")) else d
        self.assertIn("geometria mudou", self.checa(troca)[0][0])

    def test_sistema_de_coordenadas_mudou(self):
        wgs = b'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
        b = self.checa(lambda n, d: wgs if n.endswith(".prj") else d)[0]
        self.assertIn("sistema de coordenadas", b[0])

    def test_coordenadas_trocadas(self):
        def troca(n, d):
            if n.endswith((".shp", ".shx")):
                x0, y0, x1, y1 = struct.unpack("<4d", d[36:68])
                return d[:36] + struct.pack("<4d", y0, x0, y1, x1) + d[68:]
            return d
        self.assertTrue(any("caixa" in x for x in self.checa(troca)[0]))

    def test_queda_de_registros(self):
        def troca(n, d):
            return d[:4] + struct.pack("<I", 10) + d[8:] if n.endswith(".dbf") else d
        self.assertIn("registros contra", self.checa(troca)[0][0])


class RecorteAnmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.municipios = anm_recorte.municipios_goias(MALHA)
        cls.processos = anm_recorte.processos_sigmine(SIGMINE)

    def test_cfem_nacional_volta_ao_arquivo_de_goias(self):
        goias = CFEM.read_bytes()
        cab, resto = goias.split(b"\r\n", 1)
        outra = resto.split(b"\r\n", 1)[0].replace(b";GO;", b";MG;")
        nacional = cab + b"\r\n" + outra + b"\r\n" + resto
        recorte, cont = anm_recorte.recortar_uf(nacional)
        self.assertEqual(recorte, goias)
        self.assertEqual(cont["linhas_nacional"], cont["linhas_goias"] + 1)

    def test_coluna_do_recorte_que_sumiu_aparece_no_motivo(self):
        sem_uf = CFEM.read_bytes().replace(b";UF;", b";SiglaEstado;", 1)
        with self.assertRaises(ValueError) as e:
            anm_recorte.recortar_uf(sem_uf)
        self.assertIn("não tem a coluna 'UF'", str(e.exception))
        self.assertIn("SiglaEstado", str(e.exception))  # o cabeçalho novo vai junto, para quem for ajustar

    def test_cadastro_regra_de_municipio_e_processo(self):
        goias = ALVARA.read_bytes()
        cab = goias.split(b"\n", 1)[0] + b"\n"
        modelo = '"Gerência Regional / GO","{p}","Requerimento de Autorização de Pesquisa","Autorização de Pesquisa","00.000.000/0001-00","EMPRESA",' \
                 '"{m}","AREIA","Construção civil","Sim"\n'
        proc_go = sorted(self.processos)[0]
        casos = [("1/1900", "BARRO ALTO - BA", False),                      # homônimo de outro estado: não casa pelo nome
                 ("2/1900", "CACHOEIRA DOURADA - MG, CACHOEIRA DOURADA - GO", True),  # divisa: basta um município de Goiás
                 ("3/1900", "UNAÍ - MG", False),
                 (proc_go, "UNAÍ - MG", True),                                 # processo com poligonal em Goiás
                 ("4/1900", "Goiânia", True)]
        linhas = [modelo.format(p=p, m=m).encode("cp1252") for p, m, _ in casos]
        recorte, _ = anm_recorte.recortar_cadastro(cab + b"".join(linhas), "municipio_ou_processo", self.municipios, self.processos)
        esperado = cab + b"".join(ln for ln, (_, _, fica) in zip(linhas, casos) if fica)
        self.assertEqual(recorte, esperado)

    def test_caracteres_que_nao_sao_quebra_de_linha(self):
        # \x85 é "…" em cp1252 (em latin-1, "próxima linha"); \x0c e \x0b também quebram linha para str.splitlines
        cab = b'"Processo","Municipio(s)","Obs"\r\n'
        linhas = [b'"4/1900","GOIANIA - GO","texto com retic\x85ncias"\r\n',
                  b'"6/1900","ANAPOLIS - GO",sem aspas \x85 e \x0c no meio\r\n',
                  b'"7/1900","SALVADOR - BA","\x0bfora"\r\n',
                  b'"8/1900","CATALAO - GO",cr\rsolto\r\n']
        recorte, cont = anm_recorte.recortar_cadastro(cab + b"".join(linhas), "municipio_ou_processo", self.municipios, set())
        self.assertEqual(recorte, cab + linhas[0] + linhas[1] + linhas[3])
        self.assertEqual((cont["linhas_nacional"], cont["linhas_goias"]), (4, 3))

    def test_campo_com_quebra_de_linha_fica_inteiro(self):
        cab = b'"Processo","Municipio(s)","Obs"\r\n'
        linha = b'"4/1900","GOIANIA - GO","primeira\r\nsegunda; com, virgula"\r\n'
        fora = b'"5/1900","SALVADOR - BA","x"\r\n'
        recorte, cont = anm_recorte.recortar_cadastro(cab + linha + fora, "municipio_ou_processo", self.municipios, set())
        self.assertEqual(recorte, cab + linha)
        self.assertEqual((cont["linhas_nacional"], cont["linhas_goias"]), (2, 1))


def cfem_formato_novo(troca=None, extra=()):
    """A CFEM de Goiás do repositório escrita como a ANM passou a publicar em out/2026: vírgula, aspas em tudo, UTF-8, LF. Aqui
    também com ponto decimal e data ISO, para exercitar a volta. `troca(campos)` mexe em cada linha; `extra` são linhas a mais."""
    import datetime as dt
    import io
    regs = [r for r in CFEM.read_bytes().decode("cp1252").split("\r\n") if r]
    saida = io.StringIO()
    w = csv.writer(saida, delimiter=",", quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(regs[0].split(";"))
    for r in [*regs[1:], *extra]:
        c = r.split(";")
        c[10], c[12] = c[10].replace(",", "."), c[12].replace(",", ".")
        c[13] = dt.datetime.strptime(c[13], "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:00")
        w.writerow(troca(c) if troca else c)
    return saida.getvalue().encode("utf-8")


class FormatoCsvTests(unittest.TestCase):
    """A CFEM nova (vírgula e aspas) volta ao formato que o repositório, o pipeline e o Radar leem."""

    def converter(self, dados):
        f = next(f for f in json.loads((ROOT / "robo" / "fontes.json").read_text(encoding="utf-8"))["anm"]["fontes"] if f["id"] == "CFEM")
        return formato_csv.converter(dados, CFEM.read_bytes(), f["codificacao"], f["separador"], f["recorte"]["coluna"],
                                     f["recorte"]["valor"], f["diagnostico_soma"])

    def test_mesmo_conteudo_volta_byte_a_byte(self):
        de_mg = "2026;1;800001;2001;PJ;1,2E+11;AREIA;MG;3106200;BELO HORIZONTE;5;t  ;10,5;02/01/2026 08:00"
        convertido, cont, notas, diag = self.converter(cfem_formato_novo(extra=[de_mg]))
        self.assertEqual(convertido, CFEM.read_bytes())
        n = CFEM.read_bytes().count(b"\r\n") - 1  # linhas de dados do arquivo atual
        self.assertEqual((cont["linhas_nacional"], cont["linhas_goias"]), (n + 1, n))
        self.assertIn("separador ','", notas[0])
        self.assertTrue(any(n.startswith("ValorRecolhido: separador decimal '.' → ','") for n in notas), notas)
        self.assertTrue(any(n.startswith("DataCriacao: data no padrão") for n in notas), notas)
        self.assertEqual(diag[0], f"linhas do arquivo atual que reaparecem iguais no convertido: {n} de {n}")
        self.assertTrue(any(ln.startswith("  ValorRecolhido por Ano:") and "(igual)" in ln for ln in diag), diag)
        texto = "\n".join(diag)
        for valor in ("ANÁPOLIS", "860582", "41474", "9,69944E+11", "ÁGUA"):  # o diagnóstico vai para o log: só formas, nenhum valor
            self.assertNotIn(valor, texto)

    def test_arquivo_no_formato_antigo_nao_e_convertido(self):
        self.assertIsNone(self.converter(CFEM.read_bytes()))

    def test_correcao_da_fonte_entra_e_passa_na_checagem(self):
        # a ANM corrigindo um valor (como o CNPJ, que até out/2026 vinha em notação científica): fica como a ANM publicou
        def cnpj(c):
            return c[:5] + ["11222333000181"] + c[6:] if c[4] == "PJ" and c[2] == primeira[2] and c[1] == primeira[1] else c
        primeira = next(r.split(";") for r in CFEM.read_bytes().decode("cp1252").split("\r\n")[1:] if ";PJ;" in r)
        convertido, *_ = self.converter(cfem_formato_novo(cnpj))
        self.assertIn(b";11222333000181;", convertido)
        bloq, _ = forma.checar_csv(convertido, CFEM.read_bytes(), "cp1252", ";")
        self.assertEqual(bloq, [])

    def test_valor_que_o_formato_antigo_nao_representa_barra(self):
        def junta(c):
            return c[:6] + [c[6] + "; CASCALHO"] + c[7:] if c[6] == "AREIA" else c
        with self.assertRaises(ValueError) as e:
            self.converter(cfem_formato_novo(junta))
        self.assertIn("Substância", str(e.exception))

    def test_numero_com_dois_estilos_barra(self):
        def mistura(c):
            return c[:12] + [c[12].replace(".", ",")] + c[13:] if c[1] == "1" else c
        with self.assertRaises(ValueError) as e:
            self.converter(cfem_formato_novo(mistura))
        self.assertIn("ValorRecolhido", str(e.exception))

    def test_checagem_barra_ponto_decimal_e_data_iso_sem_conversao(self):
        regs = CFEM.read_bytes().decode("cp1252").split("\r\n")
        ponto = "\r\n".join([regs[0]] + [";".join(c[:12] + [c[12].replace(",", ".")] + c[13:]) for c in (r.split(";") for r in regs[1:] if r)])
        bloq, _ = forma.checar_csv(ponto.encode("cp1252"), CFEM.read_bytes(), "cp1252", ";")
        self.assertTrue(any("ValorRecolhido" in b and "'.'" in b for b in bloq), bloq)
        iso = "\r\n".join([regs[0]] + [";".join(c[:13] + ["2026-08-31 14:05:00"]) for c in (r.split(";") for r in regs[1:] if r)])
        bloq, _ = forma.checar_csv(iso.encode("cp1252"), CFEM.read_bytes(), "cp1252", ";")
        self.assertTrue(any("DataCriacao" in b and "escrita da data" in b for b in bloq), bloq)


class RepositorioTests(unittest.TestCase):
    def test_arquivos_do_repositorio_no_formato_do_site(self):
        self.assertEqual(checagem.checar_repositorio(ROOT), [])

    def test_robo_roda_todos_os_testes_do_site_antes_de_publicar(self):
        # o commit do robô usa o GITHUB_TOKEN e não dispara o validate-web.yml: um teste de lá que falte no robô só quebra depois
        # de publicado (em 24/10/2026, o test_web esperava o número de processos do SIGMINE antigo)
        import re
        validar = (ROOT / ".github" / "workflows" / "validate-web.yml").read_text(encoding="utf-8")
        robo_wf = (ROOT / ".github" / "workflows" / "robo-bases.yml").read_text(encoding="utf-8")
        passo = robo_wf.split("- name: Testes do site", 1)[1].split("- name:", 1)[0]
        faltam = [t for t in re.findall(r"-p (test_\w+)\.py", validar) if not re.search(rf"\b{t}\b", passo)]
        faltam += [js for js in re.findall(r"node (tests/[\w.-]+\.js)", validar) if js not in passo]
        self.assertEqual(faltam, [])

    def test_config_aponta_para_arquivos_que_existem(self):
        cfg = json.loads((ROOT / "robo" / "fontes.json").read_text(encoding="utf-8"))
        for f in cfg["anm"]["fontes"] + cfg["diretos"]["fontes"]:
            alvo = ROOT / f["arquivo_raiz"] if f.get("arquivo_raiz") else BRUTOS / (f.get("arquivo") or f["pasta"])
            self.assertTrue(alvo.exists(), alvo)
            self.assertTrue((f.get("url") or f.get("url_base", "")).startswith("https://"), f["id"])


# ------------------------------------------------------------------------------------------------- ponta a ponta
def copiar(destino, *relativos):
    for r in relativos:
        o, d = ROOT / r, Path(destino) / r
        d.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if o.is_dir() else shutil.copyfile)(o, d)


def robo(raiz, *args):
    p = subprocess.run([sys.executable, str(ROOT / "robo" / "robo_bases.py"), "--raiz", str(raiz), "--hoje", "2030-01-02",
                        "--json", str(Path(raiz) / "saida.json"), *args], capture_output=True, text=True, encoding="utf-8")
    return p, json.loads((Path(raiz) / "saida.json").read_text(encoding="utf-8"))


class AnmPontaAPontaTests(unittest.TestCase):
    """O robô contra um portal falso da ANM (arquivos locais no lugar das URLs)."""

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())
        copiar(self.raiz, "Squad 1/Dados brutos/ANM - CFEM", "Squad 1/Dados brutos/ANM - Cadastro Mineiro",
               "Squad 1/Dados brutos/ANM - SIGMINE", "Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)",
               "Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral", "Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv",
               "Squad 1/Dados brutos/IBGE - Malha municipal 2025", "Squad 1/Dados brutos/datas_de_acesso.json",
               "Squad 1/Dados brutos/LEIA-ME.md", "scripts/mapa_camadas.json")
        self.portal = Path(tempfile.mkdtemp())
        cfg = json.loads((ROOT / "robo" / "fontes.json").read_text(encoding="utf-8"))["anm"]
        self.espelho = {}
        recorte = json.loads((BRUTOS / "ANM - Cadastro Mineiro" / "recorte_goias.json").read_text(encoding="utf-8"))
        for f in cfg["fontes"]:
            if f["tipo"] == "cadastro":
                for item in recorte["arquivos"]:
                    self.servir(f["url_base"] + item["arquivo"], (BRUTOS / f["pasta"] / item["arquivo"]).read_bytes())
            elif f["tipo"] == "shapefile":
                rezipar(BRUTOS / f["arquivo"], self.portal / "GO.zip")  # o mesmo conteúdo, zip refeito
                self.espelho[f["url"]] = (self.portal / "GO.zip").as_uri()
            else:
                self.servir(f["url"], (ROOT / f["arquivo_raiz"] if f.get("arquivo_raiz") else BRUTOS / f["arquivo"]).read_bytes())
        self.cfem_url = next(f["url"] for f in cfg["fontes"] if f["id"] == "CFEM")
        self.rodadas = next(f for f in cfg["fontes"] if f["id"] == "RODADAS")

    def tearDown(self):
        shutil.rmtree(self.raiz)
        shutil.rmtree(self.portal)

    def servir(self, url, dados):
        p = self.portal / (str(len(self.espelho)) + "_" + url.rsplit("/", 1)[1])
        p.write_bytes(dados)
        self.espelho[url] = p.as_uri()

    def rodar(self, *args):
        (self.raiz / "espelho.json").write_text(json.dumps(self.espelho), encoding="utf-8")
        return robo(self.raiz, "--fontes", "anm", "--espelho", str(self.raiz / "espelho.json"), *args)

    def test_sem_novidade_nao_grava_nada(self):
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["situacao"] for r in saida["resultados"]}, {"sem_mudanca"}, saida["resultados"])
        self.assertEqual(saida["gravados"], [])

    def test_cfem_nova_entra_recortada_e_registrada(self):
        goias = CFEM.read_bytes()
        cab, resto = goias.split(b"\r\n", 1)
        nova = b"2026;9;860582;1995;PJ;9,69944E+11;AREIA;GO;5201108;AN\xc1POLIS;10;t  ;99,90;01/09/2026 10:00\r\n"
        de_mg = resto.split(b"\r\n", 1)[0].replace(b";GO;", b";MG;") + b"\r\n"
        self.servir(self.cfem_url, cab + b"\r\n" + de_mg + resto + nova)
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(saida["anm_mudou"])
        gravado = (self.raiz / CFEM.relative_to(ROOT)).read_bytes()
        self.assertEqual(gravado, goias + nova)  # a linha de MG ficou de fora; as de Goiás, byte a byte
        datas = json.loads((self.raiz / "Squad 1/Dados brutos/datas_de_acesso.json").read_text(encoding="utf-8"))
        self.assertEqual(datas["dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"], "2030-01-02")
        antes = json.loads((BRUTOS / "datas_de_acesso.json").read_text(encoding="utf-8"))
        self.assertEqual({k: v for k, v in datas.items() if "/cfem/" not in k}, {k: v for k, v in antes.items() if "/cfem/" not in k})
        # depois de gravar, o repositório continua no formato que o site usa (LEIA-ME, datas, recortes)
        self.assertEqual(checagem.checar_anm(self.raiz), [])

    def test_arquivo_estragado_e_barrado_e_nada_muda(self):
        self.servir(self.cfem_url, b"<html><body>Erro 500</body></html>")
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 1)
        self.assertEqual([r["situacao"] for r in saida["problemas"]], ["bloqueada"])
        self.assertEqual((self.raiz / CFEM.relative_to(ROOT)).read_bytes(), CFEM.read_bytes())
        self.assertEqual(saida["gravados"], [])

    def test_rodadas_novas_entram_em_squad1_dados(self):
        # as rodadas ficam fora de Dados brutos (Squad 1/dados) e não têm data em datas_de_acesso.json
        atual = (ROOT / self.rodadas["arquivo_raiz"]).read_bytes()
        nova = "9;1;860001/2026;Livre;Oferta Pública;Pesquisa;ANÁPOLIS;Goiás;10,50;0,00;;\r\n".encode("utf-8")
        self.servir(self.rodadas["url"], atual + nova)
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((self.raiz / self.rodadas["arquivo_raiz"]).read_bytes(), atual + nova)
        self.assertEqual([r["nome"] for r in saida["resultados"] if r["situacao"] == "atualizada"], [self.rodadas["nome"]])
        self.assertEqual(checagem.checar_anm(self.raiz), [])

    def test_cfem_no_formato_novo_entra_no_formato_antigo(self):
        self.servir(self.cfem_url, cfem_formato_novo())
        p, saida = self.rodar()
        cfem = next(r for r in saida["resultados"] if r["nome"] == "CFEM — arrecadação")
        self.assertEqual(cfem["situacao"], "sem_mudanca", p.stdout + p.stderr)  # mesmo conteúdo: nada a gravar
        n = CFEM.read_bytes().count(b"\r\n") - 1
        self.assertIn(f"[ANM]   linhas do arquivo atual que reaparecem iguais no convertido: {n} de {n}", p.stdout)
        nova = "2026;9;860582;1995;PJ;9,69944E+11;AREIA;GO;5201108;ANÁPOLIS;10;t  ;99,90;01/09/2026 10:00"
        self.servir(self.cfem_url, cfem_formato_novo(extra=[nova]))
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        gravado = (self.raiz / CFEM.relative_to(ROOT)).read_bytes()
        self.assertEqual(gravado, CFEM.read_bytes() + nova.encode("cp1252") + b"\r\n")
        self.assertEqual(checagem.checar_anm(self.raiz), [])

    def test_queda_grande_e_barrada_guardada_e_pode_ser_aceita(self):
        goias = CFEM.read_bytes()
        metade = b"".join(goias.splitlines(keepends=True)[: goias.count(b"\r\n") // 2])
        self.servir(self.cfem_url, metade)
        barrados = self.raiz / "barrados"
        p, saida = self.rodar("--guardar-barrados", str(barrados))
        self.assertEqual(p.returncode, 1)
        self.assertEqual([r["situacao"] for r in saida["problemas"]], ["bloqueada"])
        self.assertIn("menos de 90%", saida["problemas"][0]["motivo"])
        # o que a fonte publicou fica guardado para alguém conferir, com o motivo
        guardado = barrados / ("ANM_" + self.cfem_url.rsplit("/", 1)[1])
        self.assertEqual(guardado.read_bytes(), metade)
        self.assertIn("menos de 90%", (barrados / "LEIA-ME.txt").read_text(encoding="utf-8"))
        self.assertEqual((self.raiz / CFEM.relative_to(ROOT)).read_bytes(), goias)
        # conferida na fonte, a queda é aceita só para a CFEM; as outras checagens continuam valendo
        p, saida = self.rodar("--aceitar-queda", "CFEM")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual((self.raiz / CFEM.relative_to(ROOT)).read_bytes(), metade)
        self.assertEqual(checagem.checar_anm(self.raiz), [])

    def test_queda_no_cadastro_diz_se_o_arquivo_nacional_encolheu(self):
        cfg = json.loads((ROOT / "robo" / "fontes.json").read_text(encoding="utf-8"))["anm"]
        url = next(f["url_base"] for f in cfg["fontes"] if f["tipo"] == "cadastro") + "Portaria_de_Lavra.csv"
        atual = (BRUTOS / "ANM - Cadastro Mineiro" / "Portaria_de_Lavra.csv").read_bytes()
        self.servir(url, atual.split(b"\n", 1)[0] + b"\n")  # só o cabeçalho
        p, saida = self.rodar()
        r = saida["problemas"][0]
        self.assertEqual((r["nome"], r["motivo"]), ("Cadastro Mineiro — Portaria_de_Lavra.csv", "nenhuma linha de dados"))
        antes = next(a for a in json.loads((BRUTOS / "ANM - Cadastro Mineiro" / "recorte_goias.json").read_text(encoding="utf-8"))["arquivos"]
                     if a["arquivo"] == "Portaria_de_Lavra.csv")["linhas_nacional"]
        self.assertIn(f"linhas no arquivo nacional: 0 (antes {antes})", r["avisos"][-1])

    def test_download_que_falha_nao_derruba_as_outras_fontes(self):
        self.espelho[self.cfem_url] = (self.portal / "nao_existe.csv").as_uri()
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 1)
        self.assertEqual([(r["nome"], r["situacao"]) for r in saida["problemas"]], [("CFEM — arrecadação", "falhou")])
        self.assertTrue(all(r["situacao"] == "sem_mudanca" for r in saida["resultados"] if r["nome"] != "CFEM — arrecadação"))


@unittest.skipUnless(TEM_GEO, "precisa de geopandas, pyogrio e shapely (o workflow do robô instala)")
class P3mTests(unittest.TestCase):
    def test_recorte_reproduz_o_repositorio(self):
        import recorte
        go, crs = recorte.limite(P3M / "Original" / "6- Cartografia" / "GO_UF_2024.zip")
        with open(REC / "_indice_recorte.csv", encoding="utf-8-sig", newline="") as f:
            indice = {r["arquivo"]: r for r in csv.DictReader(f, delimiter=";")}
        with tempfile.TemporaryDirectory() as tmp:
            # pontos; polígonos com fiapos de divisa; camada em WGS 84 que o recorte grava em SIRGAS 2000
            for nome in (MINAS, "Distritos Auríferos.zip", "Portos (vw_antaq_inst_portu).zip"):
                saida = Path(tmp) / nome
                n = recorte.recortar_zip(P3M / indice[nome]["origem"], saida, go, crs_saida=crs)
                self.assertEqual(n[1:], (int(indice[nome]["registros_em_goias"]), int(indice[nome]["fiapos_de_divisa_removidos"])), nome)
                self.assertEqual(digital_zip(saida), digital_zip(achar(REC, nome)), nome)

    def test_ponta_a_ponta_com_portal_falso(self):
        import geopandas as gpd
        import recorte
        raiz = Path(tempfile.mkdtemp())
        portal = Path(tempfile.mkdtemp())
        try:
            orig = next(z for z in (P3M / "Original").glob("*/*.zip") if z.name == MINAS)
            rec = achar(REC, MINAS)
            copiar(raiz, "scripts/mapa_camadas.json", "Squad 1/P3M/inventario_p3m.csv", "Squad 1/P3M/Original/6- Cartografia/GO_UF_2024.zip",
                   orig.relative_to(ROOT), rec.relative_to(ROOT), (REC / "_indice_recorte.csv").relative_to(ROOT))
            with open(P3M / "inventario_p3m.csv", encoding="utf-8-sig", newline="") as f:
                inv = list(csv.DictReader(f, delimiter=";"))
            url = next(ln["url_download"] for ln in inv if ln["camada"] == "mvw_minas_ativas_grp")
            espelho = raiz / "espelho.json"

            def rodar(arquivo):
                espelho.write_text(json.dumps({url: Path(arquivo).as_uri()}), encoding="utf-8")
                return robo(raiz, "--fontes", "p3m", "--so", "mvw_minas_ativas_grp", "--sem-inventario", "--espelho", str(espelho))

            # 1. o mesmo conteúdo, zip refeito pelo servidor: nada muda
            rezipar(orig, portal / "igual.zip")
            p, saida = rodar(portal / "igual.zip")
            self.assertEqual([r["situacao"] for r in saida["resultados"]], ["sem_mudanca"], p.stdout + p.stderr)
            # 2. uma mina a menos em Goiás: original e recortado regravados, índice e data do inventário atualizados
            gdf, base = recorte.ler_zip(orig)
            go, _ = recorte.limite(P3M / "Original" / "6- Cartografia" / "GO_UF_2024.zip")
            dentro = gdf.index[gdf.geometry.within(go)][0]
            recorte.gravar_zip(gpd.GeoDataFrame(gdf.drop(index=dentro), crs=gdf.crs), base, portal / "nova.zip")
            p, saida = rodar(portal / "nova.zip")
            self.assertEqual([r["situacao"] for r in saida["resultados"]], ["atualizada"], p.stdout + p.stderr)
            antes = int(next(ln["registros_goias"] for ln in inv if ln["camada"] == "mvw_minas_ativas_grp"))
            self.assertEqual(sum(p["n"] for p in forma.ler_shapefile_zip(raiz / rec.relative_to(ROOT))), antes - 1)
            with open(raiz / "Squad 1/P3M/Recortado pelo polígono de Goiás/_indice_recorte.csv", encoding="utf-8-sig") as f:
                self.assertEqual(next(r for r in csv.DictReader(f, delimiter=";") if r["arquivo"] == MINAS)["registros_em_goias"], str(antes - 1))
            with open(raiz / "Squad 1/P3M/inventario_p3m.csv", encoding="utf-8-sig") as f:
                datas = {r["camada"]: r["data_download"] for r in csv.DictReader(f, delimiter=";")}
            self.assertEqual(datas["mvw_minas_ativas_grp"], "2030-01-02")
            self.assertEqual(sum(d == "2030-01-02" for d in datas.values()), 1)
            # 3. sem um campo que o mapa lê: barrado, nada muda
            antes_bytes = (raiz / rec.relative_to(ROOT)).read_bytes()
            rezipar(orig, portal / "sem_campo.zip", lambda n, d: d.replace(b"nm_substan", b"nm_subxxxx", 1) if n.endswith(".dbf") else d)
            p, saida = rodar(portal / "sem_campo.zip")
            self.assertEqual([r["situacao"] for r in saida["resultados"]], ["bloqueada"])
            self.assertIn("nm_substan", saida["problemas"][0]["motivo"])
            self.assertEqual((raiz / rec.relative_to(ROOT)).read_bytes(), antes_bytes)
        finally:
            shutil.rmtree(raiz)
            shutil.rmtree(portal)


class ChaveDoMapaTests(unittest.TestCase):
    """Camada do mapa que junta vários zips (os mapeamentos geológicos, um por escala): chave repetida barra só os zips dela."""

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())
        mapeamentos = [z for z in REC.glob("*/Mapeamentos 1-*.zip")]
        self.assertEqual(len(mapeamentos), 5)
        copiar(self.raiz, "scripts/mapa_camadas.json", "Squad 1/P3M/inventario_p3m.csv", (REC / "_indice_recorte.csv").relative_to(ROOT),
               achar(REC, MINAS).relative_to(ROOT), *(z.relative_to(ROOT) for z in mapeamentos))
        import p3m
        from comum import Resultado
        self.p3m = p3m.P3M(self.raiz, "2030-01-02", {}, pasta_tmp=self.raiz)
        self.Resultado = Resultado

    def tearDown(self):
        shutil.rmtree(self.raiz)

    def pendente(self, nome, novo_rec):
        r = self.Resultado("P3M", nome, situacao="atualizada")
        self.p3m.pendentes[nome] = {"r": r, "novo_rec": novo_rec}
        return r

    def test_chave_repetida_barra_so_a_camada_dela(self):
        m50, m100 = "Mapeamentos 1-50.000 (vw_cprm_map_geo_50k).zip", "Mapeamentos 1-100.000 (vw_cprm_map_geo_100k).zip"
        r50 = self.pendente(m50, achar(REC, m100))  # a escala 1:50.000 nova com os objectid da 1:100.000
        minas = self.pendente(MINAS, achar(REC, MINAS))
        barrados = self.p3m.conferir_chaves()
        self.assertEqual(barrados, [r50])
        self.assertEqual(r50.situacao, "bloqueada")
        self.assertIn("mapeamentos_geologicos", r50.motivo)
        self.assertIn("objectid repetida", r50.motivo)
        self.assertEqual(minas.situacao, "atualizada")
        self.assertEqual(list(self.p3m.pendentes), [MINAS])

    def test_zip_novo_com_chave_unica_passa(self):
        m50 = "Mapeamentos 1-50.000 (vw_cprm_map_geo_50k).zip"
        r = self.pendente(m50, achar(REC, m50))
        self.assertEqual(self.p3m.conferir_chaves(), [])
        self.assertEqual(r.situacao, "atualizada")


class DiretosTests(unittest.TestCase):
    """IBGE (SIDRA e malhas) e SGB (RECMIN) contra um portal falso."""
    SIDRA = BRUTOS / "IBGE - População e PIB (SIDRA)"
    RECMIN = BRUTOS / "SGB - RECMIN" / "ocorrencias_recursos_minerais_GO.geojson"

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())
        self.portal = Path(tempfile.mkdtemp())
        copiar(self.raiz, (self.SIDRA).relative_to(ROOT), self.RECMIN.parent.relative_to(ROOT),
               "Squad 1/Dados brutos/datas_de_acesso.json", "Squad 1/Dados brutos/LEIA-ME.md")
        self.cfg = {f["id"]: f for f in json.loads((ROOT / "robo" / "fontes.json").read_text(encoding="utf-8"))["diretos"]["fontes"]}
        self.espelho = {}
        for i in ("IBGE_POP", "IBGE_POP_UF", "IBGE_PIB"):
            self.servir(self.cfg[i]["url"], (BRUTOS / self.cfg[i]["arquivo"]).read_bytes())
        # o GeoServer põe a hora do pedido no arquivo: mesmo conteúdo, outro timeStamp
        self.servir(self.cfg["RECMIN"]["url"], self.RECMIN.read_bytes().replace(b'"timeStamp":"2026-09-12T19:19:20.130Z"',
                                                                                 b'"timeStamp":"2030-01-02T10:00:00.000Z"'))

    def tearDown(self):
        shutil.rmtree(self.raiz)
        shutil.rmtree(self.portal)

    def servir(self, url, dados):
        self.n_servidos = getattr(self, "n_servidos", 0) + 1  # um arquivo novo por chamada, mesmo para uma URL já servida
        arq = self.portal / f"{self.n_servidos}.dat"
        arq.write_bytes(dados)
        self.espelho[url] = arq.as_uri()

    def rodar(self, so="IBGE_POP,IBGE_POP_UF,IBGE_PIB,RECMIN"):
        (self.raiz / "espelho.json").write_text(json.dumps(self.espelho), encoding="utf-8")
        return robo(self.raiz, "--fontes", "ibge,sgb", "--so", so, "--espelho", str(self.raiz / "espelho.json"))

    def sidra(self, ident, troca):
        d = json.loads((BRUTOS / self.cfg[ident]["arquivo"]).read_bytes())
        d = [d[0]] + [troca(dict(r)) for r in d[1:]]
        d = [r for r in d if r is not None]
        return json.dumps(d, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode("utf-8")

    def problemas(self):
        return [x for x in checagem.checar_diretos(self.raiz) if "não existe" not in x]  # as malhas não foram copiadas

    def test_sem_novidade_nao_grava_nada(self):
        self.assertEqual(self.problemas(), [])
        p, saida = self.rodar()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["situacao"] for r in saida["resultados"]}, {"sem_mudanca"}, saida["resultados"])
        self.assertEqual(saida["gravados"], [])
        self.assertFalse(saida["base_mudou"])

    def test_populacao_de_ano_novo_entra_com_periodo_e_consulta_no_leiame(self):
        def ano_novo(r):
            r.update(D3C="2026", D3N="2026", V=str(int(r["V"]) + 1))
            return r
        novo = self.sidra("IBGE_POP", ano_novo)
        self.servir(self.cfg["IBGE_POP"]["url"], novo)
        p, saida = self.rodar("IBGE_POP")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(saida["base_mudou"])
        self.assertEqual((self.raiz / BRUTOS.relative_to(ROOT) / self.cfg["IBGE_POP"]["arquivo"]).read_bytes(), novo)
        leiame = (self.raiz / "Squad 1/Dados brutos/LEIA-ME.md").read_text(encoding="utf-8")
        self.assertIn("| 2026 (5571 municípios do Brasil no arquivo; mais 1 linha(s) de nível Unidade da Federação) | 2030-01-02 |", leiame)
        self.assertIn("/n6/all/n3/52/v/9324/p/2026 (consulta equivalente ao arquivo local) (metadados:", leiame)
        datas = json.loads((self.raiz / "Squad 1/Dados brutos/datas_de_acesso.json").read_text(encoding="utf-8"))
        self.assertEqual(datas[self.cfg["IBGE_POP"]["logico"]], "2030-01-02")
        self.assertEqual(self.problemas(), [])

    def test_populacao_de_goias_espera_a_municipal_do_mesmo_ano(self):
        def ano_novo(r):
            r.update(D3C="2026", D3N="2026")
            return r
        uf = self.sidra("IBGE_POP_UF", ano_novo)
        self.servir(self.cfg["IBGE_POP_UF"]["url"], uf)
        p, saida = self.rodar("IBGE_POP_UF")  # a municipal continua em 2025
        r = saida["resultados"][0]
        self.assertEqual(r["situacao"], "pulada", p.stdout + p.stderr)
        self.assertIn("espera a população municipal de 2026", r["motivo"])
        self.assertEqual(p.returncode, 0)
        self.servir(self.cfg["IBGE_POP"]["url"], self.sidra("IBGE_POP", ano_novo))
        p, saida = self.rodar("IBGE_POP,IBGE_POP_UF")  # as duas no mesmo ano: entram juntas
        self.assertEqual([x["situacao"] for x in saida["resultados"]], ["atualizada", "atualizada"], p.stdout + p.stderr)
        self.assertEqual(self.problemas(), [])

    def test_sidra_fora_da_forma_e_barrado(self):
        casos = {
            "unidade": ("IBGE_PIB", lambda r: {**r, "MN": "Reais"}, "unidade de medida mudou"),
            "município de Goiás": ("IBGE_POP", lambda r: None if r["D1C"] == "5201108" else r, "municípios de Goiás diferentes"),
            "ano que volta": ("IBGE_POP", lambda r: {**r, "D3C": "2024", "D3N": "2024"}, "o ano voltou"),
        }
        for caso, (ident, troca, motivo) in casos.items():
            with self.subTest(caso):
                antes = (self.raiz / BRUTOS.relative_to(ROOT) / self.cfg[ident]["arquivo"]).read_bytes()
                self.servir(self.cfg[ident]["url"], self.sidra(ident, troca))
                p, saida = self.rodar(ident)
                self.assertEqual(p.returncode, 1)
                self.assertIn(motivo, saida["problemas"][0]["motivo"])
                self.assertEqual((self.raiz / BRUTOS.relative_to(ROOT) / self.cfg[ident]["arquivo"]).read_bytes(), antes)

    def test_recmin_novo_atualiza_metadados_e_periodo(self):
        j = json.loads(self.RECMIN.read_bytes())
        j["features"] = j["features"][1:]
        j.update(totalFeatures=len(j["features"]), numberMatched=len(j["features"]), numberReturned=len(j["features"]))
        self.servir(self.cfg["RECMIN"]["url"], json.dumps(j, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        p, saida = self.rodar("RECMIN")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        meta = json.loads((self.raiz / self.RECMIN.relative_to(ROOT)).with_name("ocorrencias_recursos_minerais_GO.metadados.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual((meta["feicoes"], meta["numberMatched"]), (len(j["features"]),) * 2)
        self.assertTrue(meta["autorizado_por"].startswith("Eliel"))  # o que não é do download fica
        self.assertEqual(self.problemas(), [])

    def test_recmin_incompleto_e_barrado(self):
        j = json.loads(self.RECMIN.read_bytes())
        j["numberMatched"] = len(j["features"]) + 5
        self.servir(self.cfg["RECMIN"]["url"], json.dumps(j).encode("utf-8"))
        p, saida = self.rodar("RECMIN")
        self.assertEqual(p.returncode, 1)
        self.assertIn("download incompleto", saida["problemas"][0]["motivo"])

    def test_malha_avisa_ano_novo_e_barra_republicacao(self):
        limite = self.cfg["IBGE_LIMITE_UF"]
        copiar(self.raiz, limite["arquivo_raiz"])
        self.servir(limite["url"].format(ano=2024), (ROOT / limite["arquivo_raiz"]).read_bytes())
        self.servir(limite["url"].format(ano=2025), b"existe")
        p, saida = self.rodar("IBGE_LIMITE_UF")
        r = saida["resultados"][0]
        self.assertEqual(r["situacao"], "sem_mudanca", p.stdout + p.stderr)
        self.assertIn("já publicou a malha de 2025", r["avisos"][0])
        rezipar(ROOT / limite["arquivo_raiz"], self.portal / "republicada.zip",
                lambda n, d: d[:-20] + b"X" * 19 + d[-1:] if n.endswith(".dbf") else d)
        self.espelho[limite["url"].format(ano=2024)] = (self.portal / "republicada.zip").as_uri()
        p, saida = self.rodar("IBGE_LIMITE_UF")
        self.assertEqual(saida["problemas"][0]["situacao"], "bloqueada")
        self.assertIn("republicou", saida["problemas"][0]["motivo"])


@unittest.skipUnless(importlib.util.find_spec("openpyxl"), "precisa de openpyxl")
class PlanilhaTests(unittest.TestCase):
    def planilha(self, caminho, linhas):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "14b_validacoes_governanca"
        ws.append(["Validações de governança"])
        ws.append(["verificacao", "n", "resultado", "status"])
        for ln in linhas:
            ws.append(ln)
        wb.save(caminho)

    def test_alerta_novo_bloqueia_e_os_esperados_nao(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx"
            base = [["Plausibilidade: CFEM", 3, "x", "ALERTA"], ["Integridade referencial", 0, "0 órfãos", "OK"],
                    ["Arquivos de dados/ sem source_id no catálogo 07 (fora a documentação)", 0, "nenhum", "OK"]]
            self.planilha(a, base)
            self.planilha(b, [base[0], base[1], [base[2][0], 3, "dados/ANEEL…", "ALERTA"]])
            self.assertEqual(checagem.conferir_planilha(a, b)[0], [])
            self.planilha(b, [base[0], ["Integridade referencial", 5, "5 órfãos", "ALERTA"], base[2]])
            self.assertEqual(len(checagem.conferir_planilha(a, b)[0]), 1)


if __name__ == "__main__":
    unittest.main()
