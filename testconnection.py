import requests

try:
    r = requests.get("https://api.dr7.ai/v1/chat/completions")
    print("نجح الاتصال", r.status_code)
except Exception as e:
    print("فشل الاتصال:", e)