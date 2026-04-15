from __future__ import annotations
import json
import os
import imaplib
import email
from email.header import decode_header
from pathlib import Path

def _load_payload() -> dict:
    """Lee los datos de entrada pasados por el SkillRuntime."""
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
    """Devuelve el resultado estructurado al SkillRuntime."""
    output_path = os.getenv("GMINI_SKILL_OUTPUT", "").strip()
    if output_path:
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False))

def decode_mime_words(s: str) -> str:
    """Decodifica cadenas MIME complejas (ej. Asuntos con tildes)."""
    if not s:
        return ""
    decoded_words = decode_header(s)
    result = []
    for word, charset in decoded_words:
        if isinstance(word, bytes):
            result.append(word.decode(charset or 'utf-8', errors='ignore'))
        else:
            result.append(str(word))
    return "".join(result)

def get_body(msg) -> str:
    """Extrae el cuerpo en texto plano del mensaje."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        except Exception:
            pass
    return ""

def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})
    
    imap_server = os.getenv("GMINI_EMAIL_IMAP_SERVER", "imap.gmail.com")
    email_addr = os.getenv("GMINI_EMAIL_ADDRESS")
    password = os.getenv("GMINI_EMAIL_PASSWORD")
    
    if not email_addr or not password:
        _write_output({"error": "Faltan credenciales GMINI_EMAIL_ADDRESS o GMINI_EMAIL_PASSWORD en el entorno."})
        return 1
        
    limit = int(user_input.get("limit", 10))
    folder = str(user_input.get("folder", "inbox"))
    search_query = str(user_input.get("query", "ALL"))
    
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, password)
        mail.select(f'"{folder}"')
        
        status, messages = mail.search(None, search_query)
        if status != "OK":
            _write_output({"error": f"Fallo en la búsqueda de correos con query: {search_query}"})
            return 1
            
        mail_ids = messages[0].split()
        mail_ids = mail_ids[-limit:] # Retener solo los últimos N resultados
        
        emails_list = []
        for i in reversed(mail_ids):
            res, msg_data = mail.fetch(i, '(RFC822)')
            if res != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_mime_words(msg["Subject"])
                    from_ = decode_mime_words(msg.get("From"))
                    date_ = msg.get("Date")
                    body = get_body(msg)
                    
                    emails_list.append({
                        "id": i.decode('utf-8'),
                        "from": from_,
                        "subject": subject,
                        "date": date_,
                        "preview": body[:500] + "..." if len(body) > 500 else body
                    })
        
        mail.logout()
        _write_output({
            "status": "success",
            "count": len(emails_list),
            "emails": emails_list
        })
        return 0
        
    except imaplib.IMAP4.error as e:
        _write_output({"error": f"Error de Autenticación/IMAP: {str(e)}"})
        return 1
    except Exception as e:
        _write_output({"error": f"Error inesperado procesando correos: {str(e)}"})
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
