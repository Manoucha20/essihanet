# 1. استخدام نسخة بايثون رسمية ومستقرة
FROM python:3.10-slim

# 2. تحديث النظام وتثبيت أداة Tesseract OCR الأساسية مع الحزم اللغوية
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 3. تحديد مجلد العمل داخل السيرفر
WORKDIR /app

# 4. نسخ ملف المكتبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. نسخ بقية ملفات المشروع إلى السيرفر
COPY . .

# 6. تحديد المنفذ الافتراضي وتشغيل FastAPI عبر Uvicorn
ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
