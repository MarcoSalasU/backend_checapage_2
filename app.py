from flask import Flask, request, jsonify
import base64
import os
import uuid
import predict_crawl
import traceback

app = Flask(__name__)

UPLOAD_FOLDER = "tmp_inputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_HTML_SIZE = 500_000  # ~500KB
MAX_IMAGE_SIZE = 1_000_000  # ~1MB base64-encoded

@app.route("/analyze_content", methods=["POST"])
def analyze_content():
    try:
        data = request.get_json()
        html_content = data.get("html")
        img_base64 = data.get("img")

        if not html_content or not img_base64:
            return jsonify({"error": "Missing html or img data"}), 400

        if len(html_content) > MAX_HTML_SIZE:
            return jsonify({"error": "HTML content too large"}), 413

        if len(img_base64) > MAX_IMAGE_SIZE:
            return jsonify({"error": "Image data too large"}), 413

        if not img_base64.startswith("iVBOR") and not img_base64.startswith("/9j/"):
            return jsonify({"error": "Unsupported image format"}), 415  # PNG or JPEG expected

        # Guardar HTML
        html_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Guardar imagen base64
        img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.png")
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(img_base64))

        # Llamar a predict_crawl con validación y log de errores
        try:
            result = predict_crawl.predict(img_path, html_path)
            if result is None or not isinstance(result, list) or len(result) == 0:
                raise ValueError("Modelo no devolvió un resultado válido")
            return jsonify({"prediction": int(result[0])})
        except Exception as model_error:
            print("🔥 ERROR EN EL MODELO:")
            print(traceback.format_exc())
            return jsonify({"error": "Error en el modelo: " + str(model_error)}), 500

    except Exception as e:
        print("🔥 ERROR GENERAL:")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
