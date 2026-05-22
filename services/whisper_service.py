import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(audio_file_path):
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(audio_file_path, audio_file.read()),
                model="whisper-large-v3",
                language="ar"
            )
        return transcription.text
    except Exception as e:
        print(f"Whisper API Error: {e}")
        return None

audio_model = None
print("✅ Whisper service ready (using Groq API)")
