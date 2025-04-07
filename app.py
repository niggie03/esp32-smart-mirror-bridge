os.makedirs("static", exist_ok=True)
from flask import Flask, request, send_file, jsonify
import openai
import os
import uuid
import requests
import base64  # ⬅️ Das ist neu

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_TTS_API = os.environ.get("GOOGLE_TTS_API")  # optional

openai.api_key = OPENAI_API_KEY
AUDIO_FILE = "record.wav"
RESPONSE_FILE = "static/response.wav"

@app.route("/")
def index():
    return "✅ ESP32 Smart Mirror Bridge is online"

@app.route("/upload", methods=["POST"])
def upload():
    with open("record.wav", "wb") as f:
        f.write(request.data)
    return jsonify({"status": "upload ok"})  # ← Nur 1x!

@app.route("/process", methods=["GET"])
def process():
    # Whisper: Neue API
    with open(AUDIO_FILE, "rb") as f:
        response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    prompt = response.text

    # GPT
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    answer = completion.choices[0].message.content

    # Google TTS
    if GOOGLE_TTS_API:
        tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "input": {"text": answer},
            "voice": {"languageCode": "en-US", "name": "en-US-Wavenet-D"},
            "audioConfig": {"audioEncoding": "LINEAR16"}
        }
        response = requests.post(tts_url, headers=headers, json=payload).json()
        audio_data = response["audioContent"]

        with open(RESPONSE_FILE, "wb") as out:
            out.write(base64.b64decode(audio_data))
    else:
        with open(RESPONSE_FILE, "wb") as out:
            out.write(b"")

    return jsonify({"text": answer})


@app.route("/text", methods=["GET"])
def last_text():
    return jsonify({"status": "ready"})

@app.route("/response.wav", methods=["GET"])
def get_audio():
    return send_file(RESPONSE_FILE, mimetype="audio/wav")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
