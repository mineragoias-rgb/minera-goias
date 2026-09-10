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

@app.get("/api/projetos")
def listar_projetos():
    """Consumido pelo Eduardo (mapa): projetos + mineral + coordenadas."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.project_id, p.nome_projeto, e.nome_empresa,
                       m.mineral_name, mu.nome_municipio, mu.latitude, mu.longitude
                FROM tb_projetos p
                JOIN tb_empresas e ON p.company_id = e.company_id
                JOIN tb_minerais m ON p.mineral_id = m.mineral_id
                JOIN tb_municipios mu ON p.municipality_id = mu.municipality_id
            """)
            return cursor.fetchall()
    finally:
        conn.close()

@app.get("/api/projecoes")
def listar_projecoes(scenario: str = Query(default="referencia")):
    """Consumido pelo simulador do Henrique: filtra por cenário."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT project_id, mineral_id, year, projected_production_t, energy_demand_mwh
                FROM tb_projecoes
                WHERE scenario = %s
                ORDER BY year
            """, (scenario,))
            return cursor.fetchall()
    finally:
        conn.close()

@app.get("/api/fontes")
def listar_fontes():
    """Auditoria: de onde vieram os dados exibidos na tela."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tb_fontes")
            return cursor.fetchall()
    finally:
        conn.close()

from auth import router as auth_router
import dashboard
dashboard.connection_factory = get_connection
app.include_router(auth_router)
app.include_router(dashboard.router)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
