import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
import os
import threading
import requests
from datetime import datetime
import numpy as np
import wave
import speech_recognition as sr

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


def main():
    st.title("Ses Kaydedici ve Yazıya Dönüştürücü")
    WEBHOOK_URL = st.text_input("Webhook URL'nizi buraya girin:", "https://webhook.site/your-url")

    klasor_olustur()

    if 'kaydedici' not in st.session_state:
        st.session_state.kaydedici = SesKaydedici()
        st.session_state.kayit_durumu = False

    col1, col2 = st.columns(2)

    with col1:
        if not st.session_state.kayit_durumu:
            if st.button("Kayıt Başlat"):
                try:
                    st.session_state.kayit_durumu = True
                    with st.spinner("Kaydınız başlıyor..."):
                        st.session_state.kaydedici.kayit_baslat()
                        st.success("Kayıt başladı!")
                except Exception as e:
                    st.error(f"Hata: {str(e)}")

    with col2:
        if st.session_state.kayit_durumu:
            if st.button("Kayıt Durdur"):
                st.session_state.kayit_durumu = False
                with st.spinner("Kayıt durduruluyor ve işleniyor..."):
                    ses_parcalari, ornek_hizi = st.session_state.kaydedici.kayit_durdur()

                    # Sesi dosyaya kaydet
                    ses_dosyasi = ses_kaydet_dosyaya(ses_parcalari, ornek_hizi)
                    st.success(f"Ses kaydedildi: {ses_dosyasi}")

                    # Sesi yazıya çevir
                    metin = sesi_yaziya_cevir(ses_dosyasi)
                    st.write("Yazıya dönüştürülen metin:")
                    st.write(metin)

                    # Metni dosyaya kaydet
                    metin_dosyasi = metni_kaydet(metin)
                    st.success(f"Yazıya dönüştürüldü ve kaydedildi: {metin_dosyasi}")
                    
                    # Webhook'a gönder
                    if WEBHOOK_URL:
                        st.info("Webhook'a veri gönderiliyor...")
                        webhook_mesaji = metni_webhooka_gonder(WEBHOOK_URL, metin)
                        st.write(webhook_mesaji)
                    else:
                        st.warning("Webhook URL'i girilmemiş!")

# Webhook'a gönderim fonksiyonu
def metni_webhooka_gonder(webhook_url, metin):
    try:
        response = requests.post(webhook_url, json={"transcript": metin})
        if response.status_code == 200:
            return "Veri başarılı bir şekilde webhook'a gönderildi!"
        else:
            return f"Webhook isteği başarısız: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Webhook gönderimi sırasında bir hata oluştu: {str(e)}"


if __name__ == "__main__":
    main()
