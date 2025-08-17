import pymysql
import logging
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = Config()
        self.connection = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=self.config.MYSQL_HOST,
                user=self.config.MYSQL_USER,
                password=self.config.MYSQL_PASSWORD,
                database=self.config.MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def create_tables(self):
        try:
            cursor = self.connection.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Levels table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS levels (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    level_number INT UNIQUE NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'easy',
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    level_id INT,
                    task_type ENUM('analogy', 'story', 'presentation') NOT NULL,
                    prompt TEXT NOT NULL,
                    example_response TEXT,
                    order_index INT DEFAULT 0,
                    FOREIGN KEY (level_id) REFERENCES levels(id)
                )
            ''')
            
            # User progress table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_progress (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    level_id INT,
                    is_completed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP NULL,
                    score INT DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (level_id) REFERENCES levels(id)
                )
            ''')
            
            # Speech responses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS speech_responses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    level_number INT,
                    task_id INT,
                    transcription TEXT,
                    ai_feedback JSON,
                    audio_duration FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_quick_task BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            ''')
            
            # User statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_statistics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    total_speeches INT DEFAULT 0,
                    avg_filler_count FLOAT DEFAULT 0,
                    avg_repetition_score FLOAT DEFAULT 0,
                    avg_flow_score FLOAT DEFAULT 0,
                    best_level_completed INT DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            self.connection.commit()
            logger.info("Database tables created/verified")
            
            # Insert default levels
            self.insert_default_levels()
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def insert_default_levels(self):
        cursor = self.connection.cursor()
        
        levels = [
            (1, "Introduction Basics", "Learn to introduce yourself confidently", "easy"),
            (2, "Storytelling Fundamentals", "Master the art of compelling narratives", "easy"),
            (3, "Business Analogies", "Create powerful business comparisons", "medium"),
            (4, "Persuasive Speaking", "Develop convincing arguments", "medium"),
            (5, "Advanced Presentations", "Master complex presentation skills", "hard")
        ]
        
        for level in levels:
            cursor.execute('''
                INSERT IGNORE INTO levels (level_number, title, description, difficulty)
                VALUES (%s, %s, %s, %s)
            ''', level)
        
        # Insert tasks for each level - Fixed to prevent duplicates
        tasks = [
            # Level 1 tasks
            (1, "analogy", "Complete this sentence: 'Learning is like...'", "Learning is like riding a bicycle because once you get the hang of it, you never forget.", 1),
            (1, "analogy", "Complete this sentence: 'Friendship is like...'", "Friendship is like a garden because it needs constant care to flourish.", 2),
            (1, "story", "Tell us about yourself in 30 seconds", "Hi, I'm [name], and I believe every challenge is an opportunity to grow.", 3),
            (1, "analogy", "Complete this sentence: 'Time is like...'", "Time is like water because it flows constantly and cannot be held back.", 4),
            
            # Level 2 tasks
            (2, "story", "Tell a story about overcoming a challenge", "Share a personal experience that shaped who you are today.", 1),
            (2, "analogy", "Complete this sentence: 'Success is like...'", "Success is like climbing a mountain because the view from the top makes all the effort worthwhile.", 2),
            (2, "story", "Describe a moment when you helped someone", "Talk about a time when your actions made a positive difference.", 3),
            (2, "analogy", "Complete this sentence: 'Dreams are like...'", "Dreams are like seeds because they need nurturing to grow into reality.", 4),
            
            # Level 3 tasks
            (3, "analogy", "Complete this sentence: 'Business is like...'", "Business is like running a marathon because you need endurance and strategy to reach the finish line.", 1),
            (3, "presentation", "Pitch a simple business idea in 60 seconds", "Present your idea with problem, solution, and benefits.", 2),
            (3, "analogy", "Complete this sentence: 'Leadership is like...'", "Leadership is like conducting an orchestra because you must bring harmony from different talents.", 3),
            (3, "presentation", "Explain why teamwork matters in business", "Discuss the value of collaboration with specific examples.", 4),
            
            # Level 4 tasks
            (4, "presentation", "Argue for or against remote work", "Present a compelling case with evidence and examples.", 1),
            (4, "story", "Share a leadership experience", "Describe a time you led others through difficulty.", 2),
            (4, "presentation", "Convince someone to try a new hobby", "Use persuasive techniques to make your case compelling.", 3),
            (4, "analogy", "Complete this sentence: 'Innovation is like...'", "Innovation is like cooking because it combines existing ingredients in new ways.", 4),
            
            # Level 5 tasks
            (5, "presentation", "Present a 3-minute impromptu speech", "Topic will be given 30 seconds before you start.", 1),
            (5, "story", "Deliver an inspiring message", "Motivate others with your words and conviction.", 2),
            (5, "presentation", "Explain a complex concept simply", "Break down a difficult topic for a general audience.", 3),
            (5, "presentation", "Give a professional elevator pitch", "Present yourself or your ideas in 2 minutes or less.", 4)
        ]
        
        # Clear existing tasks to prevent duplicates (for development)
        cursor.execute('DELETE FROM tasks')
        
        for task_data in tasks:
            level_number, task_type, prompt, example, order_index = task_data
            cursor.execute('''
                SELECT id FROM levels WHERE level_number = %s
            ''', (level_number,))
            level_result = cursor.fetchone()
            
            if level_result:
                cursor.execute('''
                    INSERT INTO tasks (level_id, task_type, prompt, example_response, order_index)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (level_result['id'], task_type, prompt, example, order_index))
        
        self.connection.commit()

    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        self.connection.commit()
        return result

    def execute_single_query(self, query, params=None):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        self.connection.commit()
        return result

    def insert_query(self, query, params=None):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        insert_id = cursor.lastrowid
        self.connection.commit()
        return insert_id

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")