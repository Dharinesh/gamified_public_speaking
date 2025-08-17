import json
import logging

logger = logging.getLogger(__name__)

class GameManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_level_details(self, level_number, user_id):
        try:
            level = self.db.execute_single_query('''
                SELECT l.*, COALESCE(up.is_completed, FALSE) as is_completed,
                       up.score, up.completed_at
                FROM levels l
                LEFT JOIN user_progress up ON l.id = up.level_id AND up.user_id = %s
                WHERE l.level_number = %s AND l.is_active = TRUE
            ''', (user_id, level_number))
            
            if not level:
                return None
            
            tasks = self.db.execute_query('''
                SELECT id, task_type, prompt, example_response, order_index
                FROM tasks
                WHERE level_id = %s
                ORDER BY order_index, id
            ''', (level['id'],))
            
            level['tasks'] = tasks
            return level
            
        except Exception as e:
            logger.error(f"Get level details error: {e}")
            return None

    def get_all_levels(self, user_id):
        try:
            levels = self.db.execute_query('''
                SELECT l.level_number, l.title, l.description, l.difficulty,
                       COALESCE(up.is_completed, FALSE) as is_completed,
                       up.score, up.completed_at
                FROM levels l
                LEFT JOIN user_progress up ON l.id = up.level_id AND up.user_id = %s
                WHERE l.is_active = TRUE
                ORDER BY l.level_number
            ''', (user_id,))
            
            return levels
            
        except Exception as e:
            logger.error(f"Get all levels error: {e}")
            return []

    def save_speech_response(self, user_id, level_number, task_id, transcription, ai_feedback, audio_duration, is_quick_task=False):
        try:
            response_id = self.db.insert_query('''
                INSERT INTO speech_responses 
                (user_id, level_number, task_id, transcription, ai_feedback, audio_duration, is_quick_task)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, level_number, task_id, transcription, json.dumps(ai_feedback), audio_duration, is_quick_task))
            
            logger.info(f"Speech response saved with ID: {response_id}")
            return response_id
            
        except Exception as e:
            logger.error(f"Save speech response error: {e}")
            return None

    def complete_level(self, user_id, level_number, score):
        try:
            level = self.db.execute_single_query(
                "SELECT id FROM levels WHERE level_number = %s",
                (level_number,)
            )
            
            if not level:
                return False
            
            # Check if progress already exists
            existing_progress = self.db.execute_single_query('''
                SELECT id FROM user_progress 
                WHERE user_id = %s AND level_id = %s
            ''', (user_id, level['id']))
            
            if existing_progress:
                # Update existing progress
                self.db.execute_query('''
                    UPDATE user_progress 
                    SET is_completed = TRUE, completed_at = CURRENT_TIMESTAMP, score = %s
                    WHERE user_id = %s AND level_id = %s
                ''', (score, user_id, level['id']))
            else:
                # Insert new progress
                self.db.insert_query('''
                    INSERT INTO user_progress (user_id, level_id, is_completed, completed_at, score)
                    VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP, %s)
                ''', (user_id, level['id'], score))
            
            # Update user statistics
            self.db.execute_query('''
                UPDATE user_statistics 
                SET best_level_completed = GREATEST(best_level_completed, %s)
                WHERE user_id = %s
            ''', (level_number, user_id))
            
            logger.info(f"Level {level_number} completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Complete level error: {e}")
            return False

    def get_user_speech_history(self, user_id, limit=10):
        try:
            history = self.db.execute_query('''
                SELECT sr.*, t.prompt, l.title as level_title
                FROM speech_responses sr
                LEFT JOIN tasks t ON sr.task_id = t.id
                LEFT JOIN levels l ON t.level_id = l.id
                WHERE sr.user_id = %s
                ORDER BY sr.created_at DESC
                LIMIT %s
            ''', (user_id, limit))
            
            # Parse JSON feedback
            for record in history:
                if record['ai_feedback']:
                    try:
                        record['ai_feedback'] = json.loads(record['ai_feedback'])
                    except:
                        record['ai_feedback'] = {}
            
            return history
            
        except Exception as e:
            logger.error(f"Get speech history error: {e}")
            return []

    def calculate_level_score(self, ai_feedback):
        try:
            # Calculate composite score from AI feedback
            repetition_score = ai_feedback.get('repetition_score', 0)
            flow_score = ai_feedback.get('flow_score', 0)
            confidence_score = ai_feedback.get('confidence_score', 0)
            
            # Penalize for excessive fillers and weak words
            filler_penalty = min(ai_feedback.get('filler_count', 0) * 2, 20)
            weak_words_penalty = min(ai_feedback.get('weak_words_count', 0) * 3, 15)
            
            total_score = (repetition_score + flow_score + confidence_score) / 3
            total_score = max(0, total_score - filler_penalty - weak_words_penalty)
            
            return round(total_score)
            
        except Exception as e:
            logger.error(f"Calculate level score error: {e}")
            return 50  # Default score

    def is_level_unlocked(self, user_id, level_number):
        try:
            if level_number == 1:
                return True
            
            # Check if previous level is completed
            previous_level = self.db.execute_single_query('''
                SELECT up.is_completed
                FROM user_progress up
                JOIN levels l ON up.level_id = l.id
                WHERE up.user_id = %s AND l.level_number = %s
            ''', (user_id, level_number - 1))
            
            return previous_level and previous_level['is_completed']
            
        except Exception as e:
            logger.error(f"Check level unlock error: {e}")
            return False

    def get_leaderboard(self, limit=10):
        try:
            leaderboard = self.db.execute_query('''
                SELECT u.username, us.best_level_completed, us.total_speeches,
                       us.avg_flow_score, us.last_activity
                FROM user_statistics us
                JOIN users u ON us.user_id = u.id
                WHERE u.is_active = TRUE
                ORDER BY us.best_level_completed DESC, us.avg_flow_score DESC
                LIMIT %s
            ''', (limit,))
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Get leaderboard error: {e}")
            return []