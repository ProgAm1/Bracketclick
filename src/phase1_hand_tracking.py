# src/phase1_hand_tracking.py - BracketClick Phase 1
# ✅ Basic hand tracking + manual spacebar trigger
# ✅ Import config from shared config.py

import cv2
import numpy as np
import json
import os
import datetime
import time
import sys

# ✅ Import config from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.gesture_engine import HandAnalyzer

# ==================== UTILITIES ====================
# (calculate_angle kept for reference; HandAnalyzer from gesture_engine)
def calculate_angle(a, b, c):
    """Calculate angle between three points (A-B-C) in degrees."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    norm_ba = ba / (np.linalg.norm(ba) + 1e-8)
    norm_bc = bc / (np.linalg.norm(bc) + 1e-8)
    dot = np.clip(np.dot(norm_ba, norm_bc), -1.0, 1.0)
    return float(np.degrees(np.arccos(dot)))

def ensure_dirs():
    """Create capture and log directories if they don't exist."""
    os.makedirs(config.CAPTURE_FOLDER, exist_ok=True)
    os.makedirs(config.LOG_FOLDER, exist_ok=True)

def load_log():
    """Load existing JSON log or return empty list."""
    if os.path.exists(config.LOG_FILE):
        try:
            with open(config.LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_log(data):
    """Save data to JSON log file."""
    with open(config.LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==================== PHOTO BOOTH ====================
class PhotoBooth:
    """Main application loop: camera, UI, capture, logging."""
    
    def __init__(self, email):
        self.email = email
        self.analyzer = HandAnalyzer(config.MODEL_PATH)
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.FPS)
        self.counting = False
        self.count_start = 0
        self.count_val = 3
        self.clean_frame = None
        ensure_dirs()
        print(f"[DEBUG] Capture folder: {os.path.abspath(config.CAPTURE_FOLDER)}")
        print(f"[DEBUG] Log file: {os.path.abspath(config.LOG_FILE)}")

    def draw(self, frame, hands):
        """Draw landmarks, connections, angles, and debug info on frame."""
        for hand in hands:
            lms = hand['landmarks']
            angles = self.analyzer.get_angles(lms)
            bracket_angle = self.analyzer.get_finger_angle(lms)
            
            # Draw finger connection lines (green)
            for i, j in config.INDEX_CONNECTIONS:
                if i < len(lms) and j < len(lms):
                    cv2.line(frame, lms[i], lms[j], config.CONNECTION_COLOR, 2)
            
            for i, j in config.MIDDLE_CONNECTIONS:
                if i < len(lms) and j < len(lms):
                    cv2.line(frame, lms[i], lms[j], config.CONNECTION_COLOR, 2)
            
            # Draw main vector lines (cyan, thicker)
            if len(lms) > 12:
                cv2.line(frame, lms[5], lms[8], config.VECTOR_COLOR, 3)
                cv2.line(frame, lms[9], lms[12], config.VECTOR_COLOR, 3)
            
            # Display bracket angle
            if len(lms) > 12:
                cv2.putText(frame, f"Bracket:{int(bracket_angle)}°", 
                           (lms[0][0]-40, lms[0][1]-45),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.BRACKET_COLOR, 2)
            
            # Highlight all joint points (red circles)
            for idx in config.HIGHLIGHT_INDICES:
                if idx < len(lms):
                    x, y = lms[idx]
                    cv2.circle(frame, (x, y), 6, config.HIGHLIGHT_COLOR, -1)
                    cv2.putText(frame, str(idx), (x+8, y-8), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, config.TEXT_COLOR, 1)
            
            # Display joint angles
            if len(lms) > 10:
                cv2.putText(frame, f"Idx:{int(angles.get('idx',0))}°", 
                           (lms[6][0]-40, lms[6][1]+30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
                cv2.putText(frame, f"Mid:{int(angles.get('mid',0))}°", 
                           (lms[10][0]-40, lms[10][1]+30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
            
            # Display hand side
            if lms:
                cv2.putText(frame, hand['side'], (lms[0][0]-25, lms[0][1]-15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, config.COUNTDOWN_COLOR, 2)

    def countdown(self, frame):
        """Draw 3-second countdown overlay at TOP of screen."""
        h, w, _ = frame.shape
        cx, cy = w//2, h//4  # Top-center
        
        if self.count_val == 1:
            self.clean_frame = frame.copy()
        
        cv2.circle(frame, (cx, cy), 80, config.COUNTDOWN_COLOR, -1)
        cv2.putText(frame, str(self.count_val), (cx-20, cy+30),
                   cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 8)
        
        if time.time() - self.count_start >= 1.0:
            self.count_val -= 1
            self.count_start = time.time()
            if self.count_val < 0:
                self.counting = False
                if self.clean_frame is not None:
                    self.capture(self.clean_frame)
                    self.clean_frame = None
                self.count_val = 3

    def capture(self, frame):
        """Save image and log participant data."""
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"capture_{ts}.jpg"
            fpath = os.path.join(config.CAPTURE_FOLDER, fname)
            print(f"\n[DEBUG] Saving to: {fpath}")
            success = cv2.imwrite(fpath, frame)
            if not success:
                raise Exception("cv2.imwrite returned False")
            print(f"[OK] Saved: {fname}")
            entry = {"email": self.email, "filename": fname, "timestamp": ts, "path": fpath}
            log = load_log()
            log.append(entry)
            save_log(log)
            print(f"[OK] Logged: {self.email}")
        except Exception as e:
            print(f"[ERROR] Capture failed: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Main application loop."""
        print(f"\n{'='*50}")
        print(f"   BracketClick Phase 1: Hand Tracking")
        print(f"{'='*50}")
        print(f"[OK] Email: {self.email}")
        print(f"[OK] Press SPACE or 'c' to capture")
        print(f"[OK] Press 'q' to quit\n")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[ERROR] Camera error")
                break
            
            results = self.analyzer.process(frame)
            hands = self.analyzer.get_landmarks(results, frame.shape[1], frame.shape[0])
            
            if len(hands) > 0:
                hand_labels = [h['side'] for h in hands]
                print(f"[DEBUG] Hands: {len(hands)} | {hand_labels}", end='\r')
            
            self.draw(frame, hands)
            
            if self.counting:
                self.countdown(frame)
            else:
                cv2.putText(frame, "Press SPACE or C to Capture", (20, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, config.TEXT_COLOR, 2)
            
            cv2.imshow("BracketClick - Phase 1", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[DEBUG] Quit key pressed")
                break
            if key in config.TRIGGER_KEYS and not self.counting:
                print(f"\n[DEBUG] Trigger key pressed (code: {key})")
                self.counting = True
                self.count_start = time.time()
                self.count_val = 3
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n[OK] Done")

# ==================== MAIN ====================
def main():
    print("="*50)
    print("   BracketClick - Phase 1: Hand Tracking")
    print("="*50)
    email = input("Enter participant email: ").strip()
    try:
        booth = PhotoBooth(email)
        booth.run()
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("Download model from:")
        print("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()