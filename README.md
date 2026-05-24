# 🚘 SGMA — Automotive Workshop Management System

> A real-time automotive workshop management solution built with Python, Streamlit and Google Sheets.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-Live%20Sync-green?style=flat-square&logo=googlesheets)
![Version](https://img.shields.io/badge/Version-1.0.0--beta-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

---

## 📋 About

**SGMA (Sistema de Gestão Mecânica Automotiva)** is a lightweight, cloud-based workshop management system designed to streamline the daily operations of automotive repair shops.

Built entirely in Python using Streamlit, the app provides a fast and intuitive interface to register service orders, track vehicle history, manage mechanics, and monitor financial performance — all backed by Google Sheets as a real-time database.

No complex infrastructure needed. Just open the browser and start working.

---

## ✨ Features

- 📝 **Service Order (OS) Registration** — Multi-service orders with vehicle data, assigned mechanic, diagnosis, cost and payment tracking
- 🔍 **History & Search** — Filter records by date range, mechanic, status, plate or OS number
- 💰 **Financial Dashboard** — Real-time metrics for revenue, repair costs and net balance
- 🔄 **Live Google Sheets Sync** — All data is read and written directly to Google Sheets with zero cache delay
- 🔐 **Role-based Authentication** — Admin and mechanic profiles with scoped access
- 📊 **Status Tracking** — Track each service order as *In Shop*, *In Budget* or *Finished*

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend & App | [Streamlit](https://streamlit.io) |
| Language | Python 3.10+ |
| Database | Google Sheets via `streamlit-gsheets` |
| Auth | Role-based login via `st.secrets` |
| Hosting | [Streamlit Community Cloud](https://share.streamlit.io) |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/ojcosta/sgm-app.git
cd sgm-app
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure secrets

Create the file `.streamlit/secrets.toml`:

```toml
[usuarios]
youruser = "yourpassword"

[connections.gsheets]
spreadsheet   = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"
type          = "service_account"
project_id    = "your-project-id"
private_key_id = "..."
private_key   = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email  = "your-service-account@project.iam.gserviceaccount.com"
client_id     = "..."
```

> ⚠️ Never commit `secrets.toml` to version control. It is already listed in `.gitignore`.

### 4. Run the app
```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
sgm-app/
├── .streamlit/
│   └── secrets.toml      # Local secrets (not versioned)
├── app.py                # Main application
├── requirements.txt      # Python dependencies
└── README.md
```

---

## 🔐 User Roles

| Role | Access |
|---|---|
| **Admin** | Full access: all OS records, financial dashboard, all mechanics |
| **Mechanic** | Restricted: only their own service orders, no financial data |

---

## 📸 Screenshots

> *Coming soon*

---

## 🗺️ Roadmap

- [ ] PDF export for service orders
- [ ] WhatsApp notification on OS completion
- [ ] Customer portal (view own OS history)
- [ ] Monthly financial charts
- [ ] Mobile-optimized layout

---

## 👨‍💻 Developer

Made with 👨🏽‍💻 by **Jonas Costa**

---

## 📄 License

This project is intended for private/commercial use within the workshop environment.  
For licensing inquiries, please contact the developer.
