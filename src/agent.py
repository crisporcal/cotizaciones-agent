import os
import re
import datetime
import google.generativeai as genai
from typing import Optional, TypedDict, Any
from .rag.vectorstore import SimpleVectorStore
from .tools.cotizaciones_tool import get_cotizacion
from langgraph.graph import StateGraph, END

# Configuración de la API Key de Google
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Meses en español (minúsculas)
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}
# Estado del agente
class AgentState(TypedDict):
    question: str
    moneda: str
    fecha: Optional[str]   # 'YYYY-MM-DD' si se detecta, None si no
    raw_cotizacion: Any
    datos_procesados: Any
    rag_docs: Any
    reporte: str

# --- Detectores ---
def detectar_moneda(texto: str) -> str:
    mapping = {
        "dólar": "USD", "usd": "USD",
        "yen": "JPY", "jpy": "JPY",
        "libra": "GBP", "gbp": "GBP",
        "franco suizo": "CHF", "chf": "CHF",
        "corona sueca": "SEK", "sek": "SEK",
        "corona danesa": "DKK", "dkk": "DKK",
        "corona noruega": "NOK", "nok": "NOK",
        "real": "BRL", "brl": "BRL",
        "peso argentino": "ARS", "ars": "ARS",
        "dólar canadiense": "CAD", "cad": "CAD",
        "rand": "ZAR", "zar": "ZAR",
        "derechos especiales de giro": "XDR", "deg": "XDR", "xdr": "XDR",
        "onza de oro": "XAU", "oro": "XAU", "xau": "XAU",
        "peso chileno": "CLP", "clp": "CLP",
        "euro": "EUR", "eur": "EUR",
        "peso uruguayo": "UYU", "uyu": "UYU",
        "dólar australiano": "AUD", "aud": "AUD",
        "yuan": "CNY", "renminbi": "CNY", "cny": "CNY",
        "dólar de singapur": "SGD", "sgd": "SGD",
        "boliviano": "BOB", "bob": "BOB",
        "sol peruano": "PEN", "pen": "PEN",
        "dólar neozelandés": "NZD", "nzd": "NZD",
        "peso mexicano": "MXN", "mxn": "MXN",
        "peso colombiano": "COP", "cop": "COP",
        "dólar taiwanés": "TWD", "twd": "TWD",
        "dirham": "AED", "emiratos": "AED", "aed": "AED"
    }
    texto = texto.lower()
    for k, v in mapping.items():
        if k in texto:
            return v
    return "USD"  # por defecto

def detectar_fecha(texto: str) -> Optional[str]:
    hoy = datetime.date.today()
    texto = texto.lower().strip()

    # Palabras clave
    if "hoy" in texto:
        return hoy.strftime("%Y-%m-%d")
    elif "ayer" in texto:
        return (hoy - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # Formato DD/MM/YYYY o DD-MM-YYYY
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", texto)
    if match:
        d, m, y = map(int, match.groups())
        try:
            return datetime.date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            return None

    # Formato YYYY-MM-DD
    match_iso = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
    if match_iso:
        y, m, d = map(int, match_iso.groups())
        try:
            return datetime.date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            return None

    # Formato DD-MM (sin año)
    match_short = re.search(r"(\d{1,2})[/-](\d{1,2})", texto)
    if match_short:
        d, m = map(int, match_short.groups())
        try:
            return datetime.date(hoy.year, m, d).strftime("%Y-%m-%d")
        except ValueError:
            return None

    # Formato "11 de agosto" o "11 agosto"
    match_texto = re.search(r"(\d{1,2})\s*(de\s*)?([a-záéíóú]+)", texto)
    if match_texto:
        d = int(match_texto.group(1))
        mes_texto = match_texto.group(3).strip()
        if mes_texto in MESES:
            try:
                return datetime.date(hoy.year, MESES[mes_texto], d).strftime("%Y-%m-%d")
            except ValueError:
                return None

    # Formato "agosto 11"
    match_texto_inv = re.search(r"([a-záéíóú]+)\s*(\d{1,2})", texto)
    if match_texto_inv:
        mes_texto = match_texto_inv.group(1).strip()
        d = int(match_texto_inv.group(2))
        if mes_texto in MESES:
            try:
                return datetime.date(hoy.year, MESES[mes_texto], d).strftime("%Y-%m-%d")
            except ValueError:
                return None

    return None

# --- Nodos ---
def fetch_cotizaciones(state: AgentState) -> AgentState:
    # if state.get("fecha") == datetime.date.today().strftime("%Y-%m-%d"):
    res = get_cotizacion(state["moneda"])
    state["raw_cotizacion"] = res
    return state

def procesar_datos(state: AgentState) -> AgentState:
    raw = state.get("raw_cotizacion", {})
    inner = raw.get("result", {})
    if isinstance(inner, dict) and "result" in inner:
        datos = inner["result"]
        state["datos_procesados"] = {
            "moneda": datos.get("moneda", state.get("moneda")),
            "compra": datos.get("compra"),
            "venta": datos.get("venta"),
            "source": inner.get("source", raw.get("source", "desconocida"))
        }
    else:
        state["datos_procesados"] = {}
    return state

def rag_lookup(state: AgentState, vectorstore: Optional[SimpleVectorStore] = None) -> AgentState:
    if not vectorstore:
        return state
    moneda = state["moneda"]
    if state.get("fecha"):
        question = f"Cotización de {moneda} el {state['fecha']} en guaraníes."
    else:
        question = f"Cotizaciones históricas de {moneda} en guaraníes."
    docs = vectorstore.query(question, k=5)
    state["rag_docs"] = docs
    return state

def analizar_con_llm(state: AgentState) -> AgentState:
    hoy = datetime.date.today()
    hoy_str = hoy.strftime("%Y-%m-%d")
    fecha_pedida_str = state.get("fecha")
    rag_docs = state.get("rag_docs", [])
    datos = state.get("datos_procesados", {})

    def extraer_fecha(doc_text):
        match = re.search(r"\d{4}-\d{2}-\d{2}", doc_text)
        if match:
            try:
                return datetime.datetime.strptime(match.group(), "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    # 🟢 Caso: fecha pedida = HOY → devolver datos procesados sin LLM
    if fecha_pedida_str == hoy_str:
        state["reporte"] = (
            f"Cotización actual de {datos.get('moneda')} "
            f"(fuente {datos.get('source')}): "
            f"Compra {datos.get('compra')} | Venta {datos.get('venta')}"
        )
        return state

    # 🟢 Caso: fecha pedida y RAG disponible → devolver el más cercano
    if fecha_pedida_str and rag_docs:
        fecha_pedida = datetime.datetime.strptime(fecha_pedida_str, "%Y-%m-%d").date()
        mejor_doc = None
        mejor_diff = None

        for d in rag_docs:
            f_doc = extraer_fecha(d["doc"]["text"])
            if f_doc:
                diff = abs((f_doc - fecha_pedida).days)
                if mejor_diff is None or diff < mejor_diff:
                    mejor_doc = d
                    mejor_diff = diff

        if mejor_doc:
            f_encontrada = extraer_fecha(mejor_doc["doc"]["text"])
            if f_encontrada == fecha_pedida:
                state["reporte"] = f"Datos históricos para {state['moneda']} el {fecha_pedida_str}:\n{mejor_doc['doc']['text']}"
            else:
                state["reporte"] = f"No hay datos exactos para {fecha_pedida_str}, mostrando el más cercano ({f_encontrada}):\n{mejor_doc['doc']['text']}"
            return state

    # 🟢 Caso: sin fecha → devolver solo hoy y ayer si existen
    if not fecha_pedida_str and rag_docs:
        ayer = hoy - datetime.timedelta(days=1)
        docs_filtrados = []
        for d in rag_docs:
            f_doc = extraer_fecha(d["doc"]["text"])
            if f_doc in [hoy, ayer]:
                docs_filtrados.append(d["doc"]["text"])
        if docs_filtrados:
            state["reporte"] = f"Cotizaciones recientes de {state['moneda']}:\n" + "\n\n".join(docs_filtrados)
            return state

    # 🟢 Todo lo demás → usar LLM
    context = "\n\n".join([d['doc']['text'] for d in rag_docs])
    prompt = f"""Eres un analista financiero.
    Analiza la cotización de {datos.get("moneda")}.
    Compra: {datos.get("compra")} | Venta: {datos.get("venta")}
    Fuente: {datos.get("source")}
    Contexto histórico de datos que se tienen de fechas pasadas:
    {context}
    Y {datos} son los datos actuales a dia de hoy obtenidos por scraping de la pagina
    de Cambios Chaco
    Responde en español, breve y con fuentes."""

    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(prompt)
    state['reporte'] = resp.text
    return state

# --- Constructor ---
def build_currency_agent_graph(question: str, vectorstore: Optional[SimpleVectorStore] = None):
    moneda = detectar_moneda(question)
    fecha = detectar_fecha(question)

    workflow = StateGraph(AgentState)
    workflow.add_node("fetch", fetch_cotizaciones)
    workflow.add_node("process", procesar_datos)
    workflow.add_node("rag", lambda s: rag_lookup(s, vectorstore))
    workflow.add_node("analyze", analizar_con_llm)

    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "process")
    workflow.add_edge("process", "rag")
    workflow.add_edge("rag", "analyze")
    workflow.add_edge("analyze", END)

    app = workflow.compile()
    initial_state: AgentState = {
        "question": question,
        "moneda": moneda,
        "fecha": fecha
    }
    return app, initial_state
