from typing import Callable, Optional
from pydantic import BaseModel, ValidationError
import os
import google.generativeai as genai

# Configuración de Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class MCPRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, func: Callable, description: str = "", input_model: Optional[BaseModel] = None):
        if name in self.tools:
            raise ValueError(f"Tool {name} already registered")
        self.tools[name] = {"func": func, "description": description, "input_model": input_model}

    def call(self, name: str, **kwargs):
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not registered")
        entry = self.tools[name]
        model = entry.get("input_model")
        if model:
            try:
                validated = model(**kwargs)
                return entry["func"](**validated.dict())
            except ValidationError as e:
                raise e
        else:
            return entry["func"](**kwargs)


# Modelo de entrada para la herramienta LLM
class LLMAnalysisInput(BaseModel):
    moneda: str
    compra: float
    venta: float
    source: str
    contexto: str
    question: str

def analyze_with_llm(moneda: str, compra: float, venta: float, source: str, contexto: str, question: str) -> str:
    prompt = f"""Eres un analista financiero. y la pregunta que te realizan es {question}
    Si te hacen una pregunta que no tiene relevancia con la cotizacion de monedas, ignora la pregunta y responde muy amablemente
    diciendole que estas disponible si necesita ayuda con otra pregunta.
    en caso contrario, analiza la cotización de {moneda}.
    Compra: {compra} | Venta: {venta}
    Fuente: {source}, donde la Fuente {source} es la obtenida por scraping actualmente de la pagina cambios Chaco
    Contexto histórico:
    {contexto} es la base de datos del banco central del paraguay que se tiene almacenado.
    Responde en español, breve y con fuentes.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(prompt)
    return resp.text
