import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import base64
import pandas as pd
import datetime as dt
from typing import List, Dict, Any, Optional

URL_BASE = "https://www.cambioschaco.com.py/api/branch_office/1/exchange"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cotizaciones-agent/1.0)"}
URL_PDF = URL_BASE + "/pdf"

def _normalize_moneda(moneda: str) -> str:
    m = moneda.strip().lower()
    mapping = {
        'USD': ['dólar', 'dolar', 'usd', 'dollar', 'dólar usa', 'dolar usa'],
        'JPY': ['yen', 'jpy', 'yen japonés', 'yen japones'],
        'GBP': ['libra', 'gbp', 'libra esterlina'],
        'CHF': ['franco suizo', 'chf'],
        'SEK': ['corona sueca', 'sek'],
        'DKK': ['corona danesa', 'dkk'],
        'NOK': ['corona noruega', 'nok'],
        'BRL': ['real', 'brl', 'real brasileño'],
        'ARS': ['peso argentino', 'ars'],
        'CAD': ['dólar canadiense', 'cad'],
        'ZAR': ['rand', 'zar'],
        'XDR': ['derechos especiales de giro', 'deg', 'xdr'],
        'XAU': ['onza de oro', 'oro', 'xau'],
        'CLP': ['peso chileno', 'clp'],
        'EUR': ['euro', 'eur'],
        'UYU': ['peso uruguayo', 'uyu'],
        'AUD': ['dólar australiano', 'aud'],
        'CNY': ['yuan', 'renminbi', 'cny', 'yuan chino'],
        'SGD': ['dólar de singapur', 'sgd'],
        'BOB': ['boliviano', 'bob'],
        'PEN': ['sol peruano', 'pen'],
        'NZD': ['dólar neozelandés', 'nzd'],
        'MXN': ['peso mexicano', 'mxn'],
        'COP': ['peso colombiano', 'cop'],
        'TWD': ['dólar taiwanés', 'twd'],
        'AED': ['dirham', 'emiratos', 'aed'],
        'PYG': ['guaraní', 'guarani', 'gs', 'pyg']
    }
    
    for iso, aliases in mapping.items():
        if m in aliases or any(alias in m for alias in aliases):
            return iso
    return m.upper()  # Si no se reconoce, devolver en mayúsculas por si ya es ISO

def _safe_get_number(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def get_cotizaciones_chaco() -> List[Dict[str, Any]]:
    """
    Llama a la API y devuelve una lista de dicts normalizados:
    [{'moneda': 'USD', 'compra': 7150.0, 'venta': 7270.0, 'meta': {...}}, ...]
    Maneja estructuras que vienen como {"items": [...]} o como lista directa.
    """
    try:
        resp = requests.get(URL_BASE, timeout=8, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        # en caso de error devolvemos lista vacía (el caller decide qué hacer)
        print(f"[get_cotizaciones_chaco] error al obtener datos: {e}")
        return []

    rows: List[Dict[str, Any]] = []

    # Normalizar a una lista de elementos para iterar
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        items = data["items"]
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Podría ser dict { "USD": {...}, "EUR": {...} }
        # en ese caso transformamos en lista de dicts con el ISO como clave
        items = []
        for k, v in data.items():
            if isinstance(v, dict):
                v_copy = dict(v)
                v_copy.setdefault("isoCode", k)
                items.append(v_copy)
    else:
        items = []

    for it in items:
        if not isinstance(it, dict):
            continue

        # detectar ISO en varias posibles claves
        iso = (
            it.get("isoCode") or it.get("iso") or it.get("currencyCode") or it.get("code")
        )
        if not iso:
            # intentar si la entrada ya viene indexada por iso en clave "0": {...}
            # o saltarla
            continue
        iso = str(iso).upper()

        # posibles nombres de campo para compra/venta
        compra = (
            it.get("purchasePrice")
            or it.get("purchase_price")
            or it.get("purchase")
            or it.get("buy")
        )
        venta = (
            it.get("salePrice")
            or it.get("sale_price")
            or it.get("sale")
            or it.get("sell")
        )

        compra = _safe_get_number(compra)
        venta = _safe_get_number(venta)

        # Si la API no distingue compra/venta y solo entrega un precio, asignar ambos
        if compra is None and venta is not None:
            compra = venta
        if venta is None and compra is not None:
            venta = compra

        # Si no hay valores numéricos válidos, saltar
        if compra is None and venta is None:
            continue

        rows.append({
            "moneda": iso,
            "compra": compra,
            "venta": venta,
            "meta": {
                "fecha": dt.datetime.now().strftime("%Y-%m-%d"),
                "fuente": "Cambios Chaco",
                "raw": {k: it.get(k) for k in ("purchasePrice", "salePrice", "purchaseArbitrage") if k in it}
            }
        })

    return rows


def get_cotizacion_html(moneda_iso: str) -> Dict[str, Any]:
    """
    Busca una moneda específica (ISO) en la API y devuelve un dict con clave 'result'
    en formato compatible con el agent.py:
    {
      "result": {"moneda": "JPY", "compra": 49.07, "venta": 49.24},
      "source": "Cambios Chaco",
      "date": "2025-08-11"
    }
    Si no encuentra devuelve {"result": None, "source": "...", "date": ...}
    """
    moneda_iso = (moneda_iso or "").strip().upper()
    cotizaciones = get_cotizaciones_chaco()
    for c in cotizaciones:
        if c.get("moneda") == moneda_iso:
            return {
                "result": {
                    "moneda": c["moneda"],
                    "compra": c["compra"],
                    "venta": c["venta"]
                },
                "source": c.get("meta", {}).get("fuente", "Cambios Chaco"),
                "date": c.get("meta", {}).get("fecha")
            }

    # Si no encontramos en la API, devolvemos formato vacío (el agente puede usar RAG entonces)
    return {"result": None, "source": "Cambios Chaco - no encontrado", "date": dt.datetime.now().strftime("%Y-%m-%d")}

def find_cotizacion_html(moneda: str):
    key = _normalize_moneda(moneda)
    r = get_cotizacion_html(moneda)
    if r and r.get("result"):
        return r
    return None

def get_cotizaciones_pdf_bytes():
    """Descarga el PDF (bytes) y lo retorna. Puede ser usado por pdfplumber."""
    resp = requests.get(URL_PDF, timeout=10)
    resp.raise_for_status()
    return resp.content

def parse_pdf_bytes_for_table(pdf_bytes):
    """Usa pdfplumber para extraer tablas del PDF y devolver lista de dicts similar a HTML."""
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    moneda = (row[0] or '').strip()
                    compra_raw = (row[1] or '').strip()
                    venta_raw = (row[2] or '').strip()
                    def to_float(x):
                        try:
                            return float(x.replace('.','').replace(',','.'))
                        except:
                            try:
                                return float(x.replace(',','.'))
                            except:
                                return None
                    compra = to_float(compra_raw)
                    venta = to_float(venta_raw)
                    rows.append({'moneda': moneda, 'compra': compra, 'venta': venta})
    return rows

def find_cotizacion_pdf(moneda: str):
    key = _normalize_moneda(moneda)
    pdf_bytes = get_cotizaciones_pdf_bytes()
    rows = parse_pdf_bytes_for_table(pdf_bytes)
    for r in rows:
        if key in r['moneda'].lower() or r['moneda'].lower() in key:
            return r
    return None

# Helper combined: primero HTML, luego PDF como fallback
def get_cotizacion(moneda: str):
    res = find_cotizacion_html(moneda)
    if res:
        return {'source':'html','result':res}
    try:
        res_pdf = find_cotizacion_pdf(moneda)
        if res_pdf:
            return {'source':'pdf','result':res_pdf}
    except Exception as e:
        pass
    return {'source': None, 'result': None}
