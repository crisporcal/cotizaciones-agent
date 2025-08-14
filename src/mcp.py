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
    prompt = f"""Eres un analista financiero. La pregunta que te realizan es: {question}
    Si la pregunta no tiene relevancia con la cotización de monedas ni con el análisis financiero, responde de forma amable, disculpándote y diciendo que estás disponible para ayudar con cualquier otra pregunta relacionada con las divisas.
    Si la pregunta está relacionada con la cotización de monedas, analiza la cotización de {moneda}.
    Compra: {compra} | Venta: {venta}
    Fuente: {source}, donde la fuente {source} es la obtenida por scraping de la página Cambios Chaco.
    Contexto histórico:
    {contexto} es la base de datos del Banco Central del Paraguay que se tiene almacenado.
    Responde en español, de manera breve, y solo proporciona información sobre la cotización si es relevante para la pregunta. Si la pregunta no está relacionada, no hagas mención de las cotizaciones.
    """
    # Llamada a Gemini para generar el análisis
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(prompt)
    return resp.text
