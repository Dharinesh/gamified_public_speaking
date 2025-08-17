import os
import requests
import time
import logging
from config import Config

logger = logging.getLogger(__name__)

class TranscriptionManager:
    def __init__(self):
        self.config = Config()
        self.api_token = self.config.ASSEMBLY_AI_KEY
        self.headers = {'authorization': self.api_token}
        self.base_url = 'https://api.assemblyai.com/v2'

    def transcribe_audio(self, audio_file_path, content_type='audio/webm'):
        try:
            # Verify file exists and has content
            if not os.path.exists(audio_file_path):
                return None, "Audio file not found"
            
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                return None, "Audio file is empty"
            
            logger.info(f"Processing audio file: {audio_file_path}, size: {file_size} bytes, type: {content_type}")
            
            audio_url = self._upload_audio(audio_file_path, content_type)
            if not audio_url:
                return None, "Failed to upload audio"
            
            transcript_id = self._request_transcription(audio_url)
            if not transcript_id:
                return None, "Failed to start transcription"
            
            transcription = self._wait_for_completion(transcript_id)
            return transcription, None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None, str(e)

    def _upload_audio(self, audio_file_path, content_type='audio/webm'):
        try:
            logger.info(f"Uploading audio file for transcription with content type: {content_type}")
            
            # Read file and determine proper content type and filename
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            
            # Determine filename based on content type
            if 'wav' in content_type:
                filename = 'audio.wav'
            elif 'mp3' in content_type or 'mpeg' in content_type:
                filename = 'audio.mp3'
            elif 'mp4' in content_type:
                filename = 'audio.mp4'
            elif 'ogg' in content_type:
                filename = 'audio.ogg'
            else:
                # For WebM and other formats, try MP3 extension as fallback
                filename = 'audio.mp3'
                content_type = 'audio/mpeg'
            
            # Prepare file for upload with proper content type
            files = {
                'file': (filename, audio_data, content_type)
            }
            
            response = requests.post(
                f'{self.base_url}/upload',
                headers=self.headers,
                files=files
            )
            
            if response.status_code != 200:
                logger.error(f"Upload failed: {response.text}")
                return None
            
            audio_url = response.json()['upload_url']
            logger.info("Audio uploaded successfully")
            return audio_url
            
        except Exception as e:
            logger.error(f"Audio upload error: {e}")
            return None

    def _request_transcription(self, audio_url):
        try:
            data = {
                'audio_url': audio_url,
                'disfluencies': True,  # Preserves "uh", "um", etc.
                'filter_profanity': False,
                'punctuate': True,
                'speaker_labels': False,
                'auto_highlights': False
            }
            
            response = requests.post(
                f'{self.base_url}/transcript',
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
        try:
            logger.info("Waiting for transcription completion")
            max_attempts = 60  # 3 minutes max wait time
            attempts = 0
            
            while attempts < max_attempts:
                response = requests.get(
                    f'{self.base_url}/transcript/{transcript_id}',
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Status check failed: {response.text}")
                    return None
                
                result = response.json()
                
                if result['status'] == 'completed':
                    logger.info("Transcription completed successfully")
                    return result['text']
                elif result['status'] == 'error':
                    logger.error(f"Transcription error: {result.get('error', 'Unknown error')}")
                    return None
                
                attempts += 1
                time.sleep(3)
            
            logger.error("Transcription timeout")
            return None
            
        except Exception as e:
            logger.error(f"Transcription completion check error: {e}")
            return None

    def get_audio_duration(self, audio_file_path):
        try:
            # Basic duration estimation - for production, use librosa or mutagen
            import os
            file_size = os.path.getsize(audio_file_path)
            # Rough estimation: 1MB ≈ 1 minute for typical audio
            estimated_duration = file_size / (1024 * 1024)  # MB
            return max(estimated_duration, 0.1)  # Minimum 0.1 minutes
        except:
            return 1.0  # Default fallback