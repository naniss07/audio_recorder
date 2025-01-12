import streamlit as st
import pyaudio
import wave
import speech_recognition as sr
from datetime import datetime
import os
import threading
import requests

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
        self.p = None
        self.stream = None

    def kayit_baslat(self, chunk=1024, ornek_format=pyaudio.paInt16, kanal=1, ornek_hizi=44100):
        self.kayit_devam = True
        self.ses_parcalari = []

        self.p = pyaudio.PyAudio()
        varsayilan_mikrofon = self.p.get_default_input_device_info()
        st.write(f"Kullanılan mikrofon: {varsayilan_mikrofon['name']}")

        self.stream = self.p.open(format=ornek_format,
                                channels=kanal,
                                rate=ornek_hizi,
                                frames_per_buffer=chunk,
                                input=True)

        def kayit_dongusu():
            while self.kayit_devam:
                veri = self.stream.read(chunk)
                self.ses_parcalari.append(veri)

        self.kayit_thread = threading.Thread(target=kayit_dongusu)
        self.kayit_thread.start()

    def kayit_durdur(self):
        self.kayit_devam = False
        if self.kayit_thread:
            self.kayit_thread.join()

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        if self.p:
            self.p.terminate()

        return self.ses_parcalari, 44100  # Default örnek hızı

def ses_kaydet_dosyaya(ses_parcalari, ornek_hizi):
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_adi = f"recordings/recording_{zaman_damgasi}.wav"

    p = pyaudio.PyAudio()
    wf = wave.open(dosya_adi, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(ornek_hizi)
    wf.writeframes(b''.join(ses_parcalari))
    wf.close()
    p.terminate()

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
    """Webhook'a metni gönder"""
    try:
        response = requests.post(webhook_url, json={"transcript": metin})
        if response.status_code == 200:
            return "Veri başarılı bir şekilde webhook'a gönderildi!"
        else:
            return f"Webhook isteği başarısız: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Webhook gönderimi sırasında bir hata oluştu: {str(e)}"

def main():
    st.title("Ses Kaydedici ve Yazıya Dönüştürücü")

    klasor_olustur()

    if 'kaydedici' not in st.session_state:
        st.session_state.kaydedici = SesKaydedici()
        st.session_state.kayit_durumu = False

    # Kullanıcıdan Webhook URL'si alın
    st.sidebar.title("Ayarlar")
    webhook_url = st.sidebar.text_input("Webhook URL'si", placeholder="Webhook URL giriniz")

    # Webhook URL'sinin girilip girilmediğini kontrol edin
    if not webhook_url:
        st.warning("Lütfen önce geçerli bir Webhook URL'si girin!")
        return

    col1, col2 = st.columns(2)

    with col1:
        if not st.session_state.kayit_durumu:
            if st.button("Kayıt Başlat"):
                st.session_state.kayit_durumu = True
                st.session_state.kaydedici.kayit_baslat()
                st.success("Kayıt başladı!")

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

                    # Metni webhook'a gönder
                    st.info("Webhook'a veri gönderiliyor...")
                    webhook_mesaji = metni_webhooka_gonder(webhook_url, metin)
                    st.write(webhook_mesaji)

if __name__ == "__main__":
    main()
