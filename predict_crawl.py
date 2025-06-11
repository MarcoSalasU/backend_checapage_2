import joblib
from feature_extract import extract_feature_vector

def predict(img_path, html_path):
    vector = extract_feature_vector(img_path, html_path)
    
    if vector is None:
        return None  # 🔴 Si no se pudo generar vector, se evita fallo

    forest = joblib.load('saved_models/forest.pkl')
    prediction = forest.predict([vector])
    
    return prediction  # ✅ Retorna como lista [0] o [1]
