#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Importaciones para procesamiento de imágenes y texto
try:
    import Image
except ImportError:
    from PIL import Image

import pytesseract  # Para OCR (reconocimiento de texto en imágenes)
from bs4 import BeautifulSoup  # Para parsear HTML
from nltk import word_tokenize
from nltk.corpus import stopwords
from nltk import tag

import WORD_TERM_KEYS
import re
import os

# Vocabulario predefinido para vectorización
WORD_TERM = WORD_TERM_KEYS.WORD_TERM
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def get_img_text_ocr(img_path):
    """
    Extrae texto de una imagen usando OCR
    - Procesa la imagen para obtener texto
    - Elimina palabras comunes y caracteres especiales
    - Retorna texto limpio y procesado
    """
    try:
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img, lang='eng')
        sent = word_tokenize(text.lower())
        words = [word.lower() for word in sent if word.isalpha()]
        stop_words = set(stopwords.words('english'))
        words = [w for w in words if w not in stop_words]
        ocr_text = ' '.join(words)
        return ocr_text
    except Exception as e:
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("❌ Falla en get_img_text_ocr: " + str(e) + "\n")
        return ""

def get_structure_html_text(html_path):
    """
    Analiza la estructura HTML de una página
    - Extrae texto de diferentes elementos (encabezados, párrafos, enlaces)
    - Analiza formularios y sus atributos
    - Procesa el texto para eliminar palabras comunes
    """
    try:
        with open(html_path, 'r', encoding='utf-8') as myfile:
            data = myfile.read()
        try:
            soup = BeautifulSoup(data, "lxml")
        except Exception as inst:
            with open('/tmp/error.log', 'a', encoding='utf-8') as f:
                f.write("❌ SoupParse Exception: " + str(type(inst)) + " " + str(html_path) + '\n')
            return None, None, None

        heads = '.'.join(t.text for t in soup.find_all(re.compile(r'h\d+')))
        things = '.'.join(p.text for p in soup.find_all('p'))
        tags = '.'.join(a.text for a in soup.find_all('a'))
        titles = '.'.join(t.text for t in soup.find_all('title'))

        raw = heads + ' ' + things + ' ' + tags + ' ' + titles
        sent = word_tokenize(raw)
        tokens = tag.pos_tag(sent)
        words = [word.lower() for word, _ in tokens if word.isalpha()]
        stop_words = set(stopwords.words('english'))
        words = [w for w in words if w not in stop_words]
        text_word_str = ' '.join(words)

        forms = soup.find_all('form')
        num_of_forms = len(forms)
        candidate_attributes = ['type', 'name', 'submit', 'placeholder']
        attr_word_list = []

        for form in forms:
            inputs = form.find_all('input')
            for i in inputs:
                for j in candidate_attributes:
                    if i.has_attr(j):
                        attr_word_list.append(i[j])

        attr_word_str = ' '.join(attr_word_list)
        words = word_tokenize(attr_word_str)
        words = [word.lower() for word in words if word.isalpha()]
        words = [w for w in words if w not in stop_words]
        attr_word_str = ' '.join(words)

        return text_word_str, num_of_forms, attr_word_str
    except Exception as e:
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("❌ Falla en get_structure_html_text: " + str(e) + "\n")
        return "", 0, ""

def text_embedding_into_vector(txt_str):
    """
    Convierte texto en un vector numérico
    - Crea un vector de características basado en el vocabulario predefinido
    - Cuenta la frecuencia de cada palabra
    """
    texts = txt_str.split(' ')
    texts = [w.lower() for w in texts if w.isalpha()]
    embedding_vector = [0] * (len(WORD_TERM) + 1)
    for elem in texts:
        index = WORD_TERM.index(elem) if elem in WORD_TERM else -1
        embedding_vector[index] += 1
    return embedding_vector

def feature_vector_extraction(c):
    """
    Función principal que extrae todas las características
    - Combina características de imagen, texto y formularios
    - Crea un vector final para análisis
    """
    if os.path.exists(c.web_source) and os.path.exists(c.web_img):
        try:
            img_text = get_img_text_ocr(c.web_img)
            text_word_str, num_of_forms, attr_word_str = get_structure_html_text(c.web_source)
            img_v = text_embedding_into_vector(img_text)
            txt_v = text_embedding_into_vector(text_word_str)
            form_v = text_embedding_into_vector(attr_word_str)
            final_v = img_v + txt_v + form_v + [num_of_forms]
            return final_v
        except Exception as e:
            with open("/tmp/error.log", "a", encoding="utf-8") as log:
                log.write("❌ Falla en feature_vector_extraction: " + str(e) + "\n")
            return None

def feature_vector_extraction_from_img_html(img, html):
    try:
        img_text = ""
        if os.path.exists(img):
            img_text = get_img_text_ocr(img)

        text_word_str, num_of_forms, attr_word_str = get_structure_html_text(html)

        img_v = text_embedding_into_vector(img_text)
        txt_v = text_embedding_into_vector(text_word_str)
        form_v = text_embedding_into_vector(attr_word_str)

        img_v = [0.3 * val for val in img_v]  # peso menor para OCR

        final_v = img_v + txt_v + form_v + [num_of_forms]
        return final_v
    except Exception as e:
        with open("/tmp/error.log", "a", encoding="utf-8") as log:
            log.write("❌ Falla en feature_vector_extraction_from_img_html: " + str(e) + "\n")
        return None

# ✅ FUNCIÓN IMPORTABLE POR predict_crawl.py
def extract_feature_vector(img_path, html_path):
    """
    Wrapper para compatibilidad con predict_crawl.py
    """
    return feature_vector_extraction_from_img_html(img_path, html_path)
