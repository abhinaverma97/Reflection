import cv2
import time
from deepface import DeepFace
from flask import Response
import numpy as np

class EmotionRecognitionFeed:
    def __init__(self):
        # Load face cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Define emotion labels
        self.emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
        
        # Variables for FPS calculation
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0
        
        # Current emotion tracking
        self.current_emotion = "neutral"
        self.emotion_confidence = 0.0
    
    def get_current_emotion(self):
        """Return the currently detected emotion"""
        return self.current_emotion
    
    def generate_frames(self):
        """Generate video frames with emotion recognition for streaming"""
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            return
        
        while True:
            # Capture frame from webcam
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame from webcam.")
                break
            
            # Calculate FPS
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= 1.0:
                self.fps = self.frame_count / elapsed_time
                self.frame_count = 0
                self.start_time = time.time()
            
            # Make a copy of the frame for display
            display_frame = frame.copy()
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            
            # Process each face
            for (x, y, w, h) in faces:
                try:
                    # Analyze emotions using DeepFace
                    result = DeepFace.analyze(frame, 
                                             actions=['emotion'],
                                             enforce_detection=False,
                                             detector_backend='opencv')
                    
                    # Extract emotions
                    emotions = result[0]['emotion']
                    dominant_emotion = result[0]['dominant_emotion']
                    
                    # Update current emotion
                    self.current_emotion = dominant_emotion
                    self.emotion_confidence = emotions[dominant_emotion]
                    
                    # Draw rectangle around face
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Display dominant emotion
                    text = f"{dominant_emotion}: {emotions[dominant_emotion]:.2f}"
                    cv2.putText(display_frame, text, (x, y-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    
                    # Display all emotion scores
                    y_offset = y + h + 15
                    for emotion, score in emotions.items():
                        emotion_text = f"{emotion}: {score:.2f}"
                        cv2.putText(display_frame, emotion_text, (x, y_offset), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
                        y_offset += 25
                        
                except Exception as e:
                    print(f"Error in emotion analysis: {e}")
                    # Just draw rectangle in case of error
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(display_frame, "Error analyzing", (x, y-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display FPS on the frame
            cv2.putText(display_frame, f"FPS: {self.fps:.1f}", (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Convert to jpg for streaming
            ret, buffer = cv2.imencode('.jpg', display_frame)
            frame_bytes = buffer.tobytes()
            
            # Yield the frame for streaming
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    def get_video_feed(self):
        """Return a response for video streaming"""
        return Response(
            self.generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        ) 