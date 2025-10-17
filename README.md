# IMAP-mail-retriever
IMAP Mail Retriever is a lightweight Python-based tool designed to connect to mail servers via the IMAP protocol and retrieve emails efficiently.


Cara pakai (contoh)

POST: ambil UNSEEN dari pengirim tertentu pada 14 Okt 2025, pukul 00:00–23:59 WIB, tampilkan langsung:

curl -X POST http://localhost:5000/emails \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'X-API-Key: supersecrettoken' \
  -d 'from=billing@rumahhosting.net' \
  -d 'start=2025-10-14 00:00' \
  -d 'end=2025-10-14 23:59:59' \
  -d 'tz=Asia/Jakarta' \
  -d 'limit=50'


POST: semua pesan (all=1) yang mengandung keyword “invoice” selama 13–14 Okt 2025 WIB, simpan ke CSV:

curl -X POST http://localhost:5000/emails \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'X-API-Key: supersecrettoken' \
  -d 'q=invoice' \
  -d 'all=1' \
  -d 'start=2025-10-13' \
  -d 'end=2025-10-14 23:59:59' \
  -d 'tz=Asia/Jakarta' \
  -d 'output=file' \
  -d 'format=csv' \
  -d 'filename=invoice_13-14Oct.csv'


Catatan teknis singkat

IMAP hanya mendukung hari untuk SINCE/BEFORE, jadi range waktu jam:menit dikerjakan post-filter setelah pesan diambil.

Zona waktu default Asia/Jakarta; bisa ubah via .env (DEFAULT_TZ) atau parameter tz.

Jika header Date email tidak valid, item tersebut tidak ikut saat filter waktu aktif.