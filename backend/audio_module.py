from pathlib import Path
from typing import Optional
import os

class TTSModule:
    """Módulo de Síntesis de Voz (Text-to-Speech)"""
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self.audio_dir = Path(__file__).parent.parent / "data" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Intentar usar Coqui TTS (open-source)
            from TTS.api import TTS
            self.tts = TTS(model_name="tts_models/ru/cv/glow-tts", gpu=False)
            self.engine = "coqui"
        except ImportError:
            try:
                # Fallback a pyttsx3
                import pyttsx3
                self.tts = pyttsx3.init()
                self.tts.setProperty('voice', 'russian')
                self.engine = "pyttsx3"
            except:
                self.tts = None
                self.engine = None
    
    def synthesize(self, text: str, phrase_id: int) -> Optional[str]:
        """Sintetizar texto a audio"""
        if not self.tts:
            return None
        
        audio_file = self.audio_dir / f"phrase_{phrase_id}.wav"
        
        try:
            if self.engine == "coqui":
                # Usar Coqui TTS
                self.tts.tts_to_file(
                    text=text,
                    file_path=str(audio_file),
                    speaker_idx=0
                )
            elif self.engine == "pyttsx3":
                # Usar pyttsx3
                self.tts.save_to_file(text, str(audio_file))
                self.tts.runAndWait()
            
            return f"/api/audio/phrase_{phrase_id}.wav"
        except Exception as e:
            print(f"Error sintetizando audio: {e}")
            return None
    
    def batch_synthesize(self, phrases: list) -> dict:
        """Sintetizar múltiples frases"""
        results = {}
        for phrase in phrases:
            audio_url = self.synthesize(
                phrase.get("russian", ""),
                phrase.get("id")
            )
            results[phrase.get("id")] = audio_url
        return results

class STTModule:
    """Módulo de Reconocimiento de Voz (Speech-to-Text)"""
    
    def __init__(self, language: str = "ru"):
        self.language = language
        
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.engine = "speech_recognition"
        except ImportError:
            self.recognizer = None
            self.engine = None
    
    def recognize(self, audio_file: str) -> Optional[str]:
        """Reconocer voz desde archivo"""
        if not self.recognizer:
            return None
        
        try:
            with open(audio_file, "rb") as f:
                audio_data = self.recognizer.listen(f)
            
            text = self.recognizer.recognize_google(
                audio_data,
                language="ru-RU"
            )
            return text
        except Exception as e:
            print(f"Error reconociendo voz: {e}")
            return None
    
    def recognize_microphone(self, duration: int = 5) -> Optional[str]:
        """Reconocer voz desde micrófono"""
        if not self.recognizer:
            return None
        
        try:
            import pyaudio
            with pyaudio.PyAudio() as mic:
                audio_data = self.recognizer.listen(mic, timeout=duration)
            
            text = self.recognizer.recognize_google(
                audio_data,
                language="ru-RU"
            )
            return text
        except Exception as e:
            print(f"Error con micrófono: {e}")
            return None

class AudioManager:
    """Gestor centralizado de audio"""
    
    def __init__(self):
        self.tts = TTSModule(language="ru")
        self.stt = STTModule(language="ru")
    
    def generate_phrase_audio(self, phrase: dict) -> dict:
        """Generar audio para una frase"""
        audio_url = self.tts.synthesize(
            phrase.get("russian", ""),
            phrase.get("id")
        )
        
        return {
            "phrase_id": phrase.get("id"),
            "audio_url": audio_url,
            "language": "ru"
        }
    
    def process_voice_query(self, audio_file: str = None) -> Optional[str]:
        """Procesar consulta de voz"""
        if audio_file:
            return self.stt.recognize(audio_file)
        else:
            return self.stt.recognize_microphone()
