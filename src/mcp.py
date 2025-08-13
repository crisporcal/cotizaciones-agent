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

def analyze_with_llm(moneda: str, compra: float, venta: float, source: str, contexto: str) -> str:
    prompt = f"""Eres un analista financiero.
    Analiza la cotización de {moneda}.
    Compra: {compra} | Venta: {venta}
    Fuente: {source}
    Contexto histórico:
    {contexto}
    Responde en español, breve y con fuentes.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(prompt)
    return resp.text
