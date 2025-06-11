import joblib
from feature_extract import extract_feature_vector

def predict(img_path, html_path):
    print("📥 Iniciando extracción de features...")
    vector = extract_feature_vector(img_path, html_path)

    if vector is None:
        print("⚠️ Feature vector no se pudo generar.")
        return None

    print("✅ Feature vector generado. Cargando modelo...")
    forest = joblib.load('saved_models/forest.pkl')

    print("🧠 Ejecutando predicción...")
    prediction = forest.predict([vector])

    print("✅ Predicción final:", prediction)
    return prediction
