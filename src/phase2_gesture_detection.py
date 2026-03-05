# src/phase2_gesture_detection.py - DEBUG VERSION
# Shows all angle values to help debug gesture detection
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
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    norm_ba = ba / (np.linalg.norm(ba) + 1e-8)
    norm_bc = bc / (np.linalg.norm(bc) + 1e-8)
    dot = np.clip(np.dot(norm_ba, norm_bc), -1.0, 1.0)
    return float(np.degrees(np.arccos(dot)))

def ensure_dirs():
    os.makedirs(config.CAPTURE_FOLDER, exist_ok=True)
    os.makedirs(config.LOG_FOLDER, exist_ok=True)

def load_log():
    if os.path.exists(config.LOG_FILE):
        try:
            with open(config.LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_log(data):
    with open(config.LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==================== PHOTO BOOTH ====================
class PhotoBooth:
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
        self.gesture_detected = False
        # ✅ NEW: Cooldown variables
        self.cooldown_active = False
        self.cooldown_start = 0
        self.cooldown_duration = 3  # 3 seconds cooldown
        # ✅ NEW flags for capture flow
        self.ready_to_capture = False
        self._captured_this_round = False
        self._countdown_finished = False  # ← Add this line

        ensure_dirs()
        print(f"[DEBUG] Capture folder: {os.path.abspath(config.CAPTURE_FOLDER)}")
        print(f"[DEBUG] Log file: {os.path.abspath(config.LOG_FILE)}")

    def draw(self, frame, hands):
        left_bracket = False
        right_bracket = False

        # ✅ Check if cooldown is active
        if self.cooldown_active:
            elapsed = time.time() - self.cooldown_start
            remaining = max(0, self.cooldown_duration - elapsed)
            
            if remaining <= 0:
                self.cooldown_active = False
            else:
                # Display cooldown overlay
                h, w, _ = frame.shape
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 0), -1)
                cv2.putText(frame, f"Wait {int(remaining)+1}...", (w//2-100, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, config.COUNTDOWN_COLOR, 3)
                return

        for hand in hands:
            lms = hand['landmarks']
            side = hand['side']
            
            # ✅ Get gesture info
            is_bracket, bracket_angle, idx_angle, mid_angle, reason, tilt_angle, finger_states = self.analyzer.detect_bracket_gesture(lms, side)

            if side == "Left" and is_bracket:
                left_bracket = True
            elif side == "Right" and is_bracket:
                right_bracket = True
            
            # ==================== Draw Landmark Points (Keep Points) ====================
            for i, (x, y) in enumerate(lms):
                # Index and Middle = Larger colored dots
                if i in [5, 6, 7, 8, 9, 10, 11, 12]:
                    color = config.GESTURE_READY_COLOR if is_bracket else (0, 255, 255)
                    cv2.circle(frame, (x, y), 6, color, -1)
                # Other fingers = Small red dots
                else:
                    cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)
            
            # ==================== Draw Finger Lines ====================
            cv2.line(frame, lms[5], lms[8], config.VECTOR_COLOR, 3)  # Index
            cv2.line(frame, lms[9], lms[12], config.VECTOR_COLOR, 3)  # Middle
            
            # ==================== Display Angles (Near Hand) ====================
            if len(lms) > 12:
                # Bracket angle
                angle_color = config.GESTURE_READY_COLOR if is_bracket else (0, 255, 255)
                cv2.putText(frame, f"<>{int(bracket_angle)}°", 
                           (lms[0][0]-40, lms[0][1]-60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2)
                
                # Index angle
                idx_color = config.GESTURE_READY_COLOR if idx_angle >= 140 else (0, 0, 255)
                cv2.putText(frame, f"Idx:{int(idx_angle)}°", 
                           (lms[6][0]-30, lms[6][1]+30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, idx_color, 2)
                
                # Middle angle
                mid_color = config.GESTURE_READY_COLOR if mid_angle >= 140 else (0, 0, 255)
                cv2.putText(frame, f"Mid:{int(mid_angle)}°", 
                           (lms[10][0]-30, lms[10][1]+30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, mid_color, 2)
            
            # ==================== Display Hand Status (CLEAN STYLE) ====================
            if lms:
                status = "✓" if is_bracket else "✗"
                side_color = config.GESTURE_READY_COLOR if is_bracket else (0, 0, 255)
                # Show: "Left ✓" or "Right ✗"
                cv2.putText(frame, f"{side} {status}", 
                           (lms[0][0]-30, lms[0][1]-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, side_color, 2)
        
        # ==================== Countdown Overlay ====================
        if self.counting and self.count_val > 0:
            h, w, _ = frame.shape
            cx, cy = w//2, h//4
            cv2.circle(frame, (cx, cy), 80, config.COUNTDOWN_COLOR, -1)
            cv2.putText(frame, str(self.count_val), (cx-20, cy+30),
                       cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 8)
        
        # ==================== Overall Gesture Status ====================
        if left_bracket and right_bracket:
            if self.counting:
                cv2.putText(frame, "Hold the gesture...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.COUNTDOWN_COLOR, 3)
            else:
                cv2.putText(frame, "GESTURE DETECTED! Capturing...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.GESTURE_READY_COLOR, 3)
            self.gesture_detected = True
        else:
            cv2.putText(frame, "Form <> with both hands!", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.TEXT_COLOR, 2)
            self.gesture_detected = False

    def countdown(self, frame):
        h, w, _ = frame.shape
        cx, cy = w//2, h//4
        
        # Draw countdown overlay
        cv2.circle(frame, (cx, cy), 80, config.COUNTDOWN_COLOR, -1)
        cv2.putText(frame, str(self.count_val), (cx-20, cy+30),
                   cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 8)
        
        if time.time() - self.count_start >= 1.0:
            self.count_val -= 1
            self.count_start = time.time()
            if self.count_val < 0:
                self.counting = False
                # ✅ Capture the CURRENT frame (without overlays will be handled in capture())
                # We'll capture a fresh frame in run() method instead
                self.count_val = 3

    def capture(self, frame):
        """
        Capture and save photo with GDG watermark
        """
        try:
            # ✅ Create a copy of the frame to add watermark
            watermarked_frame = frame.copy()
            
            # ✅ Get frame dimensions
            h, w, _ = watermarked_frame.shape
            
            # ✅ Common text settings
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_color = (255, 255, 255)  # White text
            
            # ==================== #GDGCUJ Watermark (Top-Left) ====================
            watermark_text = "#GDGCUJ"
            font_scale = 1.2
            font_thickness = 2
            
            # Get text size for positioning
            (text_width, text_height), baseline = cv2.getTextSize(
                watermark_text, font, font_scale, font_thickness
            )
            
            # Position: Top-left corner with padding
            x = 20  # Left padding
            y = text_height + 20  # Top padding
            
            # Draw watermark text
            cv2.putText(
                watermarked_frame,
                watermark_text,
                (x, y),
                font,
                font_scale,
                text_color,
                font_thickness,
                cv2.LINE_AA
            )
            
            # ==================== Email (Bottom-Right) ====================
            if self.email:
                email_text = str(self.email)  # ✅ Just the email address
                email_font_scale = 0.7
                email_font_thickness = 1
                
                (email_width, email_height), baseline = cv2.getTextSize(
                    email_text, font, email_font_scale, email_font_thickness
                )
                
                # Position: Bottom-right corner with padding
                email_x = w - email_width - 20  # Right padding
                email_y = h - 20  # Bottom padding
                
                # Draw email text
                cv2.putText(
                    watermarked_frame,
                    email_text,
                    (email_x, email_y),
                    font,
                    email_font_scale,
                    text_color,
                    email_font_thickness,
                    cv2.LINE_AA
                )
            
            # ✅ Save the watermarked frame
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"capture_{ts}.jpg"
            fpath = os.path.join(config.CAPTURE_FOLDER, fname)
            
            print(f"\n[DEBUG] Saving to: {fpath}")
            success = cv2.imwrite(fpath, watermarked_frame)
            
            if not success:
                raise Exception("cv2.imwrite returned False")
            
            print(f"[OK] Saved: {fname}")
            print(f"[OK] Watermark: #GDGCUJ (top-left), Email (bottom-right)")
            
            # ✅ Save to JSON log
            entry = {
                "email": self.email,
                "filename": fname,
                "timestamp": ts,
                "path": fpath,
                "watermark": "#GDGCUJ"
            }
            log = load_log()
            log.append(entry)
            save_log(log)
            print(f"[OK] Logged: {self.email}")
            
            # ✅ Start cooldown after capture
            self.cooldown_active = True
            self.cooldown_start = time.time()
            print(f"[INFO] Cooldown: {self.cooldown_duration} seconds...")
            
        except Exception as e:
            print(f"[ERROR] Capture failed: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Main application loop."""
        print(f"\n{'='*50}")
        print(f"   BracketClick Phase 2: Gesture Detection (DEBUG)")
        print(f"{'='*50}")
        print(f"[OK] Email: {self.email}")
        print(f"[OK] Form <> with BOTH hands to auto-capture!")
        print(f"[OK] Backup: Press SPACE or 'c' to capture manually")
        print(f"[OK] Press 'q' to quit\n")
        print(f"[INFO] GREEN = Gesture detected ✓")
        print(f"[INFO] RED = Gesture NOT detected ✗")
        print(f"[INFO] Target: Bracket 30°-60°, Fingers >140° (straight)")
        print(f"[INFO] Cooldown: {self.cooldown_duration}s after each capture\n")
        print(f"[DEBUG] Watch terminal for angle values...\n")
        
        frame_count = 0
        gesture_hold_frames = 0
        self.ready_to_capture = False
        self._captured_this_round = False
        self._countdown_finished = False  # ✅ NEW: Track if countdown completed
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[ERROR] Camera error")
                break
            
            frame_count += 1
            
            # ✅ Check and handle cooldown state
            if self.cooldown_active:
                elapsed = time.time() - self.cooldown_start
                remaining = self.cooldown_duration - elapsed
                
                if remaining <= 0:
                    self.cooldown_active = False
                    self._captured_this_round = False
                    self._countdown_finished = False
                    self.gesture_detected = False  # ✅ Reset gesture state
                    print("[INFO] ✓ Ready for next photo!")
                else:
                    # Skip gesture processing during cooldown
                    self.draw(frame, [])
                    cv2.imshow("BracketClick - Phase 2 DEBUG", frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("\n[DEBUG] Quit key pressed")
                        break
                    continue  # Skip rest of loop iteration
            
            # ✅ CAPTURE CLEAN FRAME AFTER COUNTDOWN (before drawing overlays)
            if self.ready_to_capture and not self._captured_this_round:
                ret, clean_frame = self.cap.read()
                if ret:
                    print(f"\n[CAPTURE] Saving clean photo (no overlays)...")
                    self.capture(clean_frame)
                    self._captured_this_round = True
                    self.ready_to_capture = False
                    self._countdown_finished = False
                    # ✅ Start cooldown IMMEDIATELY after capture
                    self.cooldown_active = True
                    self.cooldown_start = time.time()
                continue  # Skip rest of loop after capture
            
            # ✅ Normal processing (only if NOT in cooldown)
            results = self.analyzer.process(frame)
            hands = self.analyzer.get_landmarks(results, frame.shape[1], frame.shape[0])
            
            # ✅ DEBUG: Show detailed hand info in terminal
            if len(hands) > 0:
                for i, hand in enumerate(hands):
                    lms = hand['landmarks']
                    side = hand['side']
                    is_bracket, bracket_angle, idx_angle, mid_angle, reason, tilt_angle, finger_states = self.analyzer.detect_bracket_gesture(lms, side)
                    
                    if finger_states:
                        fs = finger_states
                        print(f"[DEBUG] {side}: <>{bracket_angle:.0f}° T:{fs.get('thumb')} I:{fs.get('index')} M:{fs.get('middle')} R:{fs.get('ring')} P:{fs.get('pinky')} {'✓' if is_bracket else '✗'}", end='\r')
                    else:
                        print(f"[DEBUG] {side}: <>{bracket_angle:.0f}° {'✓' if is_bracket else '✗'} - {reason}", end='\r')
            
            # Draw debug overlay
            self.draw(frame, hands)
            
            # ✅ PHASE 2: Auto-trigger on gesture (with hold time)
            # ✅ Only trigger if NOT already counted down this round
            if self.gesture_detected and not self.counting and not self.cooldown_active and not self._countdown_finished:
                gesture_hold_frames += 1
                
                if gesture_hold_frames % 3 == 0:
                    print(f"\n[HOLD] {gesture_hold_frames}/{config.GESTURE_HOLD_THRESHOLD}", end='\r')
                
                if gesture_hold_frames >= config.GESTURE_HOLD_THRESHOLD:
                    print(f"\n✅ [GESTURE] <> Detected! Starting countdown...")
                    self.counting = True
                    self.count_start = time.time()
                    self.count_val = 3
                    gesture_hold_frames = 0
            else:
                gesture_hold_frames = 0
            
            # Handle countdown display
            if self.counting:
                self.countdown(frame)
                
                # Check if countdown finished
                if self.count_val == 0 and not self.ready_to_capture:
                    self.ready_to_capture = True
                    self._countdown_finished = True  # ✅ Mark that countdown completed
                    self.counting = False  # ✅ Stop counting
            
            # Display frame
            cv2.imshow("BracketClick - Phase 2 DEBUG", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[DEBUG] Quit key pressed")
                break
            if key in config.TRIGGER_KEYS and not self.counting and not self.cooldown_active and not self._countdown_finished:
                print(f"\n[MANUAL] Manual trigger (key code: {key})")
                self.counting = True
                self.count_start = time.time()
                self.count_val = 3
            
            # Optional: Force capture (press 'p')
            if key == ord('p') and not self.counting and not self.cooldown_active:
                print(f"\n[FORCE] Forced capture for testing!")
                self.capture(frame)
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n[OK] Done")


# ==================== MAIN ====================
def main():
    print("="*50)
    print("   BracketClick - Phase 2: Gesture Detection (DEBUG)")
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