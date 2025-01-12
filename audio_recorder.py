import streamlit as st
from datetime import datetime
import os
import requests
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr

def klasor_olustur():
    """Gerekli klasörleri oluştur (eğer yoksa)"""
    if not os.path.exists("recordings"):
        os.makedirs("recordings")
    if not os.path.exists("transcripts"):
        os.makedirs("transcripts")

def ses_kaydet_dosyaya(ses_parcalari):
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_adi = f"recordings/recording_{zaman_damgasi}.wav"

    with open(dosya_adi, "wb") as f:
        f.write(ses_parcalari)
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

    if 'kayit_durumu' not in st.session_state:
        st.session_state.kayit_durumu = False
        st.session_state.audio_bytes = None

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
                st.session_state.audio_bytes = None
                st.success("Kayıt başladı!")

    with col2:
        if st.session_state.kayit_durumu:
            if st.button("Kayıt Durdur"):
                st.session_state.kayit_durumu = False
                with st.spinner("Kayıt durduruluyor ve işleniyor..."):
                    # Kayıt durdurulduğunda ses kaydını al ve işleme başla
                    ses_parcalari = st.session_state.audio_bytes
                    
                    if ses_parcalari:
                        # Sesi dosyaya kaydet
                        ses_dosyasi = ses_kaydet_dosyaya(ses_parcalari)
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

    # Ses kaydı sadece "Kayıt Başlat" butonuna basıldığında yapılacak
    if st.session_state.kayit_durumu:
        audio_bytes = audio_recorder(key="audio_recorder")
        if audio_bytes:
            st.session_state.audio_bytes = audio_bytes

if __name__ == "__main__":
    main()
