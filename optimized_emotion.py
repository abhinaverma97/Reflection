import cv2
import time
import numpy as np
from deepface import DeepFace

def main():
    # Configuration options
    process_every_n_frames = 3  # Process emotion every N frames for better performance
    
    # Load face cascade for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Initialize webcam
    print("Initializing webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Variables for FPS calculation
    frame_count = 0
    start_time = time.time()
    fps = 0
    
    # Variables to store emotion results between processing frames
    last_emotions = None
    last_dominant_emotion = None
    face_locations = []
    frame_counter = 0
    
    print("Optimized emotion recognition started! Press 'q' to quit.")
    
    while True:
        # Capture frame from webcam
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame from webcam.")
            break
        
        # Calculate FPS
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:
            fps = frame_count / elapsed_time
            frame_count = 0
            start_time = time.time()
        
        # Make a copy of the frame for display
        display_frame = frame.copy()
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces every frame
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        face_locations = [(x, y, w, h) for (x, y, w, h) in faces]
        
        # Process emotions only every N frames or if we don't have results yet
        if frame_counter % process_every_n_frames == 0 or last_emotions is None:
            if len(face_locations) > 0:
                try:
                    # Analyze emotions using DeepFace
                    result = DeepFace.analyze(frame, 
                                             actions=['emotion'],
                                             enforce_detection=False,
                                             detector_backend='opencv')
                    
                    if result:
                        # Extract emotions
                        last_emotions = result[0]['emotion']
                        last_dominant_emotion = result[0]['dominant_emotion']
                except Exception as e:
                    print(f"Error in emotion analysis: {e}")
                    last_emotions = None
                    last_dominant_emotion = None
        
        # Display results
        for i, (x, y, w, h) in enumerate(face_locations):
            # Draw rectangle around face
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            if last_emotions is not None and last_dominant_emotion is not None:
                # Display dominant emotion
                text = f"{last_dominant_emotion}: {last_emotions[last_dominant_emotion]:.2f}"
                cv2.putText(display_frame, text, (x, y-10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                
                # Display all emotion scores
                y_offset = y + h + 15
                for emotion, score in last_emotions.items():
                    emotion_text = f"{emotion}: {score:.2f}"
                    cv2.putText(display_frame, emotion_text, (x, y_offset), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
                    y_offset += 20
            else:
                # Display message if no emotion data available
                cv2.putText(display_frame, "Analyzing...", (x, y-10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Increment frame counter
        frame_counter += 1
        
        # Display FPS and processing info on the frame
        cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(display_frame, f"Processing: {1 if frame_counter % process_every_n_frames == 0 else 0}", 
                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display the frame
        cv2.imshow('Optimized Emotion Recognition', display_frame)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print("Emotion recognition stopped.")

if __name__ == "__main__":
    main() 