from flask import Flask, request, jsonify
import base64
import os
import uuid
import predict_crawl
import traceback
import nltk
import re

# Descargar recursos necesarios de NLTK
try:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('averaged_perceptron_tagger')
except Exception as e:
    with open("/tmp/error.log", "a", encoding="utf-8") as f:
        f.write("❌ Error descargando recursos NLTK: " + str(e) + "\n")

app = Flask(__name__)

UPLOAD_FOLDER = "tmp_inputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_HTML_SIZE = 9_000_000
MAX_IMAGE_SIZE = 9_000_000

# Cargar whitelist desde CSV
def load_whitelist(path="whitelist.csv"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(line.strip().lower().replace('"', '') for line in f if line.strip())
    except Exception as e:
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("❌ Error al cargar whitelist: " + str(e) + "\n")
        return set()

WHITELIST = load_whitelist()

def pertenece_a_whitelist(html_text):
    for dominio in WHITELIST:
        patron = rf"https?://(www\.)?{re.escape(dominio)}"
        if re.search(patron, html_text.lower()):
            return True
    return False

@app.route("/analyze_content", methods=["POST"])
def analyze_content():
    try:
        data = request.get_json()
        html_content = data.get("html")
        img_base64 = data.get("img")

        print("Tamaño HTML:", len(html_content))
        if img_base64:
            print("Tamaño IMG base64:", len(img_base64))

        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("🧪 HTML length: " + str(len(html_content)) + "\n")
            if img_base64:
                log.write("🧪 IMG length: " + str(len(img_base64)) + "\n")

        # Solo validar si HTML existe
        if not html_content:
            return jsonify({"error": "No se recibió contenido HTML"}), 400

        if len(html_content) > MAX_HTML_SIZE:
            return jsonify({"error": "HTML content too large"}), 413

        # Imagen puede venir vacía, pero seguimos analizando
        img_path = None
        if img_base64:
            if len(img_base64) > MAX_IMAGE_SIZE:
                return jsonify({"error": "Image data too large"}), 413

            if not img_base64.startswith("iVBOR") and not img_base64.startswith("/9j/"):
                return jsonify({"error": "Unsupported image format"}), 415

            img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.png")
            try:
                img_data = base64.b64decode(img_base64)
                with open(img_path, "wb") as f:
                    f.write(img_data)
            except Exception as e:
                with open("/tmp/error.log", "a", encoding="utf-8") as log:
                    log.write("❌ Error al decodificar imagen: " + str(e) + "\n")
                return jsonify({"error": "Imagen inválida"}), 400
        else:
            print("⚠️ Imagen no enviada. Se usará solo HTML.")

        # VERIFICACIÓN CONTRA WHITELIST
        if pertenece_a_whitelist(html_content):
            return jsonify({
                "prediction": 0,
                "probabilidad": 0.0,
                "whitelisted": True
            })

        html_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        try:
            pred, prob = predict_crawl.predict(img_path, html_path)

            if pred is None:
                raise ValueError("Modelo no devolvió una predicción")

            # 📌 Penalizar si detectamos HTTP en el contenido
            if "http://" in html_content.lower():
                prob = min(prob + 0.10, 1.0)  # Nunca superar 100%

            with open("/tmp/error.log", "a", encoding="utf-8") as log:
                log.write(f"✅ Resultado: {pred}, prob: {prob}\n")
                log.write(f"✅ prediction enviada: {pred}, prob: {prob}\n")

            return jsonify({
                "prediction": int(pred),
                "probabilidad": float(prob)
            })
        except Exception as model_error:
            print("🔥 ERROR EN EL MODELO:")
            print(traceback.format_exc())
            return jsonify({"error": "Error en el modelo: " + str(model_error)}), 500

    except Exception as e:
        error_trace = traceback.format_exc()
        with open("/tmp/error.log", "a", encoding="utf-8") as f:
            f.write("🔥 ERROR GENERAL:\n")
            f.write(error_trace + "\n")
        return jsonify({"error": str(e)}), 500

@app.route("/ver_error")
def ver_error():
    try:
        with open("/tmp/error.log", "r", encoding="utf-8") as f:
            contenido = f.read()
        return f"<pre>{contenido}</pre>"
    except:
        return "No hay errores registrados aún."

@app.route("/test_input", methods=["GET"])
def test_input():
    from PIL import Image, ImageDraw
    import traceback

    try:
        test_img_path = "/tmp/test_ocr_img.png"
        img = Image.new("RGB", (200, 60), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "Login Now", fill=(0, 0, 0))
        img.save(test_img_path)

        test_html_path = "/tmp/test_source.html"
        test_html = "<html><head><title>Test</title></head><body><h1>Welcome</h1><form><input name='user'></form></body></html>"
        with open(test_html_path, "w", encoding="utf-8") as f:
            f.write(test_html)

        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("✅ Imagen y HTML de prueba creados correctamente.\n")

        from predict_crawl import predict
        result = predict(test_img_path, test_html_path)

        if result is None:
            with open("/tmp/error.log", "a", encoding="utf-8") as log:
                log.write("⚠️ predict() retornó None\n")
            return jsonify({"prediction": "Error: no prediction returned"})

        return jsonify({"prediction": int(result[0])})

    except Exception as e:
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("❌ EXCEPCIÓN EN /test_input:\n")
            log.write(traceback.format_exc() + "\n")
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
