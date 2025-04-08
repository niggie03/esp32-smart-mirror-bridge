import os
from flask import Flask, request, send_file, jsonify
import openai
import uuid
import requests
import base64

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_TTS_API = os.environ.get("GOOGLE_TTS_API")  # optional

openai.api_key = OPENAI_API_KEY
AUDIO_FILE = "record.wav"
RESPONSE_FILE = "static/response.wav"
print("📦 OpenAI-Version:", openai.__version__)
# Create the 'static' folder if it doesn't exist
if not os.path.exists("static"):
    os.makedirs("static")

@app.route("/")
def index():
    return "✅ ESP32 Smart Mirror Bridge is online"

@app.route("/upload", methods=["POST"])
def upload():
    with open(AUDIO_FILE, "wb") as f:
        f.write(request.data)
    return jsonify({"status": "upload ok"})

@app.route("/process", methods=["GET"])
def process():
    try:
        print("📥 Starte Whisper-Verarbeitung...")
        with open(AUDIO_FILE, "rb") as f:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        prompt = transcription.text
        print(f"📝 Transkription: {prompt}")
    except Exception as e:
        print(f"❌ Whisper-Fehler: {e}")
        return jsonify({"error": f"Whisper failed: {str(e)}"}), 500

    try:
        print("💬 Frage an ChatGPT...")
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = completion.choices[0].message.content
        print(f"🤖 GPT-Antwort: {answer}")
    except Exception as e:
        print(f"❌ GPT-Fehler: {e}")
        return jsonify({"error": f"GPT failed: {str(e)}"}), 500

    try:
        print("🗣 Starte TTS...")
        if GOOGLE_TTS_API:
            tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "input": {"text": answer},
                "voice": {"languageCode": "en-US", "name": "en-US-Wavenet-D"},
                "audioConfig": {"audioEncoding": "LINEAR16"}
            }
            response = requests.post(tts_url, headers=headers, json=payload).json()

            if "audioContent" in response:
                audio_data = response["audioContent"]
                with open(RESPONSE_FILE, "wb") as out:
                    out.write(base64.b64decode(audio_data))
                print("✅ TTS erfolgreich.")
            else:
                raise Exception("Google TTS did not return audioContent.")
        else:
            with open(RESPONSE_FILE, "wb") as out:
                out.write(b"")
            print("⚠️ Kein Google TTS API-Key – Stille erzeugt.")
    except Exception as e:
        print(f"❌ TTS-Fehler: {e}")
        return jsonify({"error": f"Google TTS failed: {str(e)}"}), 500

    return jsonify({"text": answer})


@app.route("/text", methods=["GET"])
def last_text():
    return jsonify({"status": "ready"})

@app.route("/response.wav", methods=["GET"])
def get_audio():
    if os.path.exists(RESPONSE_FILE):
        return send_file(RESPONSE_FILE, mimetype="audio/wav")
    else:
        return jsonify({"error": "No audio response found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
