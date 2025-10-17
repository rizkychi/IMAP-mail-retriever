#!/usr/bin/env python3
import os, csv, json, imaplib, email, re
from datetime import timezone, datetime, timedelta
from email import policy
from email.header import decode_header, make_header
from flask import Flask, request, jsonify, send_from_directory, abort
from dotenv import load_dotenv
from pathlib import Path

# Python 3.9+: zoneinfo built-in
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # fallback nanti pakai UTC

load_dotenv()

IMAP_HOST     = os.getenv("IMAP_HOST")
IMAP_PORT     = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER     = os.getenv("IMAP_USER")
IMAP_PASS     = os.getenv("IMAP_PASS")
IMAP_MAILBOX  = os.getenv("IMAP_MAILBOX", "INBOX")
IMAP_TIMEOUT  = int(os.getenv("IMAP_TIMEOUT", "30"))
API_TOKEN     = os.getenv("API_TOKEN", "")

EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Asia/Jakarta")

app = Flask(__name__)

# -------------------- utils --------------------

def require_token(req):
    if not API_TOKEN:
        return True
    token = req.headers.get("X-API-Key") or req.args.get("api_key") or req.form.get("api_key")
    return token == API_TOKEN

def decode_header_best(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value

def _tz(tzname: str):
    if ZoneInfo:
        try:
            return ZoneInfo(tzname)
        except Exception:
            return ZoneInfo("UTC")
    # fallback
    return timezone.utc

def parse_dt(val: str, tzname: str):
    """
    Terima:
      - '2025-10-14'
      - '2025-10-14 13:45'
      - '2025-10-14T13:45:10'
      - '2025-10-14T13:45:10+07:00'
    Kembalikan datetime aware (tz) atau None jika kosong.
    """
    if not val:
        return None
    val = val.strip()
    z = _tz(tzname or DEFAULT_TZ)
    # ISO full?
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=z)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    # Try 'YYYY-MM-DD HH:MM'
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(val, fmt)
            # tanggal saja → awal hari
            if fmt == "%Y-%m-%d":
                dt = dt.replace(hour=0, minute=0, second=0)
            dt = dt.replace(tzinfo=z)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    raise ValueError(f"Format tanggal/timestring tidak dikenali: {val}")

def imap_date_str(d: datetime, tzname: str):
    """
    IMAP SEARCH SINCE/BEFORE butuh tanggal (day precision), format: 14-Oct-2025
    Gunakan zona user agar batas harian sesuai ekspektasi.
    """
    z = _tz(tzname or DEFAULT_TZ)
    local = d.astimezone(z)
    return local.strftime("%d-%b-%Y")

def build_search_criteria(unseen_only=True, from_addr=None, keyword=None,
                          start_dt=None, end_dt=None, tzname=None):
    parts = []
    parts.append("UNSEEN" if unseen_only else "ALL")

    if from_addr:
        addr = from_addr.replace('"', '')
        parts.append(f'FROM "{addr}"')

    if keyword:
        kw = keyword.replace('"', '')
        parts.append(f'TEXT "{kw}"')

    # Tambahkan batas harian kasar di IMAP untuk memperkecil scope
    # SINCE inclusive; BEFORE exclusive.
    if start_dt:
        parts.append(f'SINCE {imap_date_str(start_dt, tzname)}')
    if end_dt:
        # Agar inclusive waktu, BEFORE harus hari+1 jika hanya tanggal.
        # Karena kita sudah punya waktu presisi, tetap pakai BEFORE tanggal end (bila end jam 23:59:59) atau end_dt+1hari untuk amankan.
        before_date = (end_dt + timedelta(days=1))
        parts.append(f'BEFORE {imap_date_str(before_date, tzname)}')

    return "(" + " ".join(parts) + ")"

def connect_and_search(mailbox, criteria, limit):
    imaplib.Commands["IDLE"] = ("NONAUTH",)
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.socket().settimeout(IMAP_TIMEOUT)
    conn.login(IMAP_USER, IMAP_PASS)
    typ, _ = conn.select(mailbox, readonly=True)
    if typ != "OK":
        conn.logout()
        raise RuntimeError(f"Gagal SELECT {mailbox}")

    typ, data = conn.search(None, criteria)
    if typ != "OK":
        conn.logout()
        raise RuntimeError(f"SEARCH {criteria} gagal")

    ids = data[0].split() if data and data[0] else []
    if not ids:
        conn.logout()
        return conn, []
    ids = ids[-limit:]  # terbaru
    return conn, ids

def extract_message(conn, seq_num):
    typ, msg_data = conn.fetch(seq_num, "(UID BODY.PEEK[])")
    if typ != "OK" or not msg_data or not msg_data[0]:
        return None

    uid = ""
    if msg_data and isinstance(msg_data[0], tuple) and msg_data[0][0]:
        m = re.search(rb'UID (\d+)', msg_data[0][0])
        if m:
            uid = m.group(1).decode()

    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw, policy=policy.default)

    subject = decode_header_best(msg.get("Subject"))
    from_   = decode_header_best(msg.get("From"))
    date_raw = msg.get("Date")
    # Parse ke UTC aware
    try:
        parsed_date = email.utils.parsedate_to_datetime(date_raw)
        if parsed_date and parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        date_iso = (parsed_date.astimezone(timezone.utc).isoformat()
                    if parsed_date else date_raw)
    except Exception:
        parsed_date = None
        date_iso = date_raw

    snippet = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp  = (part.get("Content-Disposition") or "").lower()
                if ctype == "text/plain" and "attachment" not in disp:
                    snippet = " ".join(str(part.get_content()).split())[:200]
                    break
        else:
            snippet = " ".join(str(msg.get_content()).split())[:200]
    except Exception:
        snippet = ""

    return {
        "uid": uid,
        "seq": seq_num.decode() if isinstance(seq_num, bytes) else str(seq_num),
        "from": from_,
        "subject": subject,
        "date": date_iso,
        "message_id": msg.get("Message-Id", "") or "",
        "snippet": snippet
    }

def within_range(row, start_dt_utc, end_dt_utc):
    """Post-filter presisi waktu di sisi aplikasi (UTC)."""
    if not start_dt_utc and not end_dt_utc:
        return True
    try:
        dt = datetime.fromisoformat(row["date"])
    except Exception:
        # jika Date tidak parseable, jangan keluarkan saat filter aktif
        return False
    if start_dt_utc and dt < start_dt_utc:
        return False
    if end_dt_utc and dt > end_dt_utc:
        return False
    return True

def save_as_json(filename, rows):
    path = EXPORT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return path.name

def save_as_csv(filename, rows):
    path = EXPORT_DIR / filename
    fieldnames = ["uid","seq","from","subject","date","message_id","snippet"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path.name

# -------------------- routes --------------------

@app.route("/exports/<path:fname>")
def download_file(fname):
    return send_from_directory(EXPORT_DIR, fname, as_attachment=True)

@app.route("/emails", methods=["GET","POST"])
def emails():
    if not require_token(request):
        return abort(401, description="Unauthorized")

    payload = request.form.to_dict() if request.method == "POST" else request.args.to_dict()
    if request.is_json:
        payload.update(request.get_json(silent=True) or {})

    mailbox  = payload.get("mailbox", IMAP_MAILBOX)
    limit    = int(payload.get("limit", 10))
    unseen   = payload.get("all", "").lower() not in ("1","true","yes")
    fromaddr = payload.get("from") or payload.get("sender")
    keyword  = payload.get("q") or payload.get("keyword")
    tzname   = payload.get("tz", DEFAULT_TZ)

    # Rentang waktu (string → datetime UTC)
    start_str = payload.get("start")  # contoh: 2025-10-14 00:00
    end_str   = payload.get("end")    # contoh: 2025-10-14 23:59:59
    try:
        start_dt_utc = parse_dt(start_str, tzname) if start_str else None
        end_dt_utc   = parse_dt(end_str, tzname) if end_str else None
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400

    criteria = build_search_criteria(
        unseen_only=unseen,
        from_addr=fromaddr,
        keyword=keyword,
        start_dt=start_dt_utc,
        end_dt=end_dt_utc,
        tzname=tzname
    )

    try:
        conn, ids = connect_and_search(mailbox, criteria, limit)
        rows = []
        for seq in ids:
            item = extract_message(conn, seq)
            if item:
                rows.append(item)
        try:
            conn.logout()
        except Exception:
            pass
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    # Post-filter presisi waktu (UTC)
    rows = [r for r in rows if within_range(r, start_dt_utc, end_dt_utc)]

    output_mode  = payload.get("output", "display")   # display | file
    file_format  = payload.get("format", "json")      # json | csv
    file_name    = payload.get("filename")

    if output_mode == "file":
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = file_name or f"emails_{stamp}"
        if not base.lower().endswith((".json",".csv")):
            base = base + (".csv" if file_format.lower()=="csv" else ".json")
        saved = save_as_csv(base, rows) if file_format.lower()=="csv" else save_as_json(base, rows)
        return jsonify({
            "ok": True,
            "count": len(rows),
            "saved_as": saved,
            "download_url": f"/exports/{saved}",
            "criteria": criteria,
            "tz": tzname
        })

    return jsonify({
        "ok": True,
        "count": len(rows),
        "criteria": criteria,
        "tz": tzname,
        "data": rows
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
