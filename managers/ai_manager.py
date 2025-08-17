import google.generativeai as genai
import json
import logging
from config import Config

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self):
        self.config = Config()
        genai.configure(api_key=self.config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-pro')

    def analyze_speech(self, transcription, task_prompt=None):
        try:
            analysis_prompt = f"""
            You are analyzing a transcribed speech for a gamified public speaking application. 
            
            TRANSCRIBED SPEECH (raw with filler words and pauses):
            "{transcription}"
            
            TASK CONTEXT: {task_prompt if task_prompt else "General speech analysis"}
            
            Provide a detailed analysis in STRICT JSON format with these exact keys:
            {{
                "repetition_score": [0-100 score, where 100 is no repetition],
                "filler_count": [total count of um, uh, like, you know, etc.],
                "weak_words_count": [count of uncertain words like maybe, probably, sort of],
                "flow_score": [0-100 score for overall speech flow and coherence],
                "confidence_score": [0-100 score based on word choice and delivery],
                "summary": {{
                    "flow": "Brief assessment of speech flow and structure",
                    "weakness": "Main areas needing improvement",
                    "growth_potential": "Specific suggestions for improvement"
                }},
                "detailed_feedback": "Comprehensive feedback paragraph",
                "strengths": ["list", "of", "identified", "strengths"],
                "improvement_areas": ["specific", "areas", "to", "work", "on"]
            }}
            
            Analyze the speech thoroughly and provide constructive, encouraging feedback.
            """
            
            response = self.model.generate_content(analysis_prompt)
            
            # Clean and parse the response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            analysis = json.loads(response_text)
            logger.info("Speech analysis completed successfully")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._fallback_analysis()
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._fallback_analysis()

    def generate_quick_task(self):
        try:
            prompt = """
            Generate a creative sentence starter for a public speaking quick task. 
            This should be engaging and thought-provoking, suitable for impromptu speaking practice.
            
            Provide your response in this JSON format:
            {
                "sentence_starter": "The beginning of the sentence that users will complete",
                "example_completion": "A sample completion to show the expected style",
                "topic_hint": "Brief hint about what direction to take"
            }
            
            Make it creative and varied - could be about life, business, relationships, nature, technology, dreams, etc.
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            task = json.loads(response_text)
            logger.info("Quick task generated successfully")
            return task
            
        except Exception as e:
            logger.error(f"Quick task generation error: {e}")
            return self._fallback_quick_task()

    def _fallback_analysis(self):
        return {
            "repetition_score": 75,
            "filler_count": 0,
            "weak_words_count": 0,
            "flow_score": 70,
            "confidence_score": 70,
            "summary": {
                "flow": "Speech analysis temporarily unavailable",
                "weakness": "Unable to analyze at this time",
                "growth_potential": "Keep practicing your speaking skills"
            },
            "detailed_feedback": "Analysis service temporarily unavailable. Your speech was recorded successfully.",
            "strengths": ["Completed the speaking task"],
            "improvement_areas": ["Continue practicing regularly"]
        }

    def _fallback_quick_task(self):
        import random
        
        fallback_tasks = [
            {
                "sentence_starter": "The best advice I ever received was...",
                "example_completion": "The best advice I ever received was to never stop learning, because knowledge opens doors we never knew existed.",
                "topic_hint": "Share wisdom that shaped your perspective"
            },
            {
                "sentence_starter": "If I could travel back in time...",
                "example_completion": "If I could travel back in time, I would tell my younger self that failure is just feedback in disguise.",
                "topic_hint": "Reflect on past experiences or historical moments"
            },
            {
                "sentence_starter": "The future of technology will...",
                "example_completion": "The future of technology will bridge the gap between human potential and practical possibilities.",
                "topic_hint": "Share your vision of technological progress"
            }
        ]
        
        return random.choice(fallback_tasks)