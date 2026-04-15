from __future__ import annotations
import json
import os
import imaplib
import email as email_lib
from email.header import decode_header
from collections import defaultdict
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

    query = user_input.get("query", "")
    folder = user_input.get("folder", "INBOX")
    limit = int(user_input.get("limit", 5))

    if not query:
        _write_output({"error": "Falta el parámetro 'query'"})
        return 1

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, password)
        mail.select(f'"{folder}"')

        # Buscar por asunto o remitente
        imap_query = f'(OR SUBJECT "{query}" FROM "{query}")'
        status, msg_ids = mail.search(None, imap_query)
        if status != "OK":
            _write_output({"error": f"Error buscando: {imap_query}"})
            return 1

        ids = msg_ids[0].split()
        ids = ids[-50:]  # Limitar procesamiento

        # Agrupar por hilo (References / In-Reply-To)
        threads = defaultdict(list)
        for mid in reversed(ids):
            res, msg_data = mail.fetch(mid, "(BODY.PEEK[HEADER])")
            if res != "OK":
                continue
            for part in msg_data:
                if isinstance(part, tuple):
                    hdr = email_lib.message_from_bytes(part[1])
                    subject = decode_mime_words(hdr.get("Subject", ""))
                    from_ = decode_mime_words(hdr.get("From", ""))
                    date_ = hdr.get("Date", "")
                    message_id = hdr.get("Message-ID", "")
                    references = hdr.get("References", "")
                    in_reply_to = hdr.get("In-Reply-To", "")

                    # Clave de hilo: primer Message-ID de la cadena References, o el propio
                    thread_key = ""
                    if references:
                        thread_key = references.strip().split()[0]
                    elif in_reply_to:
                        thread_key = in_reply_to.strip()
                    else:
                        thread_key = message_id

                    threads[thread_key].append({
                        "message_id": message_id,
                        "from": from_,
                        "subject": subject,
                        "date": date_,
                    })

        mail.logout()

        # Tomar los primeros N hilos
        result_threads = []
        for key, msgs in list(threads.items())[:limit]:
            result_threads.append({
                "thread_id": key,
                "message_count": len(msgs),
                "subject": msgs[0].get("subject", ""),
                "latest_date": msgs[0].get("date", ""),
                "messages": msgs[:10],  # Max 10 por hilo
            })

        _write_output({"status": "success", "threads": result_threads, "total_threads": len(threads)})
        return 0

    except Exception as e:
        _write_output({"error": f"Error: {e}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
