import streamlit as st
from datetime import datetime
import os
import requests
import speech_recognition as sr
import sounddevice as sd
import numpy as np
import wave
import threading
import queue

def create_folders():
    if not os.path.exists("recordings"):
        os.makedirs("recordings")
    if not os.path.exists("transcripts"):
        os.makedirs("transcripts")

class AudioRecorder:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.recording = False
        self.sample_rate = 44100
        self.channels = 1
        
    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            self.audio_queue.put(indata.copy())
    
    def start_recording(self):
        self.recording = True
        self.audio_queue.queue.clear()
        self.stream = sd.InputStream(
            channels=self.channels,
            samplerate=self.sample_rate,
            callback=self.callback
        )
        self.stream.start()
    
    def stop_recording(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()
        
        # Collect all audio data
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())
            
        if not audio_data:
            return None
            
        # Combine all chunks
        audio_data = np.concatenate(audio_data, axis=0)
        return audio_data, self.sample_rate

def save_audio(audio_data, sample_rate):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recordings/recording_{timestamp}.wav"
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    
    return filename

def transcribe_audio(audio_file):
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcripts/transcript_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename

def send_to_webhook(webhook_url, text):
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
    
    # Initialize session states
    if 'recorder' not in st.session_state:
        st.session_state.recorder = AudioRecorder()
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    
    # Webhook URL input in sidebar
    st.sidebar.title("Ayarlar")
    webhook_url = st.sidebar.text_input("Webhook URL'si", placeholder="Webhook URL giriniz")
    
    if not webhook_url:
        st.warning("Lütfen önce geçerli bir Webhook URL'si girin!")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.recording:
            if st.button("Kayıt Başlat", type="primary"):
                st.session_state.recording = True
                st.session_state.recorder.start_recording()
                st.experimental_rerun()
    
    with col2:
        if st.session_state.recording:
            if st.button("Kayıt Durdur", type="secondary"):
                st.session_state.recording = False
                result = st.session_state.recorder.stop_recording()
                
                if result:
                    audio_data, sample_rate = result
                    with st.spinner("Ses işleniyor..."):
                        # Save audio
                        audio_file = save_audio(audio_data, sample_rate)
                        st.success(f"Ses kaydedildi: {audio_file}")
                        
                        # Transcribe
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
                
                st.experimental_rerun()
    
    if st.session_state.recording:
        st.write("🔴 Kayıt yapılıyor...")
        st.write("Kaydı durdurmak için 'Kayıt Durdur' butonuna basın.")

if __name__ == "__main__":
    main()