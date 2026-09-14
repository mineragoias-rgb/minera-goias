from fastapi import FastAPI, Query
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="MINERA Goiás API")

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "db_minera_goias"),
        cursorclass=pymysql.cursors.DictCursor
    )

def schema_version(cursor):
    """Support every shape the database may be in; deployment never migrates by itself.
    'v2' is the schema that keys the holder by name, 'anm' the one that required a
    document, 'legacy' the original surrogate-key model still installed on the VPS.
    """
    cursor.execute("SHOW COLUMNS FROM tb_projetos LIKE 'empresa_id'")
    if cursor.fetchall():
        return 'v2'
    cursor.execute("SHOW COLUMNS FROM tb_projetos LIKE 'processo_anm'")
    return 'anm' if cursor.fetchall() else 'legacy' 

@app.get("/api/projetos")
def listar_projetos():
    conn=get_connection()
    try:
        with conn.cursor() as cursor:
            version = schema_version(cursor)
            if version == 'v2':
                # The cadastral source names individual people as holders, so this
                # public endpoint reports the claim without naming anyone. Tax
                # identifiers and holder names stay out of unauthenticated output.
                cursor.execute("""
                    SELECT p.processo_anm, m.mineral_name, p.substancia_anm, p.fase,
                           p.uso, p.categoria, p.poligonos,
                           GROUP_CONCAT(mu.nome_municipio SEPARATOR '; ') AS municipios
                    FROM tb_projetos p
                    LEFT JOIN tb_minerais m ON p.mineral_id=m.mineral_id
                    LEFT JOIN tb_projeto_municipio pm ON p.processo_anm=pm.processo_anm
                    LEFT JOIN tb_municipios mu ON pm.codigo_ibge=mu.codigo_ibge
                    GROUP BY p.processo_anm,m.mineral_name,p.substancia_anm,p.fase,
                             p.uso,p.categoria,p.poligonos
                """)
            elif version == 'anm':
                # Personal/company tax identifiers are join keys, not public output.
                cursor.execute("""
                    SELECT p.processo_anm, e.nome_empresa,
                           m.mineral_name, p.substancia_anm, p.fase, p.categoria,
                           GROUP_CONCAT(mu.nome_municipio SEPARATOR '; ') AS municipios
                    FROM tb_projetos p
                    JOIN tb_empresas e ON p.documento_cnpj_cpf=e.documento_cnpj_cpf
                    LEFT JOIN tb_minerais m ON p.mineral_id=m.mineral_id
                    LEFT JOIN tb_projeto_municipio pm ON p.processo_anm=pm.processo_anm
                    LEFT JOIN tb_municipios mu ON pm.codigo_ibge=mu.codigo_ibge
                    GROUP BY p.processo_anm,e.nome_empresa,m.mineral_name,
                             p.substancia_anm,p.fase,p.categoria
                """)
            else:
                cursor.execute("""
                    SELECT p.project_id,p.nome_projeto,e.nome_empresa,
                           m.mineral_name,mu.nome_municipio,mu.latitude,mu.longitude
                    FROM tb_projetos p
                    JOIN tb_empresas e ON p.company_id=e.company_id
                    JOIN tb_minerais m ON p.mineral_id=m.mineral_id
                    JOIN tb_municipios mu ON p.municipality_id=mu.municipality_id
                """)
            return cursor.fetchall()
    finally:
        conn.close()

@app.get("/api/projecoes")
def listar_projecoes(scenario: str=Query(default="referencia")):
    conn=get_connection()
    try:
        with conn.cursor() as cursor:
            if schema_version(cursor) in ('v2', 'anm'):
                cursor.execute("""
                    SELECT processo_anm,mineral_id,year,projected_production,unidade_producao,energy_demand_mwh
                    FROM tb_projecoes WHERE scenario=%s ORDER BY year
                """,(scenario,))
            else:
                cursor.execute("""
                    SELECT project_id,mineral_id,year,projected_production_t,energy_demand_mwh
                    FROM tb_projecoes WHERE scenario=%s ORDER BY year
                """,(scenario,))
            return cursor.fetchall()
    finally:
        conn.close()

@app.get("/api/fontes")
def listar_fontes():
    conn=get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tb_fontes")
            return cursor.fetchall()
    finally:
        conn.close()

from auth import router as auth_router
import dashboard
dashboard.connection_factory=get_connection
app.include_router(auth_router)
app.include_router(dashboard.router)

@app.middleware("http")
async def security_headers(request,call_next):
    response=await call_next(request)
    response.headers["Cache-Control"]="no-store"
    response.headers["X-Content-Type-Options"]="nosniff"
    return response

from atlas import router as atlas_router
app.include_router(atlas_router)
from panorama import router as panorama_router
app.include_router(panorama_router)
from precos import router as precos_router
app.include_router(precos_router)

import radar_api
radar_api.connection_factory=get_connection
app.include_router(radar_api.router)
