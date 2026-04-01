import json
import os
import uuid
from datetime import datetime

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
READINGS_FILE = os.path.join(STORAGE_DIR, "readings.json")
PAYMENTS_FILE = os.path.join(STORAGE_DIR, "payments.json")

def _load(fname):
    if not os.path.exists(fname):
        return {}
    with open(fname) as f:
        return json.load(f)

def _save(fname, data):
    with open(fname, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_reading(consultante: str, reading_type: str, interpretacion: dict, nombres: list = None) -> str:
    rid = uuid.uuid4().hex[:8]
    reading = {
        "id": rid,
        "consultante": consultante,
        "type": reading_type,
        "created_at": datetime.utcnow().isoformat(),
        "nombres": nombres or [],
        "free_preview": interpretacion.get("free_preview", ""),
        "score": interpretacion.get("score_general") or interpretacion.get("score_compatibilidad") or 0,
        "sections": {}
    }

    # Define which sections are premium (locked by default)
    if reading_type == "individual":
        premium_sections = ["carta_natal", "proposito", "amor_y_vinculos", "desafios_y_dones"]
        reading["free_fields"] = ["score_general", "free_preview"]
    elif reading_type == "pareja":
        premium_sections = ["energia_union", "tensiones_magnetismo", "karma_compartido", "destino_conjunto", "manual_de_la_pareja"]
        reading["free_fields"] = ["score_compatibilidad", "free_preview"]
    else:
        premium_sections = []
        reading["free_fields"] = []

    for section in premium_sections:
        content = interpretacion.get(section, "")
        reading["sections"][section] = {
            "content": content,
            "unlocked": False
        }

    readings = _load(READINGS_FILE)
    readings[rid] = reading
    _save(READINGS_FILE, readings)
    return rid

def get_reading(rid: str) -> dict:
    readings = _load(READINGS_FILE)
    return readings.get(rid)

def unlock_section(rid: str, section: str):
    readings = _load(READINGS_FILE)
    if rid in readings and section in readings[rid]["sections"]:
        readings[rid]["sections"][section]["unlocked"] = True
        _save(READINGS_FILE, readings)
        return True
    return False

def get_unlock_status(rid: str) -> dict:
    reading = get_reading(rid)
    if not reading:
        return {"success": False}
    sections = {}
    for k, v in reading["sections"].items():
        sections[k] = {"unlocked": v["unlocked"]}
    return {"success": True, "sections": sections}

def save_payment(preference_id: str, rid: str, section: str):
    payments = _load(PAYMENTS_FILE)
    payments[preference_id] = {"rid": rid, "section": section, "status": "pending"}
    _save(PAYMENTS_FILE, payments)

def mark_payment_done(preference_id: str):
    payments = _load(PAYMENTS_FILE)
    if preference_id in payments:
        payments[preference_id]["status"] = "done"
        _save(PAYMENTS_FILE, payments)
        return payments[preference_id]
    return None

def get_payment(preference_id: str):
    payments = _load(PAYMENTS_FILE)
    return payments.get(preference_id)
