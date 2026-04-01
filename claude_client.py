import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

SYSTEM_INDIVIDUAL = """Sos AstralReader, un intérprete de cartas natales astrológicas.
Recibís el texto extraído de un PDF de carta natal generado por losarcanos.com.
Tu trabajo es interpretar ese contenido en lenguaje claro, profundo y evocador.
Siempre hablás en segunda persona dirigiéndote al consultante.
Respondé SOLO con JSON válido, sin backticks, sin markdown."""

USER_INDIVIDUAL = """
Carta natal del consultante:
{texto_pdf}

Nombre del consultante: {consultante}

Generá la interpretación con este formato JSON exacto (cada campo es un string con 3-4 párrafos):
{{
 "score_general": <número 1-100>,
 "free_preview": "<2 oraciones evocadoras y vagas que generen curiosidad, sin revelar nada concreto>",
 "carta_natal": "<interpretación profunda de los aspectos principales: sol, luna, ascendente, planetas dominantes>",
 "proposito": "<misión de vida, nodos lunares, karma>",
 "amor_y_vinculos": "<venus, marte, casa 7, patrones relacionales>",
 "desafios_y_dones": "<saturno, quirón, aspectos tensos y talentos ocultos>"
}}"""

SYSTEM_PAREJA = """Sos AstralReader, un intérprete de cartas natales astrológicas.
Recibís dos textos de cartas natales y debés interpretar la compatibilidad entre ambas personas.
Tu trabajo es interpretar en lenguaje claro, profundo y evocador.
Respondé SOLO con JSON válido, sin backticks, sin markdown."""

USER_PAREJA = """
Carta natal de {nombre1}:
{texto_pdf_1}

Carta natal de {nombre2}:
{texto_pdf_2}

El consultante es {consultante}. Interpretá desde su perspectiva, respondiendo a la pregunta: "¿Cómo es mi relación con [nombre2]?"

Generá el análisis con este formato JSON exacto (cada campo es un string con 3-4 párrafos):
{{
 "score_compatibilidad": <número 1-100>,
 "free_preview": "<score visible + 1 frase intrigante que no revela nada>",
 "energia_union": "<dinámica general entre las dos cartas>",
 "tensiones_magnetismo": "<aspectos de fricción y atracción, Marte/Venus cruzados>",
 "karma_compartido": "<nodos lunares, plutón, conexiones kármicas>",
 "destino_conjunto": "<hacia dónde los llevan los astros juntos>",
 "manual_de_la_pareja": "<consejos concretos para cultivar el vínculo>"
}}"""


def interpretar_individual(texto_pdf: str, consultante: str) -> dict:
    prompt = USER_INDIVIDUAL.format(texto_pdf=texto_pdf, consultante=consultante)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_INDIVIDUAL},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def interpretar_pareja(texto1: str, texto2: str, nombre1: str, nombre2: str, consultante: str) -> dict:
    prompt = USER_PAREJA.format(
        texto_pdf_1=texto1, texto_pdf_2=texto2,
        nombre1=nombre1, nombre2=nombre2, consultante=consultante
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PAREJA},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
