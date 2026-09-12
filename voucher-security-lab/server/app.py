from flask import Flask, request, jsonify
from datetime import datetime, timezone
import json

app = Flask(__name__)

with open("vouchers.json", "r") as f:
    vouchers = json.load(f)


@app.post("/api/voucher/validate")
def validate_voucher():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()

    if not code:
        return jsonify({
            "success": False,
            "error": "missing_code"
        }), 400

    voucher = vouchers.get(code)

    if voucher is None:
        return jsonify({
            "success": False,
            "error": "invalid_voucher"
        }), 401

    if voucher["used"]:
        return jsonify({
            "success": False,
            "error": "voucher_used"
        }), 403

    expires = datetime.fromisoformat(
        voucher["expires_at"].replace("Z", "+00:00")
    )

    if datetime.now(timezone.utc) >= expires:
        return jsonify({
            "success": False,
            "error": "voucher_expired"
        }), 403

    voucher["used"] = True

    return jsonify({
        "success": True,
        "message": "voucher_valid"
    }), 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
