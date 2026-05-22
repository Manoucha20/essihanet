import whisper

audio_model = None

try:
    print("Loading Whisper model...")
    audio_model = whisper.load_model("base")
    print("✅ Whisper loaded")
except Exception as e:
    print(f"⚠️ Whisper Error: {e}")