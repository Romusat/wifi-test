from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timezone, timedelta
import json
import secrets
import string
import os
from PIL import Image, ImageDraw
import qrcode

app = Flask(__name__)

with open("vouchers.json", "r") as f:
    vouchers = json.load(f)

def generate_voucher_code(length=8, prefix=""):
    characters = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(characters) for _ in range(length))
    return f"{prefix}{random_part}"

@app.post("/api/voucher/generate")
def generate_voucher():
    data = request.get_json(silent=True) or {}
    count = data.get("count", 1)
    length = data.get("length", 8)
    prefix = data.get("prefix", "")
    output_format = data.get("format", "text")
    expires_in_days = data.get("expires_in_days", 7)

    if count < 1 or count > 100:
        return jsonify({"success": False, "error": "invalid_count"}), 400

    generated_codes = []
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for _ in range(count):
        while True:
            code = generate_voucher_code(length, prefix)
            if code not in vouchers:
                break
        
        vouchers[code] = {
            "used": False,
            "expires_at": expires_at
        }
        generated_codes.append(code)
    
    with open("vouchers.json", "w") as f:
        json.dump(vouchers, f, indent=2)
    
    if output_format == "image":
        os.makedirs("static/vouchers", exist_ok=True)
        image_urls = []
        for code in generated_codes:
            img = Image.new("RGB", (400, 200), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            qr = qrcode.QRCode(box_size=4, border=1)
            qr.add_data(code)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            # Paste using a 4‑item box to avoid Pillow region‑size error
            img.paste(qr_img, (250, 50, 250 + qr_img.width, 50 + qr_img.height))
            
            draw.text((20, 20), "WIFI VOUCHER", fill=(0, 0, 0))
            draw.text((20, 60), f"Code: {code}", fill=(0, 0, 0))
            draw.text((20, 100), f"Expires in: {expires_in_days} days", fill=(0, 0, 0))
            
            filepath = f"static/vouchers/{code}.png"
            img.save(filepath)
            
            image_urls.append(f"/static/vouchers/{code}.png")
            
        return jsonify({
            "success": True,
            "vouchers": generated_codes,
            "images": image_urls
        }), 200
        
@app.post("/api/voucher/reset")
def reset_vouchers():
    """Reset vouchers.json to initial state (for testing)."""
    # Load initial data from a known file
    try:
        with open("initial_vouchers.json", "r") as f:
            initial = json.load(f)
    except Exception as e:
        return jsonify({"success": False, "error": "reset_failed", "detail": str(e)}), 500
    with open("vouchers.json", "w") as f:
        json.dump(initial, f, indent=2)
    return jsonify({"success": True, "message": "vouchers reset"}), 200


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
