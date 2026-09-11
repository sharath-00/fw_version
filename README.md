# BBMP Panels - Firmware Version Monitoring & Mail Automation

Automated system to monitor firmware versions across **5,269 smart street light panels** in the BBMP Bangalore project via the ThingsBoard IoT REST API, analyze distribution across regions/zones, generate a modern HTML email dashboard, and dispatch daily reports via SMTP.

---

## Features

- **High Concurrency Telemetry Retrieval**: Multi-threaded fetcher (`ThreadPoolExecutor`) querying 5,269+ panels concurrently in seconds.
- **Focused Version Analytics**: Real-time aggregation of `.55`, `.54`, and `.47` firmware versions with connectivity status (Online vs Offline).
- **Region & Zone Matrix**: Hierarchical adoption matrix covering Bommanahalli and East zones (CV Raman Nagar, Hebbal, Pulakeshi Nagar, Sarvagna Nagar, Shanthi Nagar, Shivaji Nagar).
- **Executive HTML Email Dashboard**: Clean, responsive layout compatible across Gmail, Outlook, and mobile clients.
- **Environment-Driven Configuration**: All credentials securely stored in `.env`.
- **1-Click Execution**: Windows batch runner (`run_daily_report.bat`) for manual runs or automated scheduling.

---

## Project Structure

```
├── .env.example               # Template environment configuration
├── config.py                  # Configuration loader
├── tb_client.py               # ThingsBoard REST API Client
├── fw_analyzer.py             # Firmware analytics & aggregation
├── report_generator.py        # HTML email dashboard generator
├── mail_sender.py             # SMTP email dispatcher
├── main.py                    # Main CLI orchestrator
├── run_daily_report.bat       # 1-Click batch trigger
└── requirements.txt           # Python dependencies
```

---

## Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sharath-00/fw_version.git
   cd fw_version
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your ThingsBoard & SMTP credentials:
   ```bash
   cp .env.example .env
   ```

---

## Usage

- **Run full pipeline and dispatch email**:
  ```bash
  python main.py --send-now
  ```

- **Generate local preview without sending email**:
  ```bash
  python main.py
  ```

- **Run using cached data**:
  ```bash
  python main.py --cached
  ```

- **Or 1-Click via Windows Batch**:
  Double-click `run_daily_report.bat`.
