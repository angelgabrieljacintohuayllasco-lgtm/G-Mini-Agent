from __future__ import annotations
import json
import os
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime, timedelta
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
    email_addr = os.getenv("GMINI_EMAIL_ADDRESS")
    password = os.getenv("GMINI_EMAIL_PASSWORD")

    if not email_addr or not password:
        _write_output({"error": "Faltan credenciales email"})
        return 1

    days_ago = int(user_input.get("days_ago", 3))
    limit = int(user_input.get("limit", 10))

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, password)

        # Obtener emails enviados recientemente
        sent_folders = ['"[Gmail]/Sent Mail"', '"Sent"', '"INBOX.Sent"', '"Sent Items"']
        sent_folder = None
        for sf in sent_folders:
            try:
                status, _ = mail.select(sf)
                if status == "OK":
                    sent_folder = sf
                    break
            except Exception:
                continue

        if not sent_folder:
            _write_output({"error": "No se encontró carpeta de enviados"})
            return 1

        since_date = (datetime.now() - timedelta(days=days_ago)).strftime("%d-%b-%Y")
        status, msg_ids = mail.search(None, f'SINCE {since_date}')
        if status != "OK":
            _write_output({"error": "Error buscando emails enviados"})
            return 1

        sent_ids = msg_ids[0].split()
        sent_ids = sent_ids[-50:]  # Limitar

        # Recopilar Message-IDs enviados y sus destinatarios
        sent_messages = []
        for mid in reversed(sent_ids):
            res, msg_data = mail.fetch(mid, "(BODY.PEEK[HEADER])")
            if res != "OK":
                continue
            for part in msg_data:
                if isinstance(part, tuple):
                    hdr = email_lib.message_from_bytes(part[1])
                    message_id = hdr.get("Message-ID", "")
                    to = decode_mime_words(hdr.get("To", ""))
                    subject = decode_mime_words(hdr.get("Subject", ""))
                    date_ = hdr.get("Date", "")
                    sent_messages.append({
                        "message_id": message_id,
                        "to": to,
                        "subject": subject,
                        "date": date_,
                    })

        # Buscar respuestas en INBOX
        mail.select("INBOX")
        replied_ids = set()
        for sent in sent_messages:
            mid = sent["message_id"]
            if not mid:
                continue
            status, found = mail.search(None, f'HEADER In-Reply-To "{mid}"')
            if status == "OK" and found[0]:
                replied_ids.add(mid)

        mail.logout()

        # Filtrar los que NO tienen respuesta
        no_reply = [s for s in sent_messages if s["message_id"] not in replied_ids]
        no_reply = no_reply[:limit]

        _write_output({
            "status": "success",
            "awaiting_reply": no_reply,
            "count": len(no_reply),
            "total_sent_checked": len(sent_messages),
        })
        return 0

    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
