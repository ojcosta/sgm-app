# 🚘 SGMA — Automotive Workshop Management System

> A cloud-based workshop management app built with Python, Streamlit and Google Sheets.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-app-red?style=flat-square&logo=streamlit)
![Google Sheets](https://img.shields.io/badge/Database-Google%20Sheets-green?style=flat-square&logo=googlesheets)
<!-- Keep this badge in sync with APP_VERSAO in app.py -->
![Version](https://img.shields.io/badge/Version-0.9.5--beta-orange?style=flat-square)

---

## 📋 About

**SGMA (Sistema de Gestão Mecânica Automotiva)** is a lightweight, browser-based system to register service orders (OS), keep a vehicle service history and follow the financial results of an automotive repair shop.

It is written entirely in Python with Streamlit and uses a Google Sheets spreadsheet as its data store. There is nothing to install for the end user: open the browser and log in.

> **Status: beta.** One deployment serves **one** workshop and **one** spreadsheet. See [Known limitations](#-known-limitations) before using it with real data.

---

## ✨ Features

- 📝 **Service Order (OS) registration** — multi-service orders with vehicle data, responsible mechanic, defect, diagnosis, executed service, cost and payment received. New orders are appended to the spreadsheet and receive a unique OS number reserved in a dedicated tab.
- ✏️ **OS editing (admin)** — edit any line of an existing OS. Only the fields you actually changed are written, the editor and date of the last edit are recorded, and the edit is refused if someone else changed that row after you opened it.
- 📥 **Client requests (admin)** — requests sent through the public companion form (`sgmaforms`) can be accepted or refused; accepting pre-fills the OS registration screen.
- 🔍 **History & search** — filter by date range, mechanic, and plate or OS number.
- 💰 **Financial overview (admin)** — totals of cost and payments, including a monthly chart.
- 🖨️ **PDF** — print or reprint the service order as a PDF.
- 🔐 **Role-based access** — *admin* and *mechanic* profiles; mechanics only see their own orders. Passwords are stored as bcrypt hashes.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| App / UI | [Streamlit](https://streamlit.io) |
| Language | Python 3.12 |
| Data store | Google Sheets (`st-gsheets-connection` for reads and full-tab updates, `gspread` for appends) |
| Auth | Users in `st.secrets`, passwords hashed with `bcrypt` |
| PDF | ReportLab |
| Charts | Altair |
| Hosting | [Streamlit Community Cloud](https://share.streamlit.io) |

---

## 🗂️ Spreadsheet structure

The app expects a Google Sheets file with these tabs. Details and rules are in [`SCHEMA.md`](SCHEMA.md).

| Tab | Purpose |
|---|---|
| **First tab** (any name) | One row per service of each OS. Must have the exact header columns listed in `SCHEMA.md`. **It must be the first tab in the file.** |
| `SEQUENCIA` | Reserves OS numbers. `A1` = `OS`, `B1` = `RESERVADO_EM`, `C1` = `RESERVADO_POR`; `A2` = last OS number already used. Never edit `A2`, sort, or delete rows afterwards. |
| `CADASTROS` | Client requests written by the public form (`sgmaforms`). |

Share the spreadsheet with the service account e-mail (`client_email`) as **Editor**.

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/ojcosta/sgm-app.git
cd sgm-app
```

### 2. Install dependencies
```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Prepare the spreadsheet
Create the tabs described in [Spreadsheet structure](#️-spreadsheet-structure), including `SEQUENCIA` with the last used OS number in `A2` (use `0` for a new spreadsheet).

### 4. Configure secrets

Create `.streamlit/secrets.toml`:

```toml
[usuarios]
# Values MUST be bcrypt hashes, not plain-text passwords.
# Usernames must be lower case and listed in PERFIS inside app.py.
someuser = "$2b$12$...hash..."

[connections.gsheets]
spreadsheet    = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"
type           = "service_account"
project_id     = "your-project-id"
private_key_id = "..."
private_key    = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email   = "your-service-account@project.iam.gserviceaccount.com"
client_id      = "..."
```

Generate a password hash:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'the_password', bcrypt.gensalt()).decode())"
```

> ⚠️ Never commit `secrets.toml`. Make sure the file is named exactly `.gitignore` (with the leading dot) and contains `.streamlit/secrets.toml`. If a secret ever reached the git history, revoke it and create a new one.

### 5. Run the app
```bash
streamlit run app.py
```

> 💡 Test against a **copy** of the spreadsheet first, never against production data.

---

## 📁 Project Structure

```
sgm-app/
├── .devcontainer/        # Dev container configuration
├── .streamlit/
│   └── secrets.toml      # Local secrets (not versioned)
├── app.py                # Main application
├── requirements.txt      # Python dependencies
├── SCHEMA.md             # Data contract shared with sgmaforms
├── index.html            # Static page, not part of the Streamlit app
├── style.css             # Styles for index.html
├── .gitignore
└── README.md
```

---

## 🔐 User Roles

| Role | Access |
|---|---|
| **Admin** | Register OS, client requests, edit OS, history and financial overview, About |
| **Mechanic** | Register OS, own orders only (no financial data, no editing), About |

Users, roles and the username → mechanic-name mapping are currently **defined in `app.py`** (`PERFIS`, `USUARIO_PARA_MECANICO`, `LISTA_MECANICOS`), and the matching password hashes live in `st.secrets`.

---

## 🔗 Companion app: `sgmaforms`

A separate Streamlit app (separate repository, deployment and service account) lets clients submit repair requests, which are written to the `CADASTROS` tab of the same spreadsheet. The two apps share no code, only the spreadsheet structure documented in [`SCHEMA.md`](SCHEMA.md). **Read it before changing tab names, columns or `STATUS` values.**

---

## ⚠️ Known limitations

- **Google Sheets is not a transactional database.** There is no referential integrity, no locking, and the Sheets API has request quotas. Every screen interaction triggers a read.
- **Concurrent writes are only protected where noted.** Registering a new OS appends rows and reserves its number atomically. Editing an OS writes only the changed cells and checks that the row did not change since it was opened (a window of milliseconds remains between the check and the write). **Updating client requests (accept/refuse) still rewrites the whole `CADASTROS` tab** (clear, then write), so simultaneous updates, or a read during the rewrite, can lose or hide data.
- **OS numbers can have gaps.** A number is reserved before saving; if saving fails, that number is not reused.
- **PDF totals:** blank cost or payment cells in old rows can make the PDF totals show `nan` (known bug, not fixed yet).
- **Login has no attempt limit.**
- **Not multi-tenant.** Users, roles and mechanic lists are hardcoded in `app.py`; one deployment equals one workshop.
- **Data privacy:** the app stores names, phone numbers and license plates of workshop clients. Using it in production implies LGPD obligations for the workshop.

---

## 🗺️ Roadmap

- [x] Update only the changed cells in *Edit OS* (with conflict detection)
- [ ] Update only the changed row in *Client requests* (no more whole-tab rewrites)
- [ ] Fix `nan` totals in the PDF
- [ ] End-to-end validation of the `sgmaforms` → `CADASTROS` → admin flow
- [ ] Link an accepted client request to the OS it generated
- [ ] WhatsApp notification on OS completion
- [ ] Customer portal (view own OS history)
- [ ] Mobile-optimized layout

---

## 👨‍💻 Developer

Made by **Jonas Costa**

---

## 📄 License

This project is intended for private/commercial use within the workshop environment.
For licensing inquiries, please contact the developer.
