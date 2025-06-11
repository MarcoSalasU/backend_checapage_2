from flask import Flask, request, jsonify
import base64
import os
import uuid
import predict_crawl
import traceback
import nltk

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

MAX_HTML_SIZE = 500_000  # ~500KB
MAX_IMAGE_SIZE = 1_000_000  # ~1MB base64-encoded

@app.route("/analyze_content", methods=["POST"])
def analyze_content():
    try:
        data = request.get_json()
        html_content = data.get("html")
        img_base64 = data.get("img")

        # Log de longitudes
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("🧪 HTML length: " + str(len(html_content)) + "\n")
            log.write("🧪 IMG length: " + str(len(img_base64)) + "\n")

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

        # Guardar imagen base64 con manejo de errores mejorado
        img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.png")
        try:
            img_data = base64.b64decode(img_base64)
        except Exception as e:
            with open("/tmp/error.log", "a", encoding="utf-8") as log:
                log.write("❌ Error al decodificar imagen: " + str(e) + "\n")
            return jsonify({"error": "Imagen inválida"}), 400

        with open(img_path, "wb") as f:
            f.write(img_data)

        # Llamar a predict_crawl con validación y log de errores
        try:
            result = predict_crawl.predict(img_path, html_path)
            with open("/tmp/error.log", "a", encoding="utf-8") as log:
                log.write("✅ predict() se ejecutó en /analyze_content\n")
            if result is None or not isinstance(result, list) or len(result) == 0:
                raise ValueError("Modelo no devolvió un resultado válido")
            return jsonify({"prediction": int(result[0])})
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
        # Crear imagen de prueba
        test_img_path = "/tmp/test_ocr_img.png"
        img = Image.new("RGB", (200, 60), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "Login Now", fill=(0, 0, 0))
        img.save(test_img_path)

        # Crear HTML de prueba
        test_html_path = "/tmp/test_source.html"
        test_html = "<html><head><title>Test</title></head><body><h1>Welcome</h1><form><input name='user'></form></body></html>"
        with open(test_html_path, "w", encoding="utf-8") as f:
            f.write(test_html)

        # Log intermedio
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("✅ Imagen y HTML de prueba creados correctamente.\n")

        # Ejecutar predicción
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
