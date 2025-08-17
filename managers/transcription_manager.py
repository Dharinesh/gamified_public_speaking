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

    def transcribe_audio(self, audio_file_path, content_type='audio/wav'):
        try:
            # Verify file exists and has content
            if not os.path.exists(audio_file_path):
                return None, "Audio file not found"
            
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                return None, "Audio file is empty"
            
            # Check minimum size for WAV files (header + some data)
            if content_type == 'audio/wav' and file_size < 100:
                return None, "WAV file is too small to contain valid audio"
            
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

    def _upload_audio(self, audio_file_path, content_type='audio/wav'):
        try:
            logger.info(f"Uploading audio file for transcription with content type: {content_type}")
            
            # Read file
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            
            logger.info(f"Audio data read: {len(audio_data)} bytes")
            
            # Determine proper filename and content type
            if 'wav' in content_type.lower():
                filename = 'audio.wav'
                mime_type = 'audio/wav'
            elif 'mp3' in content_type.lower() or 'mpeg' in content_type.lower():
                filename = 'audio.mp3'
                mime_type = 'audio/mpeg'
            elif 'mp4' in content_type.lower():
                filename = 'audio.mp4'
                mime_type = 'audio/mp4'
            elif 'ogg' in content_type.lower():
                filename = 'audio.ogg'
                mime_type = 'audio/ogg'
            else:
                # Default to WAV
                filename = 'audio.wav'
                mime_type = 'audio/wav'
            
            # For WAV files, verify basic WAV header
            if mime_type == 'audio/wav' and len(audio_data) >= 44:
                # Check for RIFF header
                if audio_data[:4] != b'RIFF':
                    logger.warning("File doesn't have proper WAV RIFF header")
                    return None
                
                # Check for WAVE format
                if audio_data[8:12] != b'WAVE':
                    logger.warning("File doesn't have proper WAV format identifier")
                    return None
                
                logger.info("WAV header validation passed")
            
            # Prepare file for upload
            files = {
                'file': (filename, audio_data, mime_type)
            }
            
            response = requests.post(
                f'{self.base_url}/upload',
                headers=self.headers,
                files=files,
                timeout=30  # Add timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Upload failed with status {response.status_code}: {response.text}")
                return None
            
            result = response.json()
            audio_url = result.get('upload_url')
            
            if not audio_url:
                logger.error("No upload URL returned from AssemblyAI")
                return None
            
            logger.info("Audio uploaded successfully to AssemblyAI")
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
                'auto_highlights': False,
                'language_detection': False,  # Assume English
                'language_code': 'en'  # Explicit English
            }
            
            response = requests.post(
                f'{self.base_url}/transcript',
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Transcription request failed with status {response.status_code}: {response.text}")
                return None
            
            result = response.json()
            transcript_id = result.get('id')
            
            if not transcript_id:
                logger.error("No transcript ID returned from AssemblyAI")
                return None
            
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
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"Status check failed: {response.text}")
                    return None
                
                result = response.json()
                
                if result['status'] == 'completed':
                    logger.info("Transcription completed successfully")
                    text = result.get('text', '').strip()
                    
                    if not text:
                        logger.warning("Transcription completed but text is empty")
                        return None
                    
                    return text
                elif result['status'] == 'error':
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Transcription error: {error_msg}")
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
            # For WAV files, try to read the duration from header
            if audio_file_path.lower().endswith('.wav'):
                return self._get_wav_duration(audio_file_path)
            else:
                # Basic duration estimation for other formats
                file_size = os.path.getsize(audio_file_path)
                # Rough estimation: 1MB ≈ 1 minute for typical audio
                estimated_duration = file_size / (1024 * 1024)  # MB
                return max(estimated_duration, 0.1)  # Minimum 0.1 minutes
        except:
            return 1.0  # Default fallback

    def _get_wav_duration(self, wav_file_path):
        try:
            with open(wav_file_path, 'rb') as f:
                # Read WAV header
                f.seek(0)
                header = f.read(44)
                
                if len(header) < 44:
                    return 1.0
                
                # Check RIFF and WAVE
                if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                    return 1.0
                
                # Extract sample rate (bytes 24-27)
                sample_rate = int.from_bytes(header[24:28], byteorder='little')
                
                # Extract data chunk size (bytes 40-43)
                data_size = int.from_bytes(header[40:44], byteorder='little')
                
                # Calculate duration
                # For 16-bit mono: bytes_per_second = sample_rate * 2
                bytes_per_second = sample_rate * 2
                duration_seconds = data_size / bytes_per_second
                
                return max(duration_seconds / 60, 0.1)  # Convert to minutes
                
        except Exception as e:
            logger.warning(f"Could not calculate WAV duration: {e}")
            return 1.0