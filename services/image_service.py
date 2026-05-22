import pytesseract
from PIL import Image
import cv2
import os

# تأكد أن Tesseract مثبت في هذا المسار
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(path: str):
    img = cv2.imread(path)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    return thresh

def extract_text_from_image(path: str):
    try:
        processed = preprocess_image(path)
        if processed is None: return ""
        # دعم العربية والإنجليزية
        text = pytesseract.image_to_string(processed, lang='eng+ara')
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""