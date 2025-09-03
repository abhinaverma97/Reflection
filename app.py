from flask import Flask, request, jsonify, render_template, session, redirect, Response
from lifeCoach import LifeCoach
import os
import uuid
from mood_rec import emotion_to_content
from database import db
from ar_breathing_exercise import ARBreathingExercise
from emotion_recognition_feed import EmotionRecognitionFeed

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Initialize the LifeCoach instances dictionary
coach_instances = {}

# Get API key from environment variable or use default
api_key = os.environ.get('GEMINI_API_KEY', "AIzaSyCrGgr7E9k_XHp2TsUlPW4BYWJjFjhY5WQ")

# Initialize AR breathing exercise
ar_exercise = ARBreathingExercise()

# Initialize emotion recognition feed
emotion_feed = EmotionRecognitionFeed()

@app.route('/')
def home():
    # Create a unique session ID if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Initialize a coach for this session if not exists
    if session['session_id'] not in coach_instances:
        coach_instances[session['session_id']] = LifeCoach(api_key=api_key)
    
    return render_template('index.html')

@app.route('/journal')
def journal():
    # Create a unique session ID if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Get the user's current emotion from the coach if available
    current_emotion = "neutral"
    session_id = session.get('session_id')
    if session_id and session_id in coach_instances:
        current_emotion = coach_instances[session_id].get_current_emotion()
    
    # Get a random prompt based on the user's emotion
    prompt = db.get_random_prompt(current_emotion)
    
    return render_template('journal.html', prompt=prompt)

@app.route('/chat')
def chat_page():
    # Create a unique session ID if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Initialize a coach for this session if not exists
    if session['session_id'] not in coach_instances:
        coach_instances[session['session_id']] = LifeCoach(api_key=api_key)
    
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    conversation_history = data.get('history', [])
    
    # Get the session ID
    session_id = session.get('session_id')
    if not session_id or session_id not in coach_instances:
        # Create a new session if needed
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        coach_instances[session_id] = LifeCoach(api_key=api_key)
    
    # Get the coach instance for this session
    coach = coach_instances[session_id]
    
    try:
        # If the client sent a conversation history, use it to update the coach
        if conversation_history and len(conversation_history) > 1:  # Skip if only the greeting is present
            # First reset the conversation to make sure we start fresh
            coach.reset_conversation()
            
            # Then add all messages except the latest (which we'll process next)
            for msg in conversation_history[:-1]:
                if msg['role'] == 'user':
                    # For user messages, silently process them to build context
                    coach.update_conversation_history(msg['content'], 'user')
                elif msg['role'] == 'assistant':
                    coach.update_conversation_history(msg['content'], 'assistant')
        
        # Get response from LifeCoach for the current message
        response_text = coach.get_response(user_message)
        
        # Get the detected emotion
        current_emotion = coach.get_current_emotion()
        
        # Get recommendations based on emotion
        recommendations = get_recommendations(current_emotion)
        
        return jsonify({
            'message': response_text,
            'emotion': current_emotion,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/journal/save', methods=['POST'])
def save_journal():
    try:
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({
                'status': 'error',
                'message': 'No data received'
            }), 400
            
        entry_text = data.get('entry_text', '')
        prompt_used = data.get('prompt_used', '')
        manual_emotion = data.get('emotion', None)
        
        if not entry_text or entry_text.strip() == '':
            print("Empty journal entry text")
            return jsonify({
                'status': 'error',
                'message': 'Journal entry text cannot be empty'
            }), 400
        
        # Get the session ID
        session_id = session.get('session_id')
        if not session_id:
            print("Creating new session ID")
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        print(f"Processing journal entry for session {session_id}")
        
        # Analyze the entry for emotions if a coach instance exists
        emotion = manual_emotion
        sentiment_score = None
        emotions_detected = None
        
        if session_id in coach_instances:
            coach = coach_instances[session_id]
            # Only detect emotion if it wasn't manually specified
            if not manual_emotion:
                print("Detecting emotion from text...")
                detected_emotion, confidence, explanation = coach.detect_emotion(entry_text)
                emotion = detected_emotion
                sentiment_score = confidence / 10.0  # Convert 0-10 to 0-1 scale
                emotions_detected = {
                    "primary": detected_emotion,
                    "confidence": confidence,
                    "explanation": explanation
                }
                print(f"Detected emotion: {emotion} with confidence {confidence}")
        
        # Save the journal entry to the database
        print(f"Saving journal entry to database: {len(entry_text)} chars, emotion: {emotion}")
        entry_id = db.save_journal_entry(
            user_id=session_id,
            entry_text=entry_text,
            emotion=emotion,
            sentiment_score=sentiment_score,
            emotions_detected=emotions_detected,
            prompt_used=prompt_used
        )
        
        if entry_id:
            print(f"Journal entry saved successfully with ID: {entry_id}")
            return jsonify({
                'status': 'success',
                'entry_id': entry_id,
                'detected_emotion': emotion,
                'sentiment_score': sentiment_score
            })
        else:
            print("Failed to save journal entry - no entry_id returned")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save journal entry'
            }), 500
    except Exception as e:
        print(f"Exception in save_journal: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/journal/entries', methods=['GET'])
def get_journal_entries():
    # Get the session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({
            'status': 'error',
            'message': 'No active session'
        }), 401
    
    # Get pagination parameters
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get journal entries from the database
    entries = db.get_journal_entries(session_id, limit, offset)
    
    return jsonify({
        'status': 'success',
        'entries': entries
    })

@app.route('/journal/entry/<int:entry_id>', methods=['GET'])
def get_journal_entry(entry_id):
    # Get the session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({
            'status': 'error',
            'message': 'No active session'
        }), 401
    
    # Get journal entry from the database
    entry = db.get_entry_by_id(entry_id, session_id)
    
    if entry:
        return jsonify({
            'status': 'success',
            'entry': entry
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Entry not found'
        }), 404

@app.route('/journal/prompt', methods=['GET'])
def get_journal_prompt():
    # Get emotion parameter if provided
    emotion = request.args.get('emotion', None)
    
    # Get a random prompt from the database
    prompt = db.get_random_prompt(emotion)
    
    return jsonify({
        'status': 'success',
        'prompt': prompt
    })

@app.route('/journal/favorite/<int:entry_id>', methods=['POST'])
def toggle_favorite(entry_id):
    # Get the session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({
            'status': 'error',
            'message': 'No active session'
        }), 401
    
    # Toggle favorite status in the database
    success = db.toggle_favorite(entry_id, session_id)
    
    if success:
        return jsonify({
            'status': 'success',
            'message': 'Favorite status toggled'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to toggle favorite status'
        }), 500

@app.route('/journal/analytics', methods=['GET'])
def get_journal_analytics():
    # Get the session ID
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({
            'status': 'error',
            'message': 'No active session'
        }), 401
    
    # Get days parameter if provided
    days = request.args.get('days', 30, type=int)
    
    # Get mood analytics from the database
    analytics = db.get_mood_analytics(session_id, days)
    
    return jsonify({
        'status': 'success',
        'analytics': analytics
    })

def get_recommendations(emotion):
    """Get content recommendations based on detected emotion"""
    # Map emotions from our system to those in mood_rec.py
    emotion_mapping = {
        # Direct mappings
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "neutral": "neutral",
        "surprised": "surprise",
        "anxious": "fear",
        "disgusted": "disgust",
        
        # Additional mappings for emotions not directly in mood_rec
        "frustrated": "angry",
        "confused": "neutral",
        "hopeful": "happy",
        "grateful": "happy",
        "lonely": "sad",
        "overwhelmed": "fear",
        "excited": "happy",
        "calm": "neutral",
        "nervous": "fear",
        "proud": "happy",
        "disappointed": "sad",
        "worried": "fear",
        "stressed": "fear",
        "relaxed": "neutral",
        "content": "happy"
    }
    
    # Map the detected emotion to the mood_rec emotion system
    mapped_emotion = emotion_mapping.get(emotion.lower(), "neutral")
    
    # Get recommendations for the mapped emotion
    recommendations = emotion_to_content.get(mapped_emotion, emotion_to_content["neutral"])
    
    return recommendations

@app.route('/reset', methods=['POST'])
def reset_conversation():
    session_id = session.get('session_id')
    if session_id and session_id in coach_instances:
        coach_instances[session_id].reset_conversation()
        return jsonify({'status': 'success', 'message': 'Conversation reset'})
    return jsonify({'status': 'error', 'message': 'Session not found'}), 404

@app.route('/history', methods=['GET'])
def get_history():
    session_id = session.get('session_id')
    if session_id and session_id in coach_instances:
        coach = coach_instances[session_id]
        return jsonify({
            'history': coach.get_conversation_history(),
            'emotions': coach.get_emotion_history()
        })
    return jsonify({'status': 'error', 'message': 'Session not found'}), 404

# Clean up inactive sessions periodically
@app.before_request
def cleanup_inactive_sessions():
    # This would typically involve checking timestamps and removing old sessions
    # For simplicity, we're just ensuring the dict doesn't grow too large
    if len(coach_instances) > 1000:  # Arbitrary limit
        # Remove oldest sessions (we would normally use timestamps)
        oldest_keys = list(coach_instances.keys())[:100]
        for key in oldest_keys:
            if key in coach_instances:
                del coach_instances[key]

@app.route('/breathing')
def breathing_exercise():
    # Create a unique session ID if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Get the user's current emotion from the coach if available
    current_emotion = "neutral"
    session_id = session.get('session_id')
    if session_id and session_id in coach_instances:
        current_emotion = coach_instances[session_id].get_current_emotion()
    
    # Get recommended exercise type based on emotion
    recommended_exercise = ar_exercise.get_exercise_for_emotion(current_emotion)
    
    # Get exercise types and descriptions
    exercise_types = ar_exercise.get_exercise_instructions()
    
    # Get detailed info for the recommended exercise
    exercise_info = ar_exercise.get_exercise_instructions(recommended_exercise)
    
    return render_template('breathing.html', 
                          emotion=current_emotion,
                          recommended_exercise=recommended_exercise,
                          exercise_types=exercise_types,
                          exercise_info=exercise_info)

@app.route('/breathing/info')
def breathing_exercise_info():
    # Get exercise type from query parameter
    exercise_type = request.args.get('type', 'focus')
    
    # Get detailed info for the exercise
    exercise_info = ar_exercise.get_exercise_instructions(exercise_type)
    
    return jsonify(exercise_info)

@app.route('/video_feed')
def video_feed():
    # Get exercise type from query parameter
    exercise_type = request.args.get('type', 'focus')
    
    # Get the user's current emotion from the coach if available
    current_emotion = "neutral"
    session_id = session.get('session_id')
    if session_id and session_id in coach_instances:
        current_emotion = coach_instances[session_id].get_current_emotion()
    
    # Return the video feed response
    return ar_exercise.get_video_feed(current_emotion, exercise_type)

@app.route('/breathing/toggle_mode')
def toggle_breathing_mode():
    # Toggle between guided and detected breathing modes
    ar_exercise.breathing_guided = not ar_exercise.breathing_guided
    return jsonify({'guided': ar_exercise.breathing_guided})

@app.route('/emotion_feed')
def emotion_video_feed():
    """Route for emotion recognition camera feed"""
    return emotion_feed.get_video_feed()

if __name__ == '__main__':
    # Create templates folder if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Delete the database file if it exists and is corrupt
    try:
        import sqlite3
        conn = sqlite3.connect('journal.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sqlite_master')
        conn.close()
        print("Database verified successfully")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        try:
            import os
            if os.path.exists('journal.db'):
                print("Attempting to delete corrupt database")
                os.remove('journal.db')
                print("Deleted corrupt database, a new one will be created")
        except Exception as del_error:
            print(f"Could not delete database: {del_error}")
        
    print(f"Starting Flask app with Empathetic Gemini AI. Using API key: {api_key[:5]}...")
    app.run(debug=True) 