from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MINERA Goiás API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "db_minera_goias"),
        cursorclass=pymysql.cursors.DictCursor
    )

@app.get("/api/projetos")
def listar_projetos():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.processo_anm, e.nome_empresa, e.documento_cnpj_cpf,
                       m.mineral_name, p.substancia_anm, p.fase, p.categoria,
                       GROUP_CONCAT(mu.nome_municipio SEPARATOR '; ') AS municipios
                FROM tb_projetos p
                JOIN tb_empresas e ON p.documento_cnpj_cpf = e.documento_cnpj_cpf
                LEFT JOIN tb_minerais m ON p.mineral_id = m.mineral_id
                LEFT JOIN tb_projeto_municipio pm ON p.processo_anm = pm.processo_anm
                LEFT JOIN tb_municipios mu ON pm.codigo_ibge = mu.codigo_ibge
                GROUP BY p.processo_anm
            """)
            return cursor.fetchall()
    finally:
        conn.close()

@app.get("/api/projecoes")
def listar_projecoes(scenario: str = Query(default="referencia")):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT processo_anm, mineral_id, year, projected_production, unidade_producao, energy_demand_mwh
                FROM tb_projecoes
                WHERE scenario = %s
                ORDER BY year
            """, (scenario,))
            return cursor.fetchall()
    finally:
        conn.close()

@app.get("/api/fontes")
def listar_fontes():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tb_fontes")
            return cursor.fetchall()
    finally:
        conn.close()
