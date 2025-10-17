# 📧 IMAP Email Retriever API

A lightweight Flask-based REST API for fetching and filtering emails directly from an IMAP mailbox.  
Designed for self-hosted mail environments (e.g., **DirectAdmin**, **cPanel**, or **Mailcow**) without relying on any external mail services.

---

## 🚀 Features

- 🔐 Secure IMAP connection (SSL/TLS)
- 📬 Retrieve unseen or all emails
- 🎯 Advanced filtering:
  - By sender (`from`)
  - By keyword (`q`)
  - By date/time range (`start`, `end`)
- 🕒 Timezone support (`tz` parameter, default: `Asia/Jakarta`)
- 💾 Output options:
  - Direct JSON response
  - Save results to `.json` or `.csv` files (with download link)
- ⚙️ Configurable via `.env`
- 🧩 Optional API token protection

---

## 🧱 Tech Stack

- **Python 3.9+**
- **Flask**
- **IMAP (SSL)**
- **python-dotenv**

---

## 📂 Project Structure

```

.
├── app.py             # Main Flask API
├── .env               # Environment configuration
├── exports/           # Auto-created folder for saved results
└── README.md

````

---

## ⚙️ Setup

### 1️⃣ Clone and install dependencies
```bash
git clone https://github.com/rizkychi/IMAP-mail-retriever.git
cd imap-email-retriever
pip install flask python-dotenv
````

### 2️⃣ Create `.env` file

```bash
IMAP_HOST=mail.yourdomain.com
IMAP_PORT=993
IMAP_USER=your@email.com
IMAP_PASS=yourpassword
IMAP_MAILBOX=INBOX
IMAP_TIMEOUT=30
DEFAULT_TZ=Asia/Jakarta
API_TOKEN=supersecrettoken
```

### 3️⃣ Run the server

```bash
python app.py
```

By default, the API runs at:

```
http://localhost:5000
```

---

## 🧭 API Endpoints

### `POST /emails`

Retrieve filtered email data from your IMAP mailbox.

#### Request Parameters (form-data or JSON)

| Parameter         | Type   | Description                                 |
| ----------------- | ------ | ------------------------------------------- |
| `from` / `sender` | string | Filter by sender email                      |
| `q` / `keyword`   | string | Filter by keyword in subject or body        |
| `start`           | string | Start datetime (e.g. `2025-10-14 00:00`)    |
| `end`             | string | End datetime (e.g. `2025-10-14 23:59:59`)   |
| `tz`              | string | Timezone (default: `Asia/Jakarta`)          |
| `all`             | bool   | Include all messages instead of only unseen |
| `limit`           | int    | Number of messages to retrieve              |
| `output`          | string | `display` (default) or `file`               |
| `format`          | string | `json` or `csv` (for file output)           |
| `filename`        | string | Optional custom filename                    |
| `api_key`         | string | Must match `API_TOKEN` from `.env`          |

---

### 🧪 Example Requests

#### 1️⃣ Basic (Unseen only)

```bash
curl -X POST http://localhost:5000/emails \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: supersecrettoken" \
  -d "limit=5"
```

#### 2️⃣ Filter by sender and keyword

```bash
curl -X POST http://localhost:5000/emails \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: supersecrettoken" \
  -d "from=yourfriend@email.com" \
  -d "q=invoice"
```

#### 3️⃣ Filter by date/time range

```bash
curl -X POST http://localhost:5000/emails \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: supersecrettoken" \
  -d "start=2025-10-14 00:00" \
  -d "end=2025-10-14 23:59:59" \
  -d "tz=Asia/Jakarta"
```

#### 4️⃣ Save results to CSV

```bash
curl -X POST http://localhost:5000/emails \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-API-Key: supersecrettoken" \
  -d "q=reset password" \
  -d "output=file" \
  -d "format=csv"
```

Response:

```json
{
  "ok": true,
  "count": 3,
  "saved_as": "emails_20251014_135930.csv",
  "download_url": "/exports/emails_20251014_135930.csv"
}
```

---

## 📤 File Downloads

Saved files are stored under the `/exports` directory.
They can be downloaded directly from:

```
http://localhost:5000/exports/<filename>
```

---

## 🔒 Security Notes

* Always protect your `.env` file and never commit it to version control.
* Use strong `API_TOKEN` values for authentication.
* Deploy behind HTTPS if exposed publicly.
* For production, consider running behind **Nginx + Gunicorn**.

---

## 🧠 Future Enhancements

* OAuth2 (Gmail / Outlook) integration
* IMAP IDLE (real-time push notifications)
* Pagination and caching
* Frontend dashboard for email viewing

---

## 🪪 License

This project is licensed under the **GPL-3.0 license** — see the [LICENSE](LICENSE) file for details.

---

## 🧑‍💻 Author

**Developed by:** Rizkychi
**Contact:** [[rizkynhae@gmail.com](mailto:rizkynhae@gmail.com)]
**GitHub:** [@rizkychi](https://github.com/rizkychi)
