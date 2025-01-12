from flask import Flask, render_template, request, redirect, url_for
import sounddevice as sd
from scipy.io.wavfile import write
import os
import requests
from datetime import datetime
import speech_recognition as sr

app = Flask(__name__)

def klasor_olustur():
    """Gerekli klasörleri oluştur (eğer yoksa)"""
    if not os.path.exists("recordings"):
        os.makedirs("recordings")
    if not os.path.exists("transcripts"):
        os.makedirs("transcripts")

class SesKaydedici:
    def __init__(self):
        self.kayit_devam = False
        self.ses_parcalari = []

    def kayit_baslat(self, seconds=5, samplerate=44100):
        """Kaydı başlat ve ses kaydını depola"""
        self.kayit_devam = True
        self.ses_parcalari = []
        self.seconds = seconds
        self.samplerate = samplerate

        try:
            # Kaydı başlatıyoruz
            self.ses_parcalari = sd.rec(int(self.seconds * self.samplerate), samplerate=self.samplerate, channels=1, dtype='int16')
            sd.wait()  # Kaydın bitmesini bekler
        except Exception as e:
            raise Exception("Mikrofon bulunamadı veya erişilemedi: " + str(e))

    def kayit_durdur(self):
        """Kaydı durdur ve döndür"""
        return self.ses_parcalari, self.samplerate


def ses_kaydet_dosyaya(ses_parcalari, ornek_hizi):
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_adi = f"recordings/recording_{zaman_damgasi}.wav"
    write(dosya_adi, ornek_hizi, ses_parcalari)
    return dosya_adi


def sesi_yaziya_cevir(ses_dosyasi):
    taniyici = sr.Recognizer()

    try:
        with sr.AudioFile(ses_dosyasi) as kaynak:
            ses = taniyici.record(kaynak)
        return taniyici.recognize_google(ses, language="tr-TR")
    except sr.UnknownValueError:
        return "Konuşma anlaşılamadı"
    except sr.RequestError:
        return "API servisine erişilemedi"
    except Exception as e:
        return f"Hata oluştu: {str(e)}"


def metni_kaydet(metin):
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_adi = f"transcripts/transcript_{zaman_damgasi}.txt"

    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write(metin)
    return dosya_adi


def metni_webhooka_gonder(webhook_url, metin):
    try:
        response = requests.post(webhook_url, json={"transcript": metin})
        if response.status_code == 200:
            return "Veri başarılı bir şekilde webhook'a gönderildi!"
        else:
            return f"Webhook isteği başarısız: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Webhook gönderimi sırasında bir hata oluştu: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        webhook_url = request.form.get("webhook_url")
        seconds = int(request.form.get("duration"))

        kaydedici = SesKaydedici()
        kaydedici.kayit_baslat(seconds=seconds)
        ses_parcalari, ornek_hizi = kaydedici.kayit_durdur()

        # Sesi dosyaya kaydet
        ses_dosyasi = ses_kaydet_dosyaya(ses_parcalari, ornek_hizi)

        # Sesi yazıya çevir
        metin = sesi_yaziya_cevir(ses_dosyasi)

        # Metni kaydet
        metin_dosyasi = metni_kaydet(metin)

        # Webhook'a gönder
        if webhook_url:
            webhook_mesaji = metni_webhooka_gonder(webhook_url, metin)
        else:
            webhook_mesaji = "Webhook URL girilmemiş!"

        return render_template("index.html", ses_dosyasi=ses_dosyasi, metin=metin, metin_dosyasi=metin_dosyasi, webhook_mesaji=webhook_mesaji)

    return render_template("index.html", ses_dosyasi=None, metin=None, metin_dosyasi=None, webhook_mesaji=None)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
