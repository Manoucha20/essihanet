import os
import re
import uuid
from dotenv import load_dotenv

load_dotenv()

index = None
model = None

try:
    from pinecone import Pinecone, ServerlessSpec
    from sentence_transformers import SentenceTransformer

    PINECONE_KEY = os.getenv("PINECONE_KEY")
    INDEX_NAME = os.getenv("INDEX_NAME", "default_index")

    if PINECONE_KEY:
        pc = Pinecone(api_key=PINECONE_KEY)
        # التأكد من وجود الفهرس (Index)
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if INDEX_NAME not in existing_indexes:
            pc.create_index(
                name=INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

        index = pc.Index(INDEX_NAME)
        # تحميل الموديل لتحويل النص إلى Vector
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Pinecone initialized.")
    else:
        print("⚠️ PINECONE_KEY missing.")
except Exception as e:
    print(f"⚠️ Pinecone Error: {e}")


def clean_id(text: str):
    """تنظيف المعرف ليكون ASCII فقط كما تطلب Pinecone"""
    if not text:
        return str(uuid.uuid4())[:8]
    # حذف أي رموز غير مدعومة واستبدالها بشرطة سفلية
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    return text if text else str(uuid.uuid4())[:8]


def save_to_pinecone(file_id, text, analysis=None):
    if index and text and file_id:
        try:
            safe_id = clean_id(file_id)

            vector = model.encode(text).tolist()

            metadata = {
                "content": text
            }

            # إذا كاين تحليل زيدو
            if analysis:
                metadata["analysis"] = analysis

            index.upsert([
                {
                    "id": safe_id,
                    "values": vector,
                    "metadata": metadata
                }
            ])

            print(f"✅ Saved to Pinecone: {safe_id}")
            return True

        except Exception as e:
            print(f"❌ Pinecone Upsert Error: {e}")
            return False

    return False