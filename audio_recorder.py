import streamlit as st
from datetime import datetime
import os
import requests
import speech_recognition as sr
from io import BytesIO
import soundfile as sf
from audio_recorder_streamlit import audio_recorder

def create_folders():
    """Create necessary folders if they don't exist"""
    if not os.path.exists("recordings"):
        os.makedirs("recordings")
    if not os.path.exists("transcripts"):
        os.makedirs("transcripts")

def save_audio(audio_bytes):
    """Save audio bytes to a WAV file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recordings/recording_{timestamp}.wav"
    
    # Convert audio bytes to WAV format
    audio_segment = BytesIO(audio_bytes)
    data, samplerate = sf.read(audio_segment)
    sf.write(filename, data, samplerate)
    
    return filename

def transcribe_audio(audio_file):
    """Convert speech to text using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="tr-TR")
    except sr.UnknownValueError:
        return "Konuşma anlaşılamadı"
    except sr.RequestError:
        return "API servisine erişilemedi"
    except Exception as e:
        return f"Hata oluştu: {str(e)}"

def save_transcript(text):
    """Save transcript to a file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcripts/transcript_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename

def send_to_webhook(webhook_url, text):
    """Send text to webhook"""
    try:
        response = requests.post(webhook_url, json={"transcript": text})
        if response.status_code == 200:
            return "Veri başarılı bir şekilde webhook'a gönderildi!"
        else:
            return f"Webhook isteği başarısız: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Webhook gönderimi sırasında bir hata oluştu: {str(e)}"

def main():
    st.title("Web Tabanlı Ses Kaydedici ve Yazıya Dönüştürücü")
    
    create_folders()
    
    # Initialize session states if they don't exist
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'audio_bytes' not in st.session_state:
        st.session_state.audio_bytes = None
    
    # Webhook URL input in sidebar
    st.sidebar.title("Ayarlar")
    webhook_url = st.sidebar.text_input("Webhook URL'si", placeholder="Webhook URL giriniz")
    
    # Check if webhook URL is provided
    if not webhook_url:
        st.warning("Lütfen önce geçerli bir Webhook URL'si girin!")
        return
    
    # Hidden audio recorder
    if st.session_state.recording:
        audio_bytes = audio_recorder(key="hidden_recorder")
        if audio_bytes:
            st.session_state.audio_bytes = audio_bytes
    
    # Create two columns for buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Show Start button only if not recording
        if not st.session_state.recording:
            if st.button("Kayıt Başlat", type="primary"):
                st.session_state.recording = True
    
    with col2:
        # Show Stop button only if recording
        if st.session_state.recording:
            if st.button("Kayıt Durdur", type="secondary"):
                st.session_state.recording = False
                if st.session_state.audio_bytes:
                    with st.spinner("Ses işleniyor..."):
                        # Save audio to file
                        audio_file = save_audio(st.session_state.audio_bytes)
                        st.success(f"Ses kaydedildi: {audio_file}")
                        
                        # Transcribe audio
                        text = transcribe_audio(audio_file)
                        st.write("Yazıya dönüştürülen metin:")
                        st.write(text)
                        
                        # Save transcript
                        transcript_file = save_transcript(text)
                        st.success(f"Yazıya dönüştürüldü ve kaydedildi: {transcript_file}")
                        
                        # Send to webhook
                        st.info("Webhook'a veri gönderiliyor...")
                        webhook_message = send_to_webhook(webhook_url, text)
                        st.write(webhook_message)
                        
                        # Reset audio bytes
                        st.session_state.audio_bytes = None
    
    # Show recording status
    if st.session_state.recording:
        st.write("🔴 Kayıt yapılıyor...")
        st.write("Kaydı durdurmak için 'Kayıt Durdur' butonuna basın.")

if __name__ == "__main__":
    main()
