import os, re
import openai
from openai import OpenAI
from typing import Optional
from .mcp import MCPRegistry
import google.generativeai as genai

class CurrencyAgent:
    def __init__(self, mcp: MCPRegistry, vectorstore: Optional[object] = None, llm_model: str = "gemini-1.5-flash"):
        self.mcp = mcp
        self.vectorstore = vectorstore
        self.llm_model = llm_model
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.client = OpenAI()  # Esto ya lee OPENAI_API_KEY de las variables de entorno


    def call_llm(self, prompt: str, temperature: float = 0.0):
        if not self.google_api_key:
            raise RuntimeError('GOOGLE_API_KEY no configurada. Establece la variable de entorno o usa un LLM local.')
        model = genai.GenerativeModel(self.llm_model)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=400
            )
        )
        return response.text
        

    def _detect_moneda(self, question: str):
        candidates = ['dólar','dolar','usd','real','euro','guaraní','guarani','pyg','gs']
        q = question.lower()
        for c in candidates:
            if c in q:
                return c
        tokens = re.findall(r'\b[A-Z]{3,4}\b', question)
        if tokens:
            return tokens[0].lower()
        return None

    def answer(self, question: str):
        moneda = self._detect_moneda(question)
        if moneda and ('hoy' in question.lower() or 'cotizacion' in question.lower() or 'cotización' in question.lower() or 'precio' in question.lower()):
            res_html = None
            try:
                res_html = self.mcp.call('cotizaciones.get_cotizacion_html', moneda=moneda)
            except Exception as e:
                res_html = None
            if res_html:
                return {'type':'tool','tool':'cotizaciones.get_cotizacion_html','answer': f"Fuente HTML — {res_html['moneda']}: compra={res_html['compra']}, venta={res_html['venta']}",'raw': res_html}
            try:
                res_pdf = self.mcp.call('cotizaciones.get_cotizacion_pdf', moneda=moneda)
                if res_pdf:
                    return {'type':'tool','tool':'cotizaciones.get_cotizacion_pdf','answer': f"Fuente PDF — {res_pdf['moneda']}: compra={res_pdf['compra']}, venta={res_pdf['venta']}",'raw': res_pdf}
            except Exception as e:
                return {'type':'error','message': str(e)}
        if self.vectorstore and moneda and('ayer' in question.lower() or 'cotizacion' in question.lower() or 'cotización' in question.lower() or 'precio' in question.lower()):
            self.vectorstore.load('data/vectorstore.pkl')
            docs = self.vectorstore.query(question, k=3)
            if docs:
                context = "\n\n".join([d['doc']['text'] for d in docs])
                prompt = f"Usando el siguiente contexto:\n{context}\n\nPregunta: {question}\nRespuesta concisa en español:"
                try:
                    resp = self.call_llm(prompt)
                    return {'type':'rag','answer': resp, 'sources': docs}
                except Exception as e:
                    return {'type':'error','message': str(e)}
        try:
            resp = self.call_llm(question)
            return {'type':'llm','answer': resp}
        except Exception as e:
            return {'type':'error','message': str(e)}
