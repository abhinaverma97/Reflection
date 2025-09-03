import cv2
import numpy as np
import time
import math
import mediapipe as mp
import os
import json
from flask import Response

class ARBreathingExercise:
    def __init__(self):
        # Initialize mediapipe pose detection for breathing monitoring
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Breathing exercise parameters
        self.exercise_duration = 180  # 3 minutes
        self.breathing_patterns = {
            "calm": {"inhale": 4, "hold": 4, "exhale": 6, "pause": 2, "color": (0, 255, 0)},  # Green
            "energize": {"inhale": 6, "hold": 0, "exhale": 2, "pause": 0, "color": (0, 165, 255)},  # Orange
            "focus": {"inhale": 4, "hold": 7, "exhale": 8, "pause": 0, "color": (0, 0, 255)},  # Red
            "sleep": {"inhale": 4, "hold": 0, "exhale": 7, "pause": 0, "color": (128, 0, 128)},  # Purple
            "stress": {"inhale": 5, "hold": 0, "exhale": 5, "pause": 0, "color": (255, 255, 0)}  # Cyan
        }
        
        # Variables for breath detection
        self.shoulder_distances = []
        self.breath_phase = "prepare"  # prepare, inhale, hold, exhale, pause
        self.correct_breathing = True  # Track if user is following correctly
        
    def get_exercise_for_emotion(self, emotion):
        """Select appropriate breathing exercise based on detected emotion"""
        emotion_to_breathing = {
            "happy": "focus",
            "sad": "calm",
            "angry": "calm",
            "anxious": "stress",
            "frustrated": "stress",
            "confused": "focus",
            "hopeful": "energize",
            "grateful": "calm",
            "lonely": "sleep",
            "overwhelmed": "calm",
            "excited": "focus",
            "calm": "calm",
            "nervous": "stress",
            "proud": "energize",
            "disappointed": "calm",
            "neutral": "focus",
            "worried": "stress",
            "stressed": "stress",
            "relaxed": "calm",
            "content": "focus"
        }
        
        # Default to focus breathing if emotion not mapped
        return emotion_to_breathing.get(emotion.lower(), "focus")
    
    def detect_breathing(self, landmarks):
        """Detect if the user is inhaling or exhaling based on chest/shoulder movement"""
        if not landmarks or not landmarks.pose_landmarks:
            return False, None
        
        # Get shoulder landmarks
        left_shoulder = landmarks.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        
        # Calculate distance between shoulders (width)
        shoulder_distance = math.sqrt(
            (right_shoulder.x - left_shoulder.x) ** 2 + 
            (right_shoulder.y - left_shoulder.y) ** 2
        )
        
        # Keep a buffer of recent measurements
        self.shoulder_distances.append(shoulder_distance)
        if len(self.shoulder_distances) > 30:  # Keep last 30 frames (1 second at 30fps)
            self.shoulder_distances.pop(0)
        
        # Need at least 10 frames to detect trends
        if len(self.shoulder_distances) < 10:
            return False, None
        
        # Calculate trend (increasing = inhaling, decreasing = exhaling)
        recent_trend = self.shoulder_distances[-1] - self.shoulder_distances[-10]
        
        # Update breath phase based on shoulder movement
        if recent_trend > 0.002:  # Positive trend = expanding chest = inhaling
            return True, "inhale"
        elif recent_trend < -0.002:  # Negative trend = contracting chest = exhaling
            return True, "exhale"
        else:  # Stable = holding or pausing
            return True, "hold"

    def generate_frames(self, emotion="neutral", exercise_type=None):
        """Generate video frames for streaming"""
        if not exercise_type:
            exercise_type = self.get_exercise_for_emotion(emotion)
        
        pattern = self.breathing_patterns[exercise_type]
        
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            return
        
        # Set up variables for breathing cycle
        start_time = time.time()
        cycle_time = pattern["inhale"] + pattern["hold"] + pattern["exhale"] + pattern["pause"]
        cycle_count = 0
        
        while True:
            success, image = cap.read()
            if not success:
                break
            
            # Flip the image horizontally for a selfie-view
            image = cv2.flip(image, 1)
            
            # Convert the image to RGB for processing
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process the image with pose detection
            pose_results = self.pose.process(image_rgb)
            
            # Calculate current position in breathing cycle based on time
            elapsed_time = time.time() - start_time
            total_cycles = elapsed_time / cycle_time
            cycle_count = int(total_cycles)
            
            # Determine current phase in breathing cycle
            phase_time = elapsed_time % cycle_time
            
            # Get image dimensions
            h, w, _ = image.shape
            
            # Track the expected breathing phase based on timer
            if phase_time < pattern["inhale"]:
                expected_phase = "inhale"
                progress = phase_time / pattern["inhale"]
                instruction = f"INHALE through nose ({int(pattern['inhale'] - phase_time + 1)}s)"
                
                # Simple AR visualization - breathing circle outline
                circle_size = int(50 + progress * 100)
                cv2.circle(image, (w//2, 100), circle_size, pattern["color"], 2)
                
            elif phase_time < pattern["inhale"] + pattern["hold"] and pattern["hold"] > 0:
                expected_phase = "hold"
                hold_time = phase_time - pattern["inhale"] 
                progress = hold_time / pattern["hold"]
                instruction = f"HOLD your breath ({int(pattern['hold'] - hold_time + 1)}s)"
                
                # Simple AR visualization - constant circle
                cv2.circle(image, (w//2, 100), 150, pattern["color"], 2)
                
            elif phase_time < pattern["inhale"] + pattern["hold"] + pattern["exhale"]:
                expected_phase = "exhale"
                exhale_time = phase_time - pattern["inhale"] - pattern["hold"]
                progress = exhale_time / pattern["exhale"]
                instruction = f"EXHALE through mouth ({int(pattern['exhale'] - exhale_time + 1)}s)"
                
                # Simple AR visualization - shrinking circle
                circle_size = int(150 - progress * 100)
                cv2.circle(image, (w//2, 100), circle_size, pattern["color"], 2)
                
            else:
                expected_phase = "pause"
                pause_time = phase_time - pattern["inhale"] - pattern["hold"] - pattern["exhale"]
                progress = pause_time / pattern["pause"] if pattern["pause"] > 0 else 1
                instruction = f"PAUSE ({int(pattern['pause'] - pause_time + 1)}s)"
                
                # Simple AR visualization - small circle
                cv2.circle(image, (w//2, 100), 50, pattern["color"], 2)
            
            # Detect the user's actual breathing phase
            detected_valid, detected_phase = self.detect_breathing(pose_results)
            
            # Check if user is breathing correctly (following the guidance)
            if detected_valid:
                if (expected_phase == "inhale" and detected_phase == "inhale") or \
                   (expected_phase == "exhale" and detected_phase == "exhale") or \
                   ((expected_phase == "hold" or expected_phase == "pause") and detected_phase == "hold"):
                    self.correct_breathing = True
                    feedback = "Good!"
                else:
                    self.correct_breathing = False
                    if expected_phase == "inhale" and detected_phase != "inhale":
                        feedback = "Inhale now"
                    elif expected_phase == "exhale" and detected_phase != "exhale":
                        feedback = "Exhale now"
                    elif expected_phase == "hold" and detected_phase != "hold":
                        feedback = "Hold steady"
                    else:
                        feedback = "Pause briefly"
            else:
                feedback = ""
            
            # Draw simple clean progress bar at the bottom
            progress_bar_y = h - 30
            cv2.rectangle(image, (50, progress_bar_y), (w-50, progress_bar_y + 5), (200, 200, 200), -1)
            
            # Calculate progress within the current phase
            if expected_phase == "inhale":
                phase_progress = progress
            elif expected_phase == "hold":
                phase_progress = progress
            elif expected_phase == "exhale":
                phase_progress = progress
            else:  # pause
                phase_progress = progress
            
            # Calculate overall cycle progress
            cycle_progress = (phase_time / cycle_time)
            progress_width = int((w-100) * cycle_progress)
            cv2.rectangle(image, (50, progress_bar_y), (50 + progress_width, progress_bar_y + 5), 
                         pattern["color"], -1)
            
            # Add text instructions - simple, clean text at the top
            font = cv2.FONT_HERSHEY_SIMPLEX
            
            # Add light text background for better visibility
            text_size = cv2.getTextSize(instruction, font, 0.8, 2)[0]
            text_x = (w - text_size[0]) // 2
            cv2.rectangle(image, (text_x - 10, 30), 
                         (text_x + text_size[0] + 10, 60), 
                         (255, 255, 255), -1)
            
            # Instruction text
            cv2.putText(image, instruction, (text_x, 50), font, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
            
            # Add simple exercise name at top left
            cv2.putText(image, f"{exercise_type.capitalize()} Breathing", (20, 25), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Add cycle count at top right
            cv2.putText(image, f"Cycle: {cycle_count+1}", (w-150, 25), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Add feedback if available
            if feedback:
                feedback_color = (0, 255, 0) if self.correct_breathing else (0, 0, 255)
                cv2.putText(image, feedback, (w//2 - 40, h - 50), font, 0.7, feedback_color, 2, cv2.LINE_AA)
            
            # Convert to jpg for streaming
            ret, buffer = cv2.imencode('.jpg', image)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # Check if exercise duration is complete
            if elapsed_time >= self.exercise_duration:
                break
            
        # Clean up
        cap.release()

    def get_video_feed(self, emotion="neutral", exercise_type=None):
        """Return a response for video streaming"""
        if not exercise_type:
            exercise_type = self.get_exercise_for_emotion(emotion)
            
        return Response(
            self.generate_frames(emotion, exercise_type),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    def get_exercise_instructions(self, exercise_type=None):
        """Get instructions for a specific exercise type"""
        if not exercise_type:
            # Return all exercise types and their descriptions
            return {
                "calm": "Deep breathing for relaxation and stress reduction",
                "energize": "Quick breathing pattern to boost energy",
                "focus": "Balanced breathing to improve concentration",
                "sleep": "Extended exhale pattern to promote sleep",
                "stress": "Equal breathing pattern to manage acute stress"
            }
        
        instructions = {
            "calm": {
                "name": "Calm Breathing (4-4-6-2)",
                "description": "A relaxing breath pattern to reduce stress and anxiety",
                "steps": [
                    "Inhale deeply through your nose for 4 seconds",
                    "Hold your breath for 4 seconds",
                    "Exhale slowly through your mouth for 6 seconds",
                    "Pause for 2 seconds before the next breath"
                ],
                "benefits": [
                    "Reduces anxiety and stress",
                    "Lowers blood pressure",
                    "Promotes mental clarity",
                    "Helps with emotional regulation"
                ]
            },
            "energize": {
                "name": "Energizing Breath (6-0-2-0)",
                "description": "A stimulating breath pattern to increase energy and alertness",
                "steps": [
                    "Inhale deeply and quickly through your nose for 6 seconds",
                    "Exhale forcefully through your mouth for 2 seconds"
                ],
                "benefits": [
                    "Increases energy and alertness",
                    "Improves focus and concentration",
                    "Helps overcome afternoon fatigue",
                    "Prepares the mind for challenging tasks"
                ]
            },
            "focus": {
                "name": "Focus Breath (4-7-8-0)",
                "description": "A balancing breath pattern to improve concentration and focus",
                "steps": [
                    "Inhale through your nose for 4 seconds",
                    "Hold your breath for 7 seconds",
                    "Exhale completely through your mouth for 8 seconds"
                ],
                "benefits": [
                    "Improves concentration",
                    "Reduces distractions",
                    "Calms an overactive mind",
                    "Increases oxygen to the brain"
                ]
            },
            "sleep": {
                "name": "Sleep Breath (4-0-7-0)",
                "description": "A relaxing breath pattern to promote sleep and relaxation",
                "steps": [
                    "Inhale through your nose for 4 seconds",
                    "Exhale slowly through your mouth for 7 seconds"
                ],
                "benefits": [
                    "Helps transition to sleep",
                    "Reduces insomnia",
                    "Calms the nervous system",
                    "Releases physical tension"
                ]
            },
            "stress": {
                "name": "Stress Relief Breath (5-0-5-0)",
                "description": "A balanced breath pattern to manage acute stress",
                "steps": [
                    "Inhale through your nose for 5 seconds",
                    "Exhale through your mouth for 5 seconds"
                ],
                "benefits": [
                    "Immediately reduces stress response",
                    "Balances the autonomic nervous system",
                    "Improves heart rate variability",
                    "Creates a sense of control during stressful situations"
                ]
            }
        }
        
        return instructions.get(exercise_type, instructions["focus"])
