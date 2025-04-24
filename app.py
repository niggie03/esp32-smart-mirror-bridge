import os
import sys
import base64
import requests
import random        # Für Übergangssätze
from flask import Flask, request, send_file, jsonify        # Framework für REST-API
import openai        # Whisper und OpenAI
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)

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

# Überleitungssätze einbinden
def generate_thinking_audio():
    if GOOGLE_TTS_API:
        print("Erzeuge Thinking-Audio...")
        sys.stdout.flush()

        # Texte
        thinking_texts = [
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
            "Ein Moment bitte – ich poliere meine Gedanken für dich auf Hochglanz...",
            "Ich reflektiere... im wahrsten Sinne des Wortes... Sekunde noch!",
            "Hm... ich frage mein glänzendes Unterbewusstsein...",
            "Ich tippe gerade mit meinen Pixeln... gleich fertig!",
            "Verbindung zur Spiegel-Cloud wird aufgebaut... bitte warte...",
            "WLAN stabil... Rechenleistung läuft... Antwort im Anflug...",
            "Ich filtere reflektierte Daten... gleich leuchte ich dir den Weg...",
            "Glasfaser durchspiegelt... Töne moduliert... gleich gibt’s Output...",
            "Ich scanne die Realität... sie braucht noch einen Moment, um zu laden...",
            "Spieglein, Spieglein... ich durchsuche gerade meine silberne Tiefe nach einer Antwort...",
            "Ich blicke in die magischen Reflexionen der Wahrheit... einen Moment...",
            "Deine Frage hallt durch die Spiegelwelten... gleich finde ich, was du suchst...",
            "Ich berate mich mit meinem inneren Orakel... bitte einen kleinen Moment Geduld...",
            "Die Antwort zieht Nebelspuren auf meiner Oberfläche... ich bringe Klarheit...",
            "Während ich nachdenke... bewundere ruhig dein großartiges Spiegelbild...",
            "Ein Moment bitte – ich poliere meine Gedanken für dich auf Hochglanz...",
            "Ich reflektiere... im wahrsten Sinne des Wortes... Sekunde noch!",
            "Hm... ich frage mein glänzendes Unterbewusstsein...",
            "Ich tippe gerade mit meinen Pixeln... gleich fertig!",
            "Verbindung zur Spiegel-Cloud wird aufgebaut... bitte warte...",
            "WLAN stabil... Rechenleistung läuft... Antwort im Anflug...",
            "Ich filtere reflektierte Daten... gleich leuchte ich dir den Weg...",
            "Glasfaser durchspiegelt... Töne moduliert... gleich gibt’s Output...",
            "Ich scanne die Realität... sie braucht noch einen Moment, um zu laden...",
            "Ich kann dir keine Schönheit schenken… aber eine gute Antwort vielleicht."
        ]

        # random auswählen
        thinking_text = random.choice(thinking_texts)

        # Anfrage an Google TTS API für die Übergangssätze 
        tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "input": {"text": thinking_text},
            "voice": {
                "languageCode": "de-DE",
                "name": "de-DE-Standard-B"        # language Model
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "speakingRate": 1.2,
                "pitch": 1.5,
                "sampleRateHertz": 22050
            }
        }

        # Anfrage senden und Antwort verarbeiten
        response = requests.post(tts_url, headers=headers, json=payload).json()

        if "audioContent" in response:
            audio_data = response["audioContent"]
            with open("static/thinking.wav", "wb") as out:
                out.write(base64.b64decode(audio_data))
            print("Thinking-Audio gespeichert.")
        else:
            print("Keine Thinking-TTS-Antwort.")
        sys.stdout.flush()

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
        sys.stdout.flush

        # Übergangsantwort vorbereiten (geschmeidiger Übergang)
        generate_thinking_audio()
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

        # Antwort von ChatGPT
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", "content": 
                "content": f"Beantworte die folgende Frage in höchstens drei Sätzen: {prompt}
                }]
        )
        answer = completion.choices[0].message.content        # Antwort speichern
        
        # GPT soll prüfen, ob Folgefrage sinnvoll wäre
        followup_check = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system","content": "Du bist ein strenger Filter, der nur mit JA antwortet, wenn eine Rückfrage ausdrücklich erwartet wird – z. B. durch ein Fragezeichen, eine Einladung zur Reaktion oder wenn der Satz offen endet."},
                {"role": "user", "content": f"Ist folgende Antwort eine, auf die man sinnvoll antworten oder eine Rückfrage stellen würde?\n\n\"{answer}\"\n\nAntworte ausschließlich mit JA oder NEIN."}
            ]
        )
        
        followup_raw = followup_check.choices[0].message.content.strip().lower()        # Antwort für Follow up schreiben
        needs_followup = "ja" in followup_raw

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
            
            # Google TTS mit GPT Antwort
            tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "input": {"text": answer},
                "voice": {
                    "languageCode": "de-DE",
                    "name": "de-DE-Standard-B"        # Language Model
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
                audio_data = response["audioContent"]
                with open(RESPONSE_FILE, "wb") as out:
                    out.write(base64.b64decode(audio_data))
                print("TTS erfolgreich. Antwort gespeichert.")
            else:
                raise Exception("Google TTS did not return audioContent.")
        else:
            with open(RESPONSE_FILE, "wb") as out:
                out.write(b"")
            print("Kein GOOGLE_TTS_API – leere Datei.")
        sys.stdout.flush()
    except Exception as e:
        print(f"TTS-Fehler: {e}")
        sys.stdout.flush()
        return jsonify({"error": f"Google TTS failed: {str(e)}"}), 500

    return jsonify({    # Ergebnis zurückgeben
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
