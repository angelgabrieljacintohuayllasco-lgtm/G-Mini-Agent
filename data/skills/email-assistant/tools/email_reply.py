from __future__ import annotations
import json
import os
import imaplib
import smtplib
import email as email_lib
from email.header import decode_header
from email.mime.text import MIMEText
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


def decode_mime_words(s: str) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    result = []
    for word, charset in parts:
        if isinstance(word, bytes):
            result.append(word.decode(charset or "utf-8", errors="ignore"))
        else:
            result.append(str(word))
    return "".join(result)


def main() -> int:
    payload = _load_payload()
    user_input = payload.get("input", {})

    imap_server = os.getenv("GMINI_EMAIL_IMAP_SERVER", "imap.gmail.com")
    smtp_server = os.getenv("GMINI_EMAIL_SMTP_SERVER", "smtp.gmail.com")
    email_addr = os.getenv("GMINI_EMAIL_ADDRESS")
    password = os.getenv("GMINI_EMAIL_PASSWORD")

    if not email_addr or not password:
        _write_output({"error": "Faltan credenciales email"})
        return 1

    message_id = user_input.get("message_id", "").strip()
    body_text = user_input.get("body", "")
    reply_all = user_input.get("reply_all", False)

    if not message_id or not body_text:
        _write_output({"error": "Faltan message_id y/o body"})
        return 1

    try:
        # Buscar el email original por Message-ID
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, password)
        mail.select("INBOX")

        status, msg_ids = mail.search(None, f'HEADER Message-ID "{message_id}"')
        if status != "OK" or not msg_ids[0]:
            _write_output({"error": f"No se encontró email con Message-ID: {message_id}"})
            return 1

        mid = msg_ids[0].split()[-1]
        res, msg_data = mail.fetch(mid, "(RFC822)")
        original = None
        for part in msg_data:
            if isinstance(part, tuple):
                original = email_lib.message_from_bytes(part[1])
                break

        if not original:
            _write_output({"error": "No se pudo parsear el email original"})
            return 1

        # Construir la respuesta manteniendo el hilo
        orig_from = original.get("From", "")
        orig_subject = decode_mime_words(original.get("Subject", ""))
        orig_message_id = original.get("Message-ID", "")
        orig_references = original.get("References", "")

        # Determinar destinatarios
        to_addr = orig_from
        cc_addr = ""
        if reply_all:
            # Incluir CC originales excluyendo nuestra dirección
            orig_to = original.get("To", "")
            orig_cc = original.get("Cc", "")
            all_addrs = f"{orig_to}, {orig_cc}".replace(email_addr, "").strip(", ")
            cc_addr = all_addrs

        # Subject con Re:
        subject = orig_subject if orig_subject.lower().startswith("re:") else f"Re: {orig_subject}"

        # Crear email
        msg = MIMEText(body_text, "plain", "utf-8")
        msg["From"] = email_addr
        msg["To"] = to_addr
        if cc_addr:
            msg["Cc"] = cc_addr
        msg["Subject"] = subject
        msg["In-Reply-To"] = orig_message_id
        msg["References"] = f"{orig_references} {orig_message_id}".strip()

        # Enviar
        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            server.login(email_addr, password)
            recipients = [to_addr]
            if cc_addr:
                recipients.extend([a.strip() for a in cc_addr.split(",") if a.strip()])
            server.sendmail(email_addr, recipients, msg.as_string())

        mail.logout()
        _write_output({"status": "success", "replied_to": message_id, "to": to_addr, "subject": subject})
        return 0

    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
