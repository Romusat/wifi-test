import requests
import time
import json
import re

BASE_URL = "http://127.0.0.1:5000"
ENDPOINT = f"{BASE_URL}/api/voucher/validate"

results = []


def record(test, status, detail):
    results.append({
        "test": test,
        "status": status,
        "detail": detail
    })


def send(code):
    try:
        response = requests.post(
            ENDPOINT,
            json={"code": code},
            timeout=3
        )

        return response.status_code, response.json()

    except Exception as e:
        return None, {"error": str(e)}


# --------------------------------------------------
# 1. Empty input
# --------------------------------------------------

status, body = send("")

if status == 400:
    record(
        "Empty input validation",
        "PASS",
        "Server menolak kode kosong."
    )
else:
    record(
        "Empty input validation",
        "WARN",
        f"Unexpected response: {status}"
    )


# --------------------------------------------------
# 2. Invalid voucher
# --------------------------------------------------

status, body = send("INVALID-LAB-CODE")

if status in [400, 401, 403]:
    record(
        "Invalid voucher handling",
        "PASS",
        f"Invalid voucher ditolak dengan HTTP {status}."
    )
else:
    record(
        "Invalid voucher handling",
        "WARN",
        f"Unexpected HTTP {status}"
    )


# --------------------------------------------------
# 3. Valid voucher
# --------------------------------------------------

status, body = send("LAB-TEST-01")

if status == 200 and body.get("success") is True:
    record(
        "Valid voucher",
        "PASS",
        "Voucher test diterima."
    )
else:
    record(
        "Valid voucher",
        "FAIL",
        f"Voucher test tidak diterima: {status} {body}"
    )


# --------------------------------------------------
# 4. Voucher reuse
# --------------------------------------------------

status, body = send("LAB-TEST-01")

if status in [403, 409]:
    record(
        "Voucher reuse protection",
        "PASS",
        "Voucher yang sudah digunakan ditolak."
    )
else:
    record(
        "Voucher reuse protection",
        "FAIL",
        f"Voucher masih diterima setelah digunakan: HTTP {status}"
    )


# --------------------------------------------------
# 5. Expired voucher
# --------------------------------------------------

status, body = send("LAB-EXPIRED-01")

if status in [403, 410]:
    record(
        "Expired voucher",
        "PASS",
        "Voucher expired ditolak."
    )
else:
    record(
        "Expired voucher",
        "FAIL",
        f"Voucher expired diterima: HTTP {status}"
    )


# --------------------------------------------------
# 6. Rate-limit observation
#
# Hanya menggunakan kode dummy.
# Tidak melakukan brute force.
# --------------------------------------------------

start = time.time()

for _ in range(10):
    send("INVALID-LAB-CODE")

elapsed = time.time() - start

if elapsed < 1:
    record(
        "Rate-limit observation",
        "WARN",
        "10 request dummy selesai sangat cepat. "
        "Perlu diperiksa apakah server memiliki rate limiting."
    )
else:
    record(
        "Rate-limit observation",
        "PASS",
        f"Server membutuhkan {elapsed:.2f} detik untuk 10 request."
    )


# --------------------------------------------------
# 7. Error information disclosure
# --------------------------------------------------

status, body = send("INVALID-LAB-CODE")

body_text = json.dumps(body).lower()

suspicious = [
    "sql",
    "database",
    "mysql",
    "postgres",
    "exception",
    "traceback",
    "stack trace",
    "file path"
]

found = [x for x in suspicious if x in body_text]

if found:
    record(
        "Information disclosure",
        "FAIL",
        f"Response mengandung informasi sensitif: {found}"
    )
else:
    record(
        "Information disclosure",
        "PASS",
        "Tidak terlihat informasi error internal."
    )


# --------------------------------------------------
# Report
# --------------------------------------------------

print("\n========== SECURITY REPORT ==========\n")

for item in results:
    print(
        f"[{item['status']}] "
        f"{item['test']}\n"
        f"       {item['detail']}\n"
    )

with open("../reports/security_report.json", "w") as f:
    json.dump(results, f, indent=4)

print("Report disimpan ke reports/security_report.json")
