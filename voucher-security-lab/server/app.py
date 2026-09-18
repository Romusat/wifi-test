from flask import Flask, request, jsonify, send_from_directory, render_template
import os
from datetime import datetime, timezone, timedelta
import json
import secrets
import string
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import zipfile
from waitress import serve

app = Flask(__name__)

# Path for optional premium font (Inter). Falls back to default if missing.
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "Inter-Regular.ttf")
if os.path.exists(FONT_PATH):
    FONT = ImageFont.truetype(FONT_PATH, 20)
else:
    FONT = ImageFont.load_default()

# Load existing vouchers
with open("vouchers.json", "r") as f:
    vouchers = json.load(f)

def generate_voucher_code(length=8, prefix=""):
    characters = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(characters) for _ in range(length))
    return f"{prefix}{random_part}"

@app.route("/", methods=["GET"])
def index():
    # Serve a minimal modern UI (Tailwind CSS) for demo purposes.
    return render_template("index.html")

@app.route("/api/voucher/stats", methods=["GET"])
def get_stats():
    total = len(vouchers)
    used = sum(1 for v in vouchers.values() if v["used"])
    active = 0
    expired = 0
    now = datetime.now(timezone.utc)
    for v in vouchers.values():
        if not v["used"]:
            expires = datetime.fromisoformat(v["expires_at"].replace("Z", "+00:00"))
            if now >= expires:
                expired += 1
            else:
                active += 1
    return jsonify({
        "success": True, 
        "stats": {
            "total": total,
            "active": active,
            "used": used,
            "expired": expired
        }
    }), 200

@app.route("/api/voucher/download", methods=["GET"])
def download_all():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        voucher_dir = "static/vouchers"
        if os.path.exists(voucher_dir):
            for filename in os.listdir(voucher_dir):
                if filename.endswith(".png"):
                    filepath = os.path.join(voucher_dir, filename)
                    zf.write(filepath, filename)
    memory_file.seek(0)
    from flask import send_file
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='vouchers.zip'
    )

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
        vouchers[code] = {"used": False, "expires_at": expires_at}
        generated_codes.append(code)

    with open("vouchers.json", "w") as f:
        json.dump(vouchers, f, indent=2)

    if output_format == "image":
        os.makedirs("static/vouchers", exist_ok=True)
        image_urls = []
        for code in generated_codes:
            # Load the premium background template
            template_path = os.path.join(os.path.dirname(__file__), "static", "premium_bg.jpg")
            if os.path.exists(template_path):
                img = Image.open(template_path).resize((500, 300)).convert("RGB")
            else:
                # Fallback to white bg if template missing
                img = Image.new("RGB", (500, 300), color=(255, 255, 255))
            
            draw = ImageDraw.Draw(img)

            # QR code on the right side
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(code)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
            
            # Make QR background slightly transparent or keep white with rounded border if possible, but white is fine for contrast
            qr_w, qr_h = qr_img.size
            qr_x = 350
            qr_y = 75
            img.paste(qr_img, (qr_x, qr_y, qr_x + qr_w, qr_y + qr_h))

            # Voucher details
            draw.text((30, 40), "PREMIUM WI-FI", fill=(255, 255, 255), font=FONT)
            draw.text((30, 100), "ACCESS CODE:", fill=(200, 200, 255), font=FONT)
            
            # Larger font for code if possible, fallback to same font
            code_font = FONT
            if os.path.exists(FONT_PATH):
                code_font = ImageFont.truetype(FONT_PATH, 32)
            draw.text((30, 130), code, fill=(255, 255, 255), font=code_font)
            
            draw.text((30, 220), f"Expires in: {expires_in_days} days", fill=(200, 200, 255), font=FONT)

            filepath = f"static/vouchers/{code}.png"
            img.save(filepath, format="PNG", compress_level=6)
            image_urls.append(f"/static/vouchers/{code}.png")

        return jsonify({"success": True, "vouchers": generated_codes, "images": image_urls}), 200
    else:
        return jsonify({"success": True, "vouchers": generated_codes}), 200

@app.post("/api/voucher/reset")
def reset_vouchers():
    """Reset vouchers.json to initial state (for testing)."""
    auth = request.headers.get("Authorization")
    if auth != "Bearer admin-secret-token":
        return jsonify({"success": False, "error": "unauthorized"}), 401
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
        return jsonify({"success": False, "error": "missing_code"}), 400
    voucher = vouchers.get(code)
    if voucher is None:
        return jsonify({"success": False, "error": "invalid_voucher"}), 401
    if voucher["used"]:
        return jsonify({"success": False, "error": "voucher_used"}), 403
    expires = datetime.fromisoformat(voucher["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) >= expires:
        return jsonify({"success": False, "error": "voucher_expired"}), 403
    voucher["used"] = True
    return jsonify({"success": True, "message": "voucher_valid"}), 200

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        app.run(host="127.0.0.1", port=5000, debug=True)
    else:
        print("Starting production server with Waitress on port 5000...")
        serve(app, host="127.0.0.1", port=5000)
