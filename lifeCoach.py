import os
import google.generativeai as genai
import re
import json

class LifeCoach:
    def __init__(self, api_key=""):
        """Initialize the LifeCoach with the Gemini API."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.chat = self.model.start_chat(history=[])
        self.conversation_history = []
        self.user_emotions = []
        self.current_emotion = "neutral"
        
        # List of emotions we want to track
        self.emotion_categories = [
            "happy", "sad", "angry", "anxious", "frustrated", 
            "confused", "hopeful", "grateful", "lonely", "overwhelmed",
            "excited", "calm", "nervous", "proud", "disappointed",
            "neutral", "worried", "stressed", "relaxed", "content"
        ]
        
        # Empathetic response templates for different emotions
        self.empathetic_responses = {
            "happy": [
                "That sounds wonderful! I'm glad to hear you're feeling happy.",
                "It's great that you're feeling positive. What's contributing to your happiness?"
            ],
            "sad": [
                "I'm sorry to hear you're feeling down. Would you like to talk more about what's troubling you?",
                "It sounds like you're going through a difficult time. Remember that it's okay to feel sad sometimes."
            ],
            "angry": [
                "I can understand why that would be frustrating. It's natural to feel angry in that situation.",
                "That sounds really challenging. How can I help you process these feelings?"
            ],
            "anxious": [
                "It sounds like you're feeling anxious. Taking slow, deep breaths might help in the moment.",
                "Anxiety can be really difficult to manage. What typically helps you when you're feeling this way?"
            ],
            "neutral": [
                "I'm here to listen and support you. How else can I help today?",
                "Thank you for sharing. I'm here to chat whenever you need."
            ]
        }
    
    def reset_conversation(self):
        """Reset the conversation history and emotion tracking."""
        self.conversation_history = []
        self.user_emotions = []
        self.current_emotion = "neutral"
        self.chat = self.model.start_chat(history=[])
    
    def detect_emotion(self, message):
        """Detect the user's emotion based on their message using Gemini."""
        try:
            # Craft a specific prompt for emotion detection
            emotion_prompt = f"""
            Analyze the emotional tone in this message and identify the primary emotion the person is expressing.
            Choose only ONE emotion from this list: {", ".join(self.emotion_categories)}
            
            Message: "{message}"
            
            Return your answer as a JSON object with this format:
            {{
              "emotion": "the_detected_emotion",
              "confidence": 0-10,
              "explanation": "brief explanation of why this emotion was detected"
            }}
            
            Just return the JSON object and nothing else.
            """
            
            # Get emotion analysis from Gemini
            emotion_response = self.model.generate_content(emotion_prompt)
            
            # Extract JSON from the response
            json_match = re.search(r'\{.*\}', emotion_response.text, re.DOTALL)
            if json_match:
                emotion_data = json.loads(json_match.group(0))
                detected_emotion = emotion_data.get("emotion", "neutral").lower()
                
                # Ensure the detected emotion is in our list
                if detected_emotion not in self.emotion_categories:
                    detected_emotion = "neutral"
                
                return detected_emotion, emotion_data.get("confidence", 5), emotion_data.get("explanation", "")
            return "neutral", 5, "No clear emotion detected"
        except Exception as e:
            print(f"Error detecting emotion: {str(e)}")
            return "neutral", 5, "Error in emotion detection"
    
    def craft_empathetic_response_prompt(self, message, emotion):
        """Craft a prompt that guides the model to generate an empathetic response."""
        # Build system prompt based on detected emotion
        empathetic_guidance = f"""
        The user appears to be feeling {emotion}. 
        
        Respond in an empathetic way that acknowledges their feelings without explicitly labeling their emotion.
        Be supportive, compassionate, and understanding.
        Keep your response conversational and natural.
        Avoid being judgmental or dismissive of their feelings.
        Provide gentle guidance or support if appropriate.
        
        User message: "{message}"
        
        Your empathetic response:
        """
        return empathetic_guidance
    
    def get_response(self, message):
        """Get an empathetic response from the Gemini model based on the user's message.
        
        Args:
            message (str): The user's message.
            
        Returns:
            str: The AI's empathetic response.
        """
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": message})
            
            # Detect emotion in the user's message
            emotion, confidence, explanation = self.detect_emotion(message)
            self.current_emotion = emotion
            
            # Track emotion history
            self.user_emotions.append({
                "emotion": emotion,
                "confidence": confidence,
                "explanation": explanation,
                "message": message
            })
            
            # Create prompt for empathetic response
            empathetic_prompt = self.craft_empathetic_response_prompt(message, emotion)
            
            # Get response from Gemini with empathetic guidance
            empathetic_response = self.model.generate_content(empathetic_prompt)
            response_text = empathetic_response.text
            
            # Add AI response to history
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            return response_text
        except Exception as e:
            # Fallback response in case of error
            fallback_response = "I'm here to listen. Would you like to share more about how you're feeling?"
            self.conversation_history.append({"role": "assistant", "content": fallback_response})
            return fallback_response
    
    def get_conversation_history(self):
        """Return the conversation history."""
        return self.conversation_history
    
    def update_conversation_history(self, message, role):
        """Update the conversation history without generating a response.
        
        Args:
            message (str): The message to add to the history.
            role (str): Either 'user' or 'assistant'.
        """
        if role not in ['user', 'assistant']:
            return
            
        # Add to the conversation history
        self.conversation_history.append({"role": role, "content": message})
        
        # If this is a user message, try to detect emotion silently
        if role == 'user':
            try:
                emotion, confidence, explanation = self.detect_emotion(message)
                self.current_emotion = emotion
                
                # Track emotion history
                self.user_emotions.append({
                    "emotion": emotion,
                    "confidence": confidence,
                    "explanation": explanation,
                    "message": message
                })
            except:
                # Ignore errors in emotion detection for history updates
                pass
    
    def get_current_emotion(self):
        """Return the currently detected emotion."""
        return self.current_emotion
    
    def get_emotion_history(self):
        """Return the full emotion history."""
        return self.user_emotions


# Example usage
if __name__ == "__main__":
    # Use environment variable if available, otherwise use default key
    api_key = os.environ.get('GEMINI_API_KEY', "AIzaSyCrGgr7E9k_XHp2TsUlPW4BYWJjFjhY5WQ")
    coach = LifeCoach(api_key=api_key)
    print("EmpatheticAI: Hello, I'm here to chat with you. How are you feeling today?")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("EmpatheticAI: Take care. I'm here if you need to talk again.")
            break
            
        response = coach.get_response(user_input)
        print(f"EmpatheticAI: {response}")
        print(f"[Current emotion: {coach.get_current_emotion()}]")  # Only for demo, not shown in production


#

