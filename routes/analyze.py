from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import fitz
import subprocess
import requests
import json
import uuid

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.image_service import extract_text_from_image
from services.groq_service import ask_llm
from services.pinecone_service import save_to_pinecone, clean_id
from services.neo4j_service import save_to_neo4j
from services.whisper_service import audio_model
from models.request_models import AnalysisRequest

router = APIRouter()

FFMPEG_EXE_PATH = r"E:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"


# ==================================================
# UTF8 RESPONSE
# ==================================================

def utf8_response(data: dict, code: int = 200):
    return JSONResponse(
        status_code=code,
        content=data,
        media_type="application/json; charset=utf-8"
    )


# ==================================================
# MODELS
# ==================================================

class PatientQuestion(BaseModel):
    patient_id: str
    question: str
    patient_data: dict


# ==================================================
# PROMPT
# ==================================================

def medical_text_prompt(text: str) -> str:
    return f"""
أنت نظام طبي ذكي متقدم (Clinical Decision Support AI).

🎯 الهدف:
مساعدة المستخدم طبيًا بطريقة محترمة ودقيقة، سواء كانت رسالته طبية أو غير طبية.

────────────────────────
🧠 قواعد الفهم:
- إذا كانت الرسالة تحية أو كلام عام (مثل: مرحبا، كيف حالك):
  → رد بلطف + اسأل عن الأعراض أو الحالة الصحية

- إذا كانت الرسالة تحتوي أعراض أو معلومات طبية:
  → قم بتحليل طبي احترافي

────────────────────────
⚠️ قيود صارمة:
- لا تقدم تشخيص نهائي
- لا تضمن أي مرض بنسبة 100%
- لا تخرج عن المجال الطبي في الحالات الصحية
- لا تهمل أي عرض مذكور

────────────────────────
🏥 عند وجود أعراض، يجب إعطاء:

1) 🔍 تحليل طبي محتمل (Differential analysis)
2) 🤒 الأعراض المرتبطة
3) 🧪 الفحوصات المقترحة:
   - تحاليل دم (CBC, CRP, …)
   - تصوير (Scanner / IRM / Radiographie) حسب الحالة
4) 👨‍⚕️ التخصص الطبي المناسب:
   - طبيب عام / باطنية / قلب / أعصاب / رئة / طوارئ...
5) 💡 نصائح أولية آمنة
6) 🚨 مستوى الخطورة:
   - منخفض / متوسط / عالي

────────────────────────
📌 الرسالة:
{text}

🩺 الرد الطبي:
"""


# ==================================================
# ASK PATIENT
# ==================================================

@router.post("/ask-patient")
async def ask_patient(data: PatientQuestion):
    try:
        prompt = f"""
بيانات المريض:
{json.dumps(data.patient_data, ensure_ascii=False)}

السؤال:
{data.question}

أجب بالعربية:
"""

        answer = ask_llm(prompt)

        save_to_neo4j(data.patient_id, data.question, answer)
        save_to_pinecone(data.patient_id, data.question, answer)

        return utf8_response({
            "answer": answer
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)


# ==================================================
# TEXT
# ==================================================

@router.post("/analyze-text")
async def analyze_text(data: dict):
    try:
        text = data.get("text", "").strip()
        patient_id = data.get("patient_id", "unknown")

        if not text:
            return utf8_response({
                "analysis": "الرسالة فارغة"
            })

        prompt = medical_text_prompt(text)

        analysis = ask_llm(prompt)

        save_to_pinecone(clean_id(patient_id), text, analysis)
        save_to_neo4j(patient_id, text, analysis)

        return utf8_response({
            "analysis": analysis
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)


# ==================================================
# IMAGE
# ==================================================

@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    temp_file = f"temp_{uuid.uuid4()}_{file.filename}"

    try:
        content = await file.read()

        with open(temp_file, "wb") as f:
            f.write(content)

        text = extract_text_from_image(temp_file).strip()

        if not text:
            return utf8_response({
                "error": "لم يتم العثور على نص"
            }, 400)

        analysis = ask_llm(medical_text_prompt(text))

        return utf8_response({
            "type": "image",
            "text": text,
            "analysis": analysis
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# ==================================================
# PDF
# ==================================================

@router.post("/analyze-pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    temp_file = f"temp_{uuid.uuid4()}_{file.filename}"

    try:
        content = await file.read()

        with open(temp_file, "wb") as f:
            f.write(content)

        doc = fitz.open(temp_file)

        text = ""
        for page in doc:
            text += page.get_text()

        doc.close()

        analysis = ask_llm(medical_text_prompt(text))

        return utf8_response({
            "type": "pdf",
            "analysis": analysis
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# Add this to your FastAPI router file

@router.post("/analyze-file")
async def analyze_file(
        file: UploadFile = File(...),
        prompt: str = "",
        patient_id: str = ""
):
    """Generic file analysis endpoint that handles different file types"""
    try:
        # Determine file type by extension
        filename = file.filename.lower()
        temp_file = f"temp_{uuid.uuid4()}_{file.filename}"

        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        text = ""

        # Check file type
        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            # Image
            text = extract_text_from_image(temp_file)

        elif filename.endswith('.pdf'):
            # PDF
            doc = fitz.open(temp_file)
            for page in doc:
                text += page.get_text()
            doc.close()

        elif filename.endswith(('.m4a', '.mp3', '.wav')):
            # Audio - transcribe with Whisper
            if audio_model:
                # Convert to wav if needed
                wav_file = f"conv_{uuid.uuid4()}.wav"
                subprocess.run([
                    FFMPEG_EXE_PATH, "-y", "-i", temp_file,
                    "-vn", "-ac", "1", "-ar", "16000", wav_file
                ], capture_output=True)

                result = audio_model.transcribe(wav_file, language="ar")
                text = result["text"].strip()
                os.remove(wav_file)
            else:
                text = "Audio transcription not available"

        # Combine with prompt if provided
        if prompt and prompt.strip():
            full_text = f"User prompt: {prompt}\n\nExtracted text from file: {text}"
        else:
            full_text = text

        if not full_text.strip():
            return utf8_response({
                "analysis": "No text could be extracted from the file"
            })

        # Analyze with LLM
        analysis = ask_llm(medical_text_prompt(full_text))

        return utf8_response({
            "analysis": analysis,
            "type": "file",
            "transcript": text[:500] if len(text) > 500 else text
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
# ==================================================
# AUDIO
# ==================================================

@router.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    if not audio_model:
        raise HTTPException(status_code=500, detail="Whisper not ready")

    uid = str(uuid.uuid4())

    temp_audio = f"temp_{uid}_{file.filename}"
    temp_wav = f"conv_{uid}.wav"

    try:
        content = await file.read()

        with open(temp_audio, "wb") as f:
            f.write(content)

        subprocess.run([
            FFMPEG_EXE_PATH,
            "-y",
            "-i", temp_audio,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            temp_wav
        ])

        result = audio_model.transcribe(
            temp_wav,
            language="ar"
        )

        transcript = result["text"].strip()

        if not transcript:
            return utf8_response({
                "analysis": "الصوت غير واضح"
            })

        analysis = ask_llm("حلل هذا النص الطبي:\n" + transcript)

        return utf8_response({
            "transcript": transcript,
            "analysis": analysis
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)

    finally:
        for f in [temp_audio, temp_wav]:
            if os.path.exists(f):
                os.remove(f)


# ==================================================
# URL
# ==================================================

@router.post("/analyze-url")
async def analyze_url(request: AnalysisRequest):
    temp_file = f"temp_{uuid.uuid4()}"

    try:
        r = requests.get(request.file_url, timeout=30)
        r.raise_for_status()

        with open(temp_file, "wb") as f:
            f.write(r.content)

        text = ""

        if request.type == "image":
            text = extract_text_from_image(temp_file)

        elif request.type == "pdf":
            doc = fitz.open(temp_file)

            for page in doc:
                text += page.get_text()

            doc.close()

        else:
            return utf8_response({
                "error": "type يجب أن يكون image أو pdf"
            }, 400)

        analysis = ask_llm("حلل هذه البيانات الطبية:\n" + text)

        return utf8_response({
            "analysis": analysis,
            "text": text[:500]
        })

    except Exception as e:
        return utf8_response({
            "error": str(e)
        }, 500)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)