import os
import sys
import subprocess
import sqlite3

def check_database():
    """Check if the database file exists and is valid."""
    db_path = 'journal.db'
    if not os.path.exists(db_path):
        print(f"Database file {db_path} doesn't exist. A new one will be created.")
        return True
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Try to access a table to verify the database is valid
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"Database verified successfully. Found {len(tables)} tables.")
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

def reset_database():
    """Delete the existing database file."""
    db_path = 'journal.db'
    try:
        # Also delete WAL and SHM files if they exist
        for extension in ['', '-wal', '-shm']:
            file_path = f'{db_path}{extension}'
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Warning: Could not delete {file_path}: {e}")
                    if extension == '':  # If we can't delete the main DB file, it's a problem
                        return False
        return True
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

def run_app():
    """Run the Flask application."""
    print("Starting the Flask application...")
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running Flask app: {e}")
        return False
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
        return True

if __name__ == "__main__":
    print("=" * 50)
    print("EmpatheticAI Journal App Starter")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Resetting database...")
        if not reset_database():
            print("Failed to reset database. Exiting.")
            sys.exit(1)
    else:
        if not check_database():
            print("Database is corrupt. Resetting...")
            if not reset_database():
                print("Failed to reset database. Exiting.")
                sys.exit(1)
    
    run_app() 