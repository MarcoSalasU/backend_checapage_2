import joblib
from feature_extract import extract_feature_vector

def predict(img_path, html_path):
    vector = extract_feature_vector(img_path, html_path)

    if vector is None:
        return None, None

    forest = joblib.load('saved_models/forest.pkl')
    prediction = forest.predict([vector])[0]
    probabilidad = forest.predict_proba([vector])[0][1]  # clase 1 = malicioso

    return prediction, probabilidad
