from fastapi import FastAPI
from pydantic import BaseModel
from .mcp import MCPRegistry
from .tools.cotizaciones_tool import get_cotizacion, find_cotizacion_html, find_cotizacion_pdf
from .rag.vectorstore import SimpleVectorStore
from .agent import build_currency_agent_graph
import os

app = FastAPI(title='AGENTE DE COTIZACIONES DE MONEDAS (MCP demo)')

mcp = MCPRegistry()
mcp.register('cotizaciones.get_cotizacion_html', find_cotizacion_html, description='Obtiene cotizacion desde una página HTML')
mcp.register('cotizaciones.get_cotizacion_pdf', find_cotizacion_pdf, description='Obtiene cotizacion desde PDF')

# Cargar vectorstore si existe
vs = SimpleVectorStore()
if os.path.exists('data/vectorstore.pkl'):
    try:
        vs.load('data/vectorstore.pkl')
    except Exception:
        pass

# agent = CurrencyAgent(mcp, vectorstore=vectorstore)

class Query(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Query):
    graph, init_state = build_currency_agent_graph(question=q.question, vectorstore=vs)
    out = graph.invoke(init_state)
    return {"reporte": out.get("reporte", "")}

@app.get('/health')
async def health():
    return {'status': 'ok'}
