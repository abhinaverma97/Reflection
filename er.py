import cv2
import time
from deepface import DeepFace

def main():
    # Load face cascade for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Define emotion labels
    emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
    
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
    
    print("Emotion recognition started! Press 'q' to quit.")
    
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
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        
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
        cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display the frame
        cv2.imshow('Facial Emotion Recognition', display_frame)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print("Emotion recognition stopped.")

if __name__ == "__main__":
    main() 