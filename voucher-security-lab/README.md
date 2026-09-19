# Wi‑Fi Voucher Security Lab

A tiny Flask/Waitress application that simulates a Wi‑Fi voucher system.

## 📦 Project structure
```text
voucher-security-lab/
├─ server/                 # Flask app
│  ├─ app.py
│  ├─ static/vouchers/     # Generated QR-code images
│  └─ vouchers.json        # Current voucher state
├─ tester/                 # Security test suite
│  └─ security_tester.py
├─ reports/                # Test reports (`security_report.json`)
├─ initial_vouchers.json   # Seed file used by reset
└─ requirements.txt        # Python dependencies
```

## 🛠️ Prerequisites
- **Python 3.9+** (check with `python --version`)
- **Git** (to clone the repo)
- **PowerShell** (or any terminal on Windows)

## 📥 Clone the repository
```powershell
git clone https://github.com/Romusat/wifi-test.git
cd wifi-test/voucher-security-lab
```

## 📦 Install dependencies
```powershell
python -m pip install -r requirements.txt
```

## ▶️ Run the server
### Development mode (auto-reload, debugging)
```powershell
python server/app.py dev
```
The API will be available at `http://127.0.0.1:5000`.

### Production mode (Waitress)
```powershell
python server/app.py
```

## 🧪 Run the security test suite
Open a **second** terminal (so the server stays up) and execute:
```powershell
python tester/security_tester.py
```
The script prints a short report and also saves a JSON file to `reports/security_report.json`.

## 🔄 Reset voucher data
The endpoint `/api/voucher/reset` restores the original voucher list. It requires the authorization value configured by the server:
```powershell
$headers = @{ Authorization = "******" }
Invoke-WebRequest -Uri http://127.0.0.1:5000/api/voucher/reset -Method POST -Headers $headers
```

## 📄 Expected output (sample)
```
========== SECURITY REPORT ==========
[PASS] Empty input validation
[PASS] Invalid voucher handling
[PASS] Valid voucher
[PASS] Voucher reuse protection
[PASS] Expired voucher
[WARN] Rate-limit observation
[PASS] Information disclosure
[PASS] Voucher generator (text)
[PASS] Generated voucher validation
[PASS] Voucher generator (image)
Report disimpan ke reports/security_report.json
```

## 🛡️ Tips for token-conscious usage (Antigravity)
- Use `agy token status` to monitor token consumption.
- Cache static API responses with a small helper script (see `tools/cache_fetch.py`).
- Run the long-running test suite in the background with `agy run_command … --IsDaemon true`.

---
*Happy hacking!*