import os
import uuid
import mercadopago
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_parser import extract_pdf_text
from claude_client import interpretar_individual, interpretar_pareja
import storage

app = Flask(__name__)
CORS(app)

MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "APP_USR-7874783142118095-033112-a29e5dfe20e578c90580299ef1e33528-3305667694")
MP_WEBHOOK_URL = os.environ.get("MP_WEBHOOK_URL", "https://astalamo-api.up.railway.app/webhook")
ASTAL_BASE = os.environ.get("ASTAL_BASE", "http://aquamarine-sorbet-64dfea.netlify.app")
PORT = int(os.environ.get("PORT", 3002))

mp = mercadopago.SDK(MP_ACCESS_TOKEN)

PRECIOS = {
    "individual": {"seccion": 300, "pack": 900},
    "pareja": {"seccion": 300, "pack": 1500},
    "grupo": {"seccion": 300, "pack": 1200},
}

SECTIONS_BY_TYPE = {
    "individual": ["carta_natal", "proposito", "amor_y_vinculos", "desafios_y_dones"],
    "pareja": ["energia_union", "tensiones_magnetismo", "karma_compartido", "destino_conjunto", "manual_de_la_pareja"],
    "grupo": ["energia_union", "roles_naturales", "fortalezas_colectivas", "desafios_colectivos"],
}

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "astal-api-v2"})


@app.route("/api/readings/create", methods=["POST"])
def create_reading():
    try:
        if "pdf_file" not in request.files:
            return jsonify({"success": False, "error": "Falta pdf_file"}), 400

        pdf_file = request.files["pdf_file"]
        reading_type = request.form.get("reading_type", "individual")
        consultante = request.form.get("consultante_nombre", "Consultante")
        pdf_file_2 = request.files.get("pdf_file_2")
        nombre1 = request.form.get("nombre1", consultante)
        nombre2 = request.form.get("nombre2", "")

        if not allowed_file(pdf_file.filename):
            return jsonify({"success": False, "error": "Archivo debe ser PDF"}), 400

        # Extract text from PDF
        pdf_bytes = pdf_file.read()
        texto_pdf = extract_pdf_text(pdf_bytes)

        if not texto_pdf or len(texto_pdf) < 100:
            return jsonify({"success": False, "error": "No se pudo extraer texto del PDF"}), 400

        # Interpret with Claude
        if reading_type == "pareja" and pdf_file_2 and allowed_file(pdf_file_2.filename):
            texto_pdf_2 = extract_pdf_text(pdf_file_2.read())
            interpretacion = interpretar_pareja(texto_pdf, texto_pdf_2, nombre1, nombre2, consultante)
        else:
            interpretacion = interpretar_individual(texto_pdf, consultante)

        # Save reading
        nombres = [nombre1]
        if reading_type == "pareja" and nombre2:
            nombres.append(nombre2)

        rid = storage.create_reading(consultante, reading_type, interpretacion, nombres)

        # Build response (only free fields exposed)
        reading = storage.get_reading(rid)
        free_fields = reading.get("free_fields", [])
        free_data = {"id": rid, "consultante": consultante, "type": reading_type, "score": reading["score"]}
        if "free_preview" in free_fields:
            free_data["free_preview"] = interpretacion.get("free_preview", "")

        return jsonify({"success": True, "reading": free_data})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/readings/<rid>")
def get_reading(rid):
    reading = storage.get_reading(rid)
    if not reading:
        return jsonify({"success": False, "error": "Reading no encontrado"}), 404

    # Return full reading but with content: null for locked sections
    free_fields = reading.get("free_fields", [])
    sections = {}
    for k, v in reading["sections"].items():
        if v["unlocked"] or k in free_fields:
            sections[k] = {"content": v["content"], "unlocked": v["unlocked"]}
        else:
            sections[k] = {"content": None, "unlocked": False}

    return jsonify({
        "success": True,
        "reading": {
            "id": reading["id"],
            "consultante": reading["consultante"],
            "type": reading["type"],
            "nombres": reading.get("nombres", []),
            "score": reading["score"],
            "free_preview": reading.get("free_preview", ""),
            "free_fields": free_fields,
            "sections": sections
        }
    })


@app.route("/api/readings/<rid>/unlock-status")
def unlock_status(rid):
    result = storage.get_unlock_status(rid)
    if not result.get("success"):
        return jsonify({"success": False, "error": "Reading no encontrado"}), 404
    return jsonify(result)


@app.route("/api/payments/create-preference", methods=["POST"])
def create_preference():
    try:
        data = request.get_json()
        rid = data.get("reading_id")
        section = data.get("section")  # None = pack completo

        reading = storage.get_reading(rid)
        if not reading:
            return jsonify({"success": False, "error": "Reading no encontrado"}), 404

        reading_type = reading["type"]
        if section is None:
            amount = PRECIOS.get(reading_type, {}).get("pack", 300)
            title = f"AstalAMO {reading_type.title()} — Pack completo"
            description = "Desbloqueo de todas las secciones premium"
        else:
            amount = PRECIOS.get(reading_type, {}).get("seccion", 300)
            title = f"AstalAMO {reading_type.title()} — {section.replace('_', ' ').title()}"
            description = f"Sección: {section}"

        preference_data = {
            "items": [{
                "title": title,
                "description": description,
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(amount)
            }],
            "external_reference": f"{rid}|{section or 'pack'}",
            "back_urls": {
                "success": f"{ASTAL_BASE}/dashboards/view/?reading_id={rid}",
                "failure": f"{ASTAL_BASE}/dashboards/view/?reading_id={rid}",
                "pending": f"{ASTAL_BASE}/dashboards/view/?reading_id={rid}"
            },
            "notification_url": f"{MP_WEBHOOK_URL}/webhook"
        }

        result = mp.preference().create(preference_data)
        preference = result.get("response", {})

        storage.save_payment(preference.get("id"), rid, section or "pack")

        return jsonify({
            "success": True,
            "preference_id": preference.get("id"),
            "init_point": preference.get("init_point")
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payload = request.get_json()
        if payload.get("type") == "payment":
            payment_id = payload.get("data", {}).get("id")
            if payment_id:
                payment_info = mp.payment().get(payment_id)
                pref_id = payment_info.get("response", {}).get("external_reference")
                if pref_id and storage.mark_payment_done(pref_id):
                    rid, section = pref_id.split("|", 1)
                    storage.unlock_section(rid, section)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
