#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para precargar cotizaciones históricas reales en el vectorstore.
Fuente: Banco Central del Paraguay (fechas agosto 2025)
"""

from src.rag.vectorstore import SimpleVectorStore

# Datos reales estructurados (cada planilla -> fecha -> lista de monedas)
cotizaciones_reales = [
    {
        "fecha": "2025-08-11",
        "monedas": [
            ("USD", 7263.48),
            ("JPY", 49.07),
            ("GBP", 9738.15),
            ("CHF", 8940.77),
            ("SEK", 752.79),
            ("DKK", 1129.10),
            ("NOK", 709.16),
            ("BRL", 1332.72),
            ("ARS", 5.44),
            ("CAD", 5267.97),
            ("ZAR", 408.80),
            ("XDR", 9923.37),
            ("XAU", 24308906.42),
            ("CLP", 7.49),
            ("EUR", 8425.64),
            ("UYU", 181.77),
            ("AUD", 4726.35),
            ("CNY", 1010.53),
            ("SGD", 5643.29),
            ("BOB", 1059.34),
            ("PEN", 2057.64),
            ("NZD", 4307.97),
            ("MXN", 389.06),
            ("COP", 1.79),
            ("TWD", 242.89),
            ("AED", 1977.53),
        ],
    },
    {
        "fecha": "2025-08-08",
        "monedas": [
            ("USD", 7271.55),
            ("JPY", 49.24),
            ("GBP", 9783.14),
            ("CHF", 9012.83),
            ("SEK", 760.19),
            ("DKK", 1136.75),
            ("NOK", 708.00),
            ("BRL", 1341.44),
            ("ARS", 5.49),
            ("CAD", 5289.17),
            ("ZAR", 410.66),
            ("XDR", 9930.76),
            ("XAU", 24681240.44),
            ("CLP", 7.55),
            ("EUR", 8483.72),
            ("UYU", 182.34),
            ("AUD", 4749.05),
            ("CNY", 1012.16),
            ("SGD", 5661.00),
            ("BOB", 1060.77),
            ("PEN", 2062.85),
            ("NZD", 4332.39),
            ("MXN", 392.45),
            ("COP", 1.80),
            ("TWD", 243.72),
            ("AED", 1980.00),
        ],
    },
    {
        "fecha": "2025-08-07",
        "monedas": [
            ("USD", 7299.41),
            ("JPY", 49.53),
            ("GBP", 9794.35),
            ("CHF", 9038.40),
            ("SEK", 760.68),
            ("DKK", 1138.03),
            ("NOK", 712.30),
            ("BRL", 1334.27),
            ("ARS", 5.49),
            ("CAD", 5305.96),
            ("ZAR", 410.45),
            ("XDR", 9979.75),
            ("XAU", 24729744.13),
            ("CLP", 7.52),
            ("EUR", 8492.86),
            ("UYU", 182.58),
            ("AUD", 4743.16),
            ("CNY", 1016.52),
            ("SGD", 5680.03),
            ("BOB", 1064.05),
            ("PEN", 2061.40),
            ("NZD", 4335.85),
            ("MXN", 390.47),
            ("COP", 1.80),
            ("TWD", 245.19),
            ("AED", 1987.37),
        ],
    },
]

def main():
    store = SimpleVectorStore()
    docs = []
    for planilla in cotizaciones_reales:
        fecha = planilla["fecha"]
        for moneda, valor in planilla["monedas"]:
            doc_id = f"{fecha}_{moneda}"
            texto = f"El {fecha} la cotización de {moneda} fue {valor} guaraníes por unidad, según el Banco Central del Paraguay."
            docs.append({"id": doc_id, "text": texto, "meta": {"fecha": fecha, "moneda": moneda, "valor_guaranies": valor}})
    store.add_documents(docs)
    store.save("data/vectorstore.pkl")
    print(f"Vectorstore pre-cargado con {len(docs)} documentos reales (data/vectorstore.pkl)")

if __name__ == "__main__":
    main()
