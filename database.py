import sqlite3
import os
import json
import threading
import time
from datetime import datetime

class Database:
    _instances = {}
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            db_path = kwargs.get('db_path', 'journal.db')
            if db_path not in cls._instances:
                instance = super(Database, cls).__new__(cls)
                instance._initialized = False
                cls._instances[db_path] = instance
            return cls._instances[db_path]
    
    def __init__(self, db_path='journal.db'):
        """Initialize the database connection."""
        if getattr(self, '_initialized', False):
            return
            
        self.db_path = db_path
        self.conn = None
        self.lock = threading.Lock()
        self._busy_timeout = 30000  # 30 seconds
        self.setup_database()
        self._initialized = True
    
    def _get_connection(self):
        """Get a database connection with proper timeout settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=self._busy_timeout)
        conn.execute("PRAGMA busy_timeout = %d" % self._busy_timeout)
        conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
        conn.row_factory = sqlite3.Row
        return conn
    
    def setup_database(self):
        """Setup database tables if they don't exist."""
        try:
            with self.lock:
                # Create a new connection for setup
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Create journal entries table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    entry_text TEXT NOT NULL,
                    emotion TEXT,
                    sentiment_score REAL,
                    emotions_detected TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prompt_used TEXT,
                    is_favorite INTEGER DEFAULT 0
                )
                ''')
                
                # Create prompts table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS journal_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_text TEXT NOT NULL,
                    emotion_category TEXT,
                    usage_count INTEGER DEFAULT 0
                )
                ''')
                
                # Create mood tags table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS mood_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    journal_id INTEGER,
                    tag_name TEXT NOT NULL,
                    tag_emoji TEXT,
                    FOREIGN KEY (journal_id) REFERENCES journal_entries (id)
                )
                ''')
                
                # Insert default prompts if the prompts table is empty
                cursor.execute("SELECT COUNT(*) FROM journal_prompts")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    self._insert_default_prompts(cursor)
                
                conn.commit()
                conn.close()
                print("Database setup completed successfully")
        except sqlite3.Error as e:
            print(f"Database setup error: {e}")
    
    def _insert_default_prompts(self, cursor):
        """Insert default journal prompts into the database."""
        default_prompts = [
            # General/Neutral prompts
            ("What made you smile today?", "neutral"),
            ("What are three things you're grateful for?", "neutral"),
            ("Describe a moment of peace you felt today.", "neutral"),
            ("What's something new you learned today?", "neutral"),
            ("What's something you're looking forward to?", "neutral"),
            
            # Happy prompts
            ("What accomplishment are you proud of today?", "happy"),
            ("How did you spread joy to others today?", "happy"),
            ("What made today special?", "happy"),
            ("Describe a moment that made you laugh.", "happy"),
            ("What's the best thing that happened today?", "happy"),
            
            # Sad prompts
            ("What's weighing on your mind today?", "sad"),
            ("What's one small comfort you can give yourself right now?", "sad"),
            ("What would help you feel better?", "sad"),
            ("Is there something you need to let go of?", "sad"),
            ("What's a tiny win you can celebrate even on a hard day?", "sad"),
            
            # Anxious prompts
            ("What are you worried about right now?", "anxious"),
            ("What helps you feel grounded when you're stressed?", "anxious"),
            ("What's one thing you can control right now?", "anxious"),
            ("What's a calming thought you can hold onto?", "anxious"),
            ("What would you tell a friend who's feeling this way?", "anxious"),
            
            # Angry prompts
            ("What's frustrating you today?", "angry"),
            ("How can you channel this energy constructively?", "angry"),
            ("What boundaries might you need to set?", "angry"),
            ("What would help you let go of this anger?", "angry"),
            ("What's the real issue beneath the surface?", "angry")
        ]
        
        # Insert each prompt individually to avoid parameter binding issues
        for prompt_text, emotion_category in default_prompts:
            try:
                cursor.execute(
                    "INSERT INTO journal_prompts (prompt_text, emotion_category) VALUES (?, ?)",
                    (prompt_text, emotion_category)
                )
            except sqlite3.Error as e:
                print(f"Error inserting prompt '{prompt_text}': {e}")
                # Continue with other prompts even if one fails
                continue
    
    def close(self):
        """Close the database connection."""
        pass  # We're using new connections for each operation, no need to close
    
    def save_journal_entry(self, user_id, entry_text, emotion=None, sentiment_score=None, 
                           emotions_detected=None, prompt_used=None, is_favorite=0):
        """Save a new journal entry to the database."""
        # We'll make multiple attempts to handle transient locking issues
        max_attempts = 5
        attempt = 0
        conn = None
        
        while attempt < max_attempts:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Convert emotions_detected to JSON string if it's a dictionary
                if emotions_detected and isinstance(emotions_detected, dict):
                    emotions_detected = json.dumps(emotions_detected)
                
                print(f"Saving journal entry for user {user_id}, emotion: {emotion} (attempt {attempt+1})")
                
                cursor.execute('''
                INSERT INTO journal_entries 
                (user_id, entry_text, emotion, sentiment_score, emotions_detected, prompt_used, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, entry_text, emotion, sentiment_score, emotions_detected, prompt_used, is_favorite))
                
                conn.commit()
                last_id = cursor.lastrowid
                conn.close()
                
                print(f"Journal entry saved with ID: {last_id}")
                return last_id
                
            except sqlite3.Error as e:
                attempt += 1
                print(f"Error saving journal entry (attempt {attempt}): {e}")
                
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                
                # Wait a bit before retrying (with exponential backoff)
                if attempt < max_attempts:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                    print(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print("Max attempts reached, giving up.")
                    return None
        
        return None
    
    def get_journal_entries(self, user_id, limit=10, offset=0):
        """Get journal entries for a user with pagination."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, entry_text, emotion, sentiment_score, emotions_detected, 
                   created_at, prompt_used, is_favorite
            FROM journal_entries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            entries = []
            for row in cursor.fetchall():
                entry = {
                    'id': row['id'],
                    'entry_text': row['entry_text'],
                    'emotion': row['emotion'],
                    'sentiment_score': row['sentiment_score'],
                    'emotions_detected': json.loads(row['emotions_detected']) if row['emotions_detected'] else None,
                    'created_at': row['created_at'],
                    'prompt_used': row['prompt_used'],
                    'is_favorite': bool(row['is_favorite'])
                }
                entries.append(entry)
            
            conn.close()
            return entries
        except sqlite3.Error as e:
            print(f"Error fetching journal entries: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            return []
    
    def get_entry_by_id(self, entry_id, user_id):
        """Get a specific journal entry by ID for a user."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, entry_text, emotion, sentiment_score, emotions_detected, 
                   created_at, prompt_used, is_favorite
            FROM journal_entries
            WHERE id = ? AND user_id = ?
            ''', (entry_id, user_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
                
            entry = {
                'id': row['id'],
                'entry_text': row['entry_text'],
                'emotion': row['emotion'],
                'sentiment_score': row['sentiment_score'],
                'emotions_detected': json.loads(row['emotions_detected']) if row['emotions_detected'] else None,
                'created_at': row['created_at'],
                'prompt_used': row['prompt_used'],
                'is_favorite': bool(row['is_favorite'])
            }
            
            return entry
        except sqlite3.Error as e:
            print(f"Error fetching journal entry: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            return None
    
    def toggle_favorite(self, entry_id, user_id):
        """Toggle the favorite status of a journal entry."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # First get current favorite status
            cursor.execute('''
            SELECT is_favorite FROM journal_entries
            WHERE id = ? AND user_id = ?
            ''', (entry_id, user_id))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
                
            current_status = bool(row[0])
            new_status = 1 if not current_status else 0
            
            # Update favorite status
            cursor.execute('''
            UPDATE journal_entries
            SET is_favorite = ?
            WHERE id = ? AND user_id = ?
            ''', (new_status, entry_id, user_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error toggling favorite status: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            return False
    
    def get_random_prompt(self, emotion=None):
        """Get a random prompt, optionally filtered by emotion category."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if emotion:
                cursor.execute('''
                SELECT id, prompt_text FROM journal_prompts
                WHERE emotion_category = ?
                ORDER BY RANDOM() LIMIT 1
                ''', (emotion,))
            else:
                cursor.execute('''
                SELECT id, prompt_text FROM journal_prompts
                ORDER BY RANDOM() LIMIT 1
                ''')
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {"id": 0, "text": "What's on your mind today?"}
                
            # Increment usage count
            prompt_id = row[0]
            prompt_text = row[1]
            
            cursor.execute('''
            UPDATE journal_prompts
            SET usage_count = usage_count + 1
            WHERE id = ?
            ''', (prompt_id,))
            
            conn.commit()
            conn.close()
            return {"id": prompt_id, "text": prompt_text}
        except sqlite3.Error as e:
            print(f"Error getting random prompt: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            return {"id": 0, "text": "What's on your mind today?"}
    
    def get_mood_analytics(self, user_id, days=30):
        """Get mood analytics for a user over a specified period."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get average sentiment score over time
            cursor.execute('''
            SELECT date(created_at) as entry_date, AVG(sentiment_score) as avg_score, 
                   COUNT(*) as entry_count, GROUP_CONCAT(emotion) as emotions
            FROM journal_entries
            WHERE user_id = ? AND created_at >= date('now', ?)
            GROUP BY date(created_at)
            ORDER BY entry_date
            ''', (user_id, f'-{days} days'))
            
            mood_data = []
            for row in cursor.fetchall():
                mood_data.append({
                    'date': row[0],
                    'avg_sentiment': row[1],
                    'entry_count': row[2],
                    'emotions': row[3].split(',') if row[3] else []
                })
            
            # Get most common emotions
            cursor.execute('''
            SELECT emotion, COUNT(*) as count
            FROM journal_entries
            WHERE user_id = ? AND created_at >= date('now', ?) AND emotion IS NOT NULL
            GROUP BY emotion
            ORDER BY count DESC
            LIMIT 5
            ''', (user_id, f'-{days} days'))
            
            top_emotions = []
            for row in cursor.fetchall():
                top_emotions.append({
                    'emotion': row[0],
                    'count': row[1]
                })
            
            # Get favorite entries
            cursor.execute('''
            SELECT COUNT(*) FROM journal_entries
            WHERE user_id = ? AND is_favorite = 1 AND created_at >= date('now', ?)
            ''', (user_id, f'-{days} days'))
            
            favorite_count = cursor.fetchone()[0]
            conn.close()
            
            return {
                'mood_data': mood_data,
                'top_emotions': top_emotions,
                'favorite_count': favorite_count,
                'entry_count': sum(item['entry_count'] for item in mood_data)
            }
        except sqlite3.Error as e:
            print(f"Error getting mood analytics: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            return {
                'mood_data': [],
                'top_emotions': [],
                'favorite_count': 0,
                'entry_count': 0
            }

# Initialize database when module is imported
db = Database()

# No need for explicit cleanup, as connections are created and closed per operation
# import atexit
# atexit.register(db.close) 