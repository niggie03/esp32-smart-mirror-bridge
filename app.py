import os
import sys
import json
import base64
import shutil
import requests
import random        # Für Übergangssätze
from flask import Flask, request, send_file, jsonify        # Framework für REST-API
import openai        # Whisper und OpenAI
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
THINKING_VARIANTS_DIR = "static/thinking_variants"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_TTS_API = os.environ.get("GOOGLE_TTS_API")

openai.api_key = OPENAI_API_KEY

# Dateipfade
AUDIO_FILE = "record.wav"
RESPONSE_FILE = "static/response.wav"
THINKING_FILE = "static/thinking.wav"

# existiert Static?
if os.path.exists("static") and not os.path.isdir("static"):
    os.remove("static")        # entfernen falls doppelt
if not os.path.exists("static"):
    os.makedirs("static")      # erstellen

# Texte fuer die Uebergangsaudios
THINKING_TEXTS = [
    "Einen Moment bitte... ich denke kurz nach... das ist eine interessante Frage...",
    "Hm... einen Augenblick... ich analysiere gerade die Informationen...",
    "Okay... das muss ich mir genauer überlegen... gleich hab ich was für dich...",
    "Ahh... gib mir kurz Zeit... ich formuliere eine passende Antwort...",
    "Oh, da muss ich mal kurz nachdenken... das dauert einen kleinen Moment...",
    "Spieglein, Spieglein... ich durchsuche gerade meine silberne Tiefe nach einer Antwort...",
    "Ich blicke in die magischen Reflexionen der Wahrheit... einen Moment...",
    "Deine Frage hallt durch die Spiegelwelten... gleich finde ich, was du suchst...",
    "Ich berate mich mit meinem inneren Orakel... bitte einen kleinen Moment Geduld...",
    "Die Antwort zieht Nebelspuren auf meiner Oberfläche... ich bringe Klarheit...",
    "Während ich nachdenke... bewundere ruhig dein großartiges Spiegelbild...",
    "Ein Moment bitte, ich poliere meine Gedanken für dich auf Hochglanz...",
    "Ich reflektiere... im wahrsten Sinne des Wortes... Sekunde noch!",
    "Hm... ich frage mein glänzendes Unterbewusstsein...",
    "Ich tippe gerade mit meinen Pixeln... gleich fertig!",
    "Verbindung zur Spiegel-Cloud wird aufgebaut... bitte warte...",
    "WLAN stabil... Rechenleistung läuft... Antwort im Anflug...",
    "Ich filtere reflektierte Daten... gleich leuchte ich dir den Weg...",
    "Glasfaser durchspiegelt... Töne moduliert... gleich gibt's Output...",
    "Ich scanne die Realität... sie braucht noch einen Moment, um zu laden...",
    "Ich kann dir keine Schönheit schenken, aber eine gute Antwort vielleicht."
]

# Generische Google-TTS-Hilfsfunktion
def synthesize_tts(text, out_path):
    tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": "de-DE",
            "name": "de-DE-Standard-B"
        },
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "speakingRate": 1.2,
            "pitch": 1.5,
            "sampleRateHertz": 22050
        }
    }
    response = requests.post(tts_url, headers=headers, json=payload).json()
    if "audioContent" in response:
        with open(out_path, "wb") as out:
            out.write(base64.b64decode(response["audioContent"]))
        return True
    return False

# Uebergangsaudios einmalig vorab generieren (statt bei jedem Upload live bei Google TTS anzufragen)
def pregenerate_thinking_variants():
    if not GOOGLE_TTS_API:
        return
    os.makedirs(THINKING_VARIANTS_DIR, exist_ok=True)
    for i, text in enumerate(THINKING_TEXTS):
        out_path = os.path.join(THINKING_VARIANTS_DIR, f"{i}.wav")
        if not os.path.exists(out_path):
            print(f"Generiere Thinking-Variante {i}...")
            sys.stdout.flush()
            synthesize_tts(text, out_path)

# Schnelle Auswahl einer vorab generierten Variante statt live TTS
def pick_thinking_audio():
    variants = [f for f in os.listdir(THINKING_VARIANTS_DIR) if f.endswith(".wav")] if os.path.isdir(THINKING_VARIANTS_DIR) else []
    if variants:
        shutil.copyfile(os.path.join(THINKING_VARIANTS_DIR, random.choice(variants)), THINKING_FILE)
        print("Thinking-Audio ausgewaehlt.")
    else:
        print("Keine Thinking-Varianten vorhanden.")
    sys.stdout.flush()

pregenerate_thinking_variants()

# Allgemeine Statusanzeige
@app.route("/")
def index():
    return "ESP32 Smart Mirror Bridge is online"

# Upload Funktion
@app.route("/upload", methods=["POST"])
def upload():
    try:
        # WAV Datei speichern
        with open(AUDIO_FILE, "wb") as f:
            f.write(request.data)
        print("Audio-Datei empfangen.")
        sys.stdout.flush()

        # Übergangsantwort vorbereiten (geschmeidiger Übergang) - keine Live-TTS mehr, nur Dateiauswahl
        pick_thinking_audio()
        return jsonify({"status": "upload ok"})
    except Exception as e:
        print(f"Fehler beim Upload: {e}")
        sys.stdout.flush()
        return jsonify({"error": str(e)}), 500

# Hauptverarbeitung
@app.route("/process", methods=["GET"])
def process():
    try:
        print("Starte Whisper...")
        sys.stdout.flush()

        #Transkription mit Whisper
        with open(AUDIO_FILE, "rb") as f:
            transcription = openai.audio.transcriptions.create(        # STT starten
                model="whisper-1",
                file=f
            )
        prompt = transcription.text
        print(f"Transkription: {prompt}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Whisper-Fehler: {e}")
        sys.stdout.flush()
        return jsonify({"error": f"Whisper failed: {str(e)}"}), 500

    try:
        print("GPT wird gefragt...")
        sys.stdout.flush()

        # Antwort + Folgefrage-Einschaetzung in einem einzigen GPT-Call (JSON-Modus)
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "Du bist ein sprechender Spiegel. Beantworte die Frage des Nutzers in hoechstens 3 Saetzen. "
                    "Haeng keine pauschale Abschlussfloskel an wie 'Kann ich sonst noch etwas fuer dich tun?' oder 'Hast du noch weitere Fragen?'. "
                    "Entscheide zusaetzlich anhand von BEIDEM - der Eingabe des Nutzers UND deiner eigenen Antwort - ob eine Rueckfrage sinnvoll ist. "
                    "followup=true NUR wenn die Eingabe des Nutzers erkennbar unvollstaendig/mehrdeutig war oder deine Antwort inhaltlich eine Praezisierung braucht. "
                    "followup=false bei Verabschiedungen, Dank, abgeschlossenen Aussagen, Smalltalk-Enden oder wenn die Eingabe unverstaendlich/leer war - auch wenn deine Antwort zufaellig mit einem Fragezeichen endet. "
                    "Antworte ausschliesslich als JSON-Objekt mit den Feldern answer (string) und followup (bool)."
                )},
                {"role": "user", "content": prompt}
            ]
        )
        result = json.loads(completion.choices[0].message.content)
        answer = result.get("answer", "")
        needs_followup = bool(result.get("followup", False))

        print(f"GPT-Antwort: {answer}")
        sys.stdout.flush()
    except Exception as e:
        print(f"GPT-Fehler: {e}")
        sys.stdout.flush()
        return jsonify({"error": f"GPT failed: {str(e)}"}), 500

    try:
        print("Starte TTS...")
        sys.stdout.flush()
        if GOOGLE_TTS_API:
            if not synthesize_tts(answer, RESPONSE_FILE):
                raise Exception("Google TTS did not return audioContent.")
            print("TTS erfolgreich. Antwort gespeichert.")
        else:
            with open(RESPONSE_FILE, "wb") as out:
                out.write(b"")
            print("Kein GOOGLE_TTS_API - leere Datei.")
        sys.stdout.flush()
    except Exception as e:
        print(f"TTS-Fehler: {e}")
        sys.stdout.flush()
        return jsonify({"error": f"Google TTS failed: {str(e)}"}), 500

    return jsonify({    # Ergebnis zurueckgeben
        "text": answer,
        "followup": needs_followup
    })


# Übergangsaudio
@app.route("/thinking.wav", methods=["GET"])
def get_thinking():
    if os.path.exists(THINKING_FILE):
        return send_file(THINKING_FILE, mimetype="audio/wav")
    else:
        return jsonify({"error": "No thinking audio found."}), 404

# Antwort Audio
@app.route("/response.wav", methods=["GET"])
def get_audio():
    if os.path.exists(RESPONSE_FILE):
        return send_file(RESPONSE_FILE, mimetype="audio/wav")
    else:
        return jsonify({"error": "No audio response found."}), 404

# Einstiegspunkt
if __name__ == "__main__":
    print("OpenAI-Version:", openai.__version__)
    sys.stdout.flush()
    app.run(host="0.0.0.0", port=5000)
