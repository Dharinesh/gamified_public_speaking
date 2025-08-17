import os
import requests
import time
import logging
from config import Config
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class TranscriptionManager:
    def __init__(self):
        self.config = Config()
        self.api_token = self.config.ASSEMBLY_AI_KEY
        self.headers = {'authorization': self.api_token}
        self.base_url = 'https://api.assemblyai.com/v2'

    def transcribe_audio(self, audio_file_path, content_type='audio/wav'):
        try:
            # Verify file exists and has content
            if not os.path.exists(audio_file_path):
                return None, "Audio file not found"
            
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                return None, "Audio file is empty"
            
            logger.info(f"Processing audio file: {audio_file_path}, size: {file_size} bytes")
            
            # Convert WAV to MP3 if needed
            mp3_file_path = None
            if content_type == 'audio/wav' or audio_file_path.lower().endswith('.wav'):
                logger.info("Converting WAV to MP3 for AssemblyAI compatibility...")
                mp3_file_path = self._convert_wav_to_mp3(audio_file_path)
                if not mp3_file_path:
                    return None, "Failed to convert WAV to MP3"
                
                # Use the MP3 file for transcription
                file_to_upload = mp3_file_path
                upload_content_type = 'audio/mpeg'
            else:
                file_to_upload = audio_file_path
                upload_content_type = content_type
            
            # Upload the audio file (now MP3)
            audio_url = self._upload_audio_simple(file_to_upload)
            if not audio_url:
                self._cleanup_temp_file(mp3_file_path)
                return None, "Failed to upload audio"
            
            transcript_id = self._request_transcription(audio_url)
            if not transcript_id:
                self._cleanup_temp_file(mp3_file_path)
                return None, "Failed to start transcription"
            
            transcription = self._wait_for_completion(transcript_id)
            
            # Clean up temporary MP3 file
            self._cleanup_temp_file(mp3_file_path)
            
            return transcription, None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None, str(e)

    def _convert_wav_to_mp3(self, wav_file_path):
        """Convert WAV file to MP3 format"""
        try:
            # Generate MP3 filename
            base_path = os.path.splitext(wav_file_path)[0]
            mp3_file_path = f"{base_path}.mp3"
            
            logger.info(f"Converting {wav_file_path} to {mp3_file_path}")
            
            # Load WAV file and convert to MP3
            audio = AudioSegment.from_wav(wav_file_path)
            
            # Export as MP3 with good quality
            audio.export(
                mp3_file_path, 
                format="mp3", 
                bitrate="128k",  # Good quality for speech
                parameters=["-ac", "1"]  # Mono channel
            )
            
            # Verify MP3 file was created
            if os.path.exists(mp3_file_path) and os.path.getsize(mp3_file_path) > 0:
                logger.info(f"Successfully converted to MP3: {os.path.getsize(mp3_file_path)} bytes")
                return mp3_file_path
            else:
                logger.error("MP3 conversion failed - no output file")
                return None
                
        except Exception as e:
            logger.error(f"WAV to MP3 conversion error: {e}")
            return None

    def _cleanup_temp_file(self, file_path):
        """Clean up temporary files"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not clean up temp file {file_path}: {e}")

    def _upload_audio_simple(self, audio_file_path):
        """Simplified upload method - exactly like your working test code"""
        try:
            logger.info("Uploading audio file to AssemblyAI...")
            
            # Upload the audio file - EXACT same method as your working code
            with open(audio_file_path, 'rb') as f:
                response = requests.post(
                    'https://api.assemblyai.com/v2/upload',
                    headers=self.headers, 
                    files={'file': f}
                )
            
            if response.status_code != 200:
                logger.error(f"Upload failed: {response.text}")
                return None
            
            audio_url = response.json()['upload_url']
            logger.info("Audio uploaded successfully!")
            return audio_url
            
        except Exception as e:
            logger.error(f"Audio upload error: {e}")
            return None

    def _request_transcription(self, audio_url):
        """Request transcription - exactly like your working test code"""
        try:
            # Request transcription with disfluencies enabled - EXACT same as your code
            data = {
                'audio_url': audio_url,
                'disfluencies': True,  # Preserves "uh", "um", etc.
                'filter_profanity': False,
                'punctuate': True
            }
            
            logger.info("Starting transcription...")
            response = requests.post(
                'https://api.assemblyai.com/v2/transcript',
                json=data, 
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error(f"Transcription request failed: {response.text}")
                return None
            
            transcript_id = response.json()['id']
            logger.info(f"Transcription started with ID: {transcript_id}")
            return transcript_id
            
        except Exception as e:
            logger.error(f"Transcription request error: {e}")
            return None

    def _wait_for_completion(self, transcript_id):
        """Wait for completion - exactly like your working test code"""
        try:
            logger.info("Waiting for transcription completion")
            
            # Wait for completion - EXACT same logic as your code
            while True:
                response = requests.get(
                    f'https://api.assemblyai.com/v2/transcript/{transcript_id}',
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Status check failed: {response.text}")
                    return None
                
                result = response.json()
                
                if result['status'] == 'completed':
                    logger.info("Transcription completed successfully")
                    text = result.get('text', '').strip()
                    return text if text else None
                elif result['status'] == 'error':
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Transcription error: {error_msg}")
                    return None
                
                logger.info("Processing...")
                time.sleep(3)
            
        except Exception as e:
            logger.error(f"Transcription completion check error: {e}")
            return None

    def get_audio_duration(self, audio_file_path):
        """Get audio duration using pydub for accuracy"""
        try:
            if audio_file_path.lower().endswith('.wav'):
                audio = AudioSegment.from_wav(audio_file_path)
            elif audio_file_path.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_file_path)
            else:
                # Fallback to file size estimation
                file_size = os.path.getsize(audio_file_path)
                return max(file_size / (1024 * 1024), 0.1)
            
            # Return duration in minutes
            duration_minutes = len(audio) / (1000 * 60)  # pydub returns milliseconds
            return max(duration_minutes, 0.1)
            
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            return 1.0  # Default fallback