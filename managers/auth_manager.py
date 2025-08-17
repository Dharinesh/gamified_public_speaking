from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.created_at = user_data['created_at']
        self._is_active = user_data['is_active']

    @property
    def is_active(self):
        return bool(self._is_active)

    def get_id(self):
        return str(self.id)

class AuthManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_user(self, username, email, password):
        try:
            # Check if user already exists
            existing_user = self.db.execute_single_query(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            
            if existing_user:
                return None, "Username or email already exists"
            
            # Create password hash
            password_hash = generate_password_hash(password)
            
            # Insert new user
            user_id = self.db.insert_query(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            
            # Initialize user statistics
            self.db.insert_query(
                "INSERT INTO user_statistics (user_id) VALUES (%s)",
                (user_id,)
            )
            
            logger.info(f"New user created: {username}")
            return user_id, None
            
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return None, "Registration failed"

    def authenticate_user(self, username, password):
        try:
            user_data = self.db.execute_single_query(
                "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
                (username,)
            )
            
            if not user_data:
                return None, "Invalid username or password"
            
            if not check_password_hash(user_data['password_hash'], password):
                return None, "Invalid username or password"
            
            user = User(user_data)
            logger.info(f"User authenticated: {username}")
            return user, None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None, "Login failed"

    def get_user_by_id(self, user_id):
        try:
            user_data = self.db.execute_single_query(
                "SELECT * FROM users WHERE id = %s AND is_active = TRUE",
                (user_id,)
            )
            
            if user_data:
                return User(user_data)
            return None
            
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None

    def get_user_progress(self, user_id):
        try:
            progress = self.db.execute_query('''
                SELECT l.level_number, l.title, l.description, l.difficulty,
                       COALESCE(up.is_completed, FALSE) as is_completed,
                       up.completed_at, up.score
                FROM levels l
                LEFT JOIN user_progress up ON l.id = up.level_id AND up.user_id = %s
                WHERE l.is_active = TRUE
                ORDER BY l.level_number
            ''', (user_id,))
            
            return progress
            
        except Exception as e:
            logger.error(f"Get user progress error: {e}")
            return []

    def get_user_statistics(self, user_id):
        try:
            stats = self.db.execute_single_query(
                "SELECT * FROM user_statistics WHERE user_id = %s",
                (user_id,)
            )
            
            if not stats:
                # Create default statistics if none exist
                self.db.insert_query(
                    "INSERT INTO user_statistics (user_id) VALUES (%s)",
                    (user_id,)
                )
                stats = self.db.execute_single_query(
                    "SELECT * FROM user_statistics WHERE user_id = %s",
                    (user_id,)
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"Get user statistics error: {e}")
            return None

    def update_user_statistics(self, user_id, speech_analysis):
        try:
            current_stats = self.get_user_statistics(user_id)
            if not current_stats:
                return False
            
            # Calculate new averages
            total_speeches = current_stats['total_speeches'] + 1
            
            new_avg_filler = ((current_stats['avg_filler_count'] * current_stats['total_speeches']) + 
                             speech_analysis['filler_count']) / total_speeches
            
            new_avg_repetition = ((current_stats['avg_repetition_score'] * current_stats['total_speeches']) + 
                                 speech_analysis['repetition_score']) / total_speeches
            
            new_avg_flow = ((current_stats['avg_flow_score'] * current_stats['total_speeches']) + 
                           speech_analysis['flow_score']) / total_speeches
            
            # Update statistics
            self.db.execute_query('''
                UPDATE user_statistics 
                SET total_speeches = %s, 
                    avg_filler_count = %s, 
                    avg_repetition_score = %s, 
                    avg_flow_score = %s,
                    last_activity = CURRENT_TIMESTAMP
                WHERE user_id = %s
            ''', (total_speeches, new_avg_filler, new_avg_repetition, new_avg_flow, user_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Update user statistics error: {e}")
            return False