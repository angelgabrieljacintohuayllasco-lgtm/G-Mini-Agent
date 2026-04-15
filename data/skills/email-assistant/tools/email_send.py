from __future__ import annotations
import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

def _load_payload() -> dict:
    input_path = os.getenv("GMINI_SKILL_INPUT", "").strip()
    if input_path and Path(input_path).exists():
        return json.loads(Path(input_path).read_text(encoding="utf-8"))
    try:
        raw = input()
    except EOFError:
        return {}
    raw = raw.strip()
    return json.loads(raw) if raw else {}

def _write_output(result: dict) -> None:
    output_path = os.getenv("GMINI_SKILL_OUTPUT", "").strip()
    if output_path:
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False))

def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    
    smtp_server = os.getenv("GMINI_EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("GMINI_EMAIL_SMTP_PORT", "465"))
    email_addr = os.getenv("GMINI_EMAIL_ADDRESS")
    password = os.getenv("GMINI_EMAIL_PASSWORD")
    
    if not email_addr or not password:
        _write_output({"error": "Faltan credenciales GMINI_EMAIL_ADDRESS o GMINI_EMAIL_PASSWORD en el entorno."})
        return 1
        
    to_address = str(user_input.get("to", "")).strip()
    subject = str(user_input.get("subject", "Sin asunto")).strip()
    body = str(user_input.get("body", "")).strip()
    
    if not to_address:
        _write_output({"error": "El parámetro 'to' es obligatorio."})
        return 1
        
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = email_addr
        msg["To"] = to_address
        
        # Soporte híbrido para puertos SSL (465) vs STARTTLS (587)
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(email_addr, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_addr, password)
                server.send_message(msg)
                
        _write_output({
            "status": "success",
            "message": f"Correo enviado exitosamente a {to_address}"
        })
        return 0
        
    except smtplib.SMTPAuthenticationError:
        _write_output({"error": "Error de autenticación SMTP. Verifica tu App Password."})
        return 1
    except Exception as e:
        _write_output({"error": f"Error SMTP inesperado: {str(e)}"})
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
