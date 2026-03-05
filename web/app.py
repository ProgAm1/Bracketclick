# web/app.py - FIXED IMPORT ORDER
import sys
import os
import re

# ✅ ADD PROJECT ROOT TO PATH BEFORE ANY src IMPORTS
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now imports from src will work
from src.gesture_engine import HandAnalyzer
from src import config
from src.email_service import send_photo_email

import cv2
import numpy as np
import json
import time
import threading
import datetime
from flask import Flask, render_template, Response, request, jsonify

import urllib.request

MODEL_URL = "https://github.com/ProgAm1/Bracketclick/releases/download/v1.0.0/hand_landmarker.task"

def ensure_model():
    model_path = config.MODEL_PATH

    if os.path.exists(model_path):
        return model_path

    print("[INFO] Model not found. Downloading...")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    urllib.request.urlretrieve(MODEL_URL, model_path)

    print("[OK] Model downloaded")

    return model_path




def is_valid_email(email):
    """Validate email format (basic RFC 5322-style)."""
    if not email or len(email) > 254:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Initialize Flask with correct paths
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

UPLOAD_FOLDER = config.CAPTURE_FOLDER
LOG_FOLDER = config.LOG_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

COUNTDOWN_SECONDS = 3
COOLDOWN_SECONDS = 3
GESTURE_HOLD_FRAMES = 5

state = {
    'email': None,
    'gesture_detected': False,
    'left_hand_ready': False,
    'right_hand_ready': False,
    'countdown_active': False,
    'countdown_value': COUNTDOWN_SECONDS,
    'countdown_start': 0,  # timestamp when current countdown second started
    'capture_complete': False,
    'cooldown_active': False,
    'cooldown_start': 0,
    'gesture_hold_count': 0,
    'angles': {'left_bracket': 0, 'right_bracket': 0},
    'hands_detected': 0,
    'error': ''
}
state_lock = threading.Lock()

# Initialize Hand Analyzer with detailed error checking
analyzer = None

try:
    print(f"\n[INFO] Looking for model at: {os.path.abspath(config.MODEL_PATH)}")
    print(f"[INFO] Model exists: {os.path.exists(config.MODEL_PATH)}")

    # Ensure model exists (download if missing)
    model_path = ensure_model()

    print(f"\n[INFO] Using model at: {os.path.abspath(model_path)}")
    print(f"[INFO] Model exists: {os.path.exists(model_path)}")

    analyzer = HandAnalyzer(model_path)
    print("[OK] HandAnalyzer initialized successfully!\n")

except Exception as e:
    error_msg = f"Failed to load HandAnalyzer: {str(e)}"
    print(f"[ERROR] {error_msg}")

    import traceback
    traceback.print_exc()

    with state_lock:
        state['error'] = error_msg


def add_watermark(frame, email):
    """Add watermark to captured image"""
    watermarked = frame.copy()
    h, w, _ = watermarked.shape

    # GDG watermark
    cv2.putText(watermarked, "#GDGCUJ", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)

    # Email
    if email:
        (ew, eh), _ = cv2.getTextSize(email, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
        cv2.putText(watermarked, email, (w - ew - 20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)

    return watermarked


def save_capture(frame, email):
    """Save captured image and send via email."""
    try:
        watermarked = add_watermark(frame, email)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        cv2.imwrite(filepath, watermarked)
        print(f"[OK] Saved: {filename}")

        # Log to JSON
        log_entry = {
            'email': email,
            'timestamp': timestamp,
            'image_path': filename,
            'full_path': filepath
        }
        log_file = os.path.join(LOG_FOLDER, 'participants.json')
        log_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            except Exception:
                pass
        log_data.append(log_entry)
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        # Send email with photo (if enabled and email present)
        if getattr(config, 'EMAIL_ENABLED', False) and email:
            print(f"[EMAIL] Sending photo to {email}...")
            send_photo_email(email, filepath)
        else:
            if not email:
                print("[INFO] Email sending skipped (no email)")
            else:
                print("[INFO] Email sending skipped (disabled in config)")

        return True
    except Exception as e:
        print(f"[ERROR] Save failed: {e}")
        return False


def draw_landmarks(frame, hands, analyzer):
    """
    Draw landmark points, lines, and angles on frame
    (Same logic as Phase 2's draw() method)
    """
    left_bracket = False
    right_bracket = False

    for hand in hands:
        lms = hand['landmarks']
        side = hand['side']

        if len(lms) < 21:
            continue

        # Detect gesture for color coding
        try:
            is_bracket, bracket_angle, idx_angle, mid_angle, reason, tilt_angle, finger_states = \
                analyzer.detect_bracket_gesture(lms, side)
        except:
            is_bracket = False
            bracket_angle = 0
            idx_angle = 0
            mid_angle = 0

        if side == "Left" and is_bracket:
            left_bracket = True
        elif side == "Right" and is_bracket:
            right_bracket = True

        # ==================== Draw Landmark Points ====================
        for i, (x, y) in enumerate(lms):
            if i in [5, 6, 7, 8, 9, 10, 11, 12]:
                color = config.GESTURE_READY_COLOR if is_bracket else config.VECTOR_COLOR
                cv2.circle(frame, (x, y), 6, color, -1)
            else:
                cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)

        # ==================== Draw Finger Lines ====================
        cv2.line(frame, lms[5], lms[6], config.VECTOR_COLOR, 2)
        cv2.line(frame, lms[6], lms[7], config.VECTOR_COLOR, 2)
        cv2.line(frame, lms[7], lms[8], config.VECTOR_COLOR, 2)
        cv2.line(frame, lms[9], lms[10], config.VECTOR_COLOR, 2)
        cv2.line(frame, lms[10], lms[11], config.VECTOR_COLOR, 2)
        cv2.line(frame, lms[11], lms[12], config.VECTOR_COLOR, 2)

        # ==================== Display Angles ====================
        if len(lms) > 12:
            angle_color = config.GESTURE_READY_COLOR if is_bracket else config.VECTOR_COLOR
            cv2.putText(frame, f"<>{int(bracket_angle)}°",
                       (lms[0][0]-40, lms[0][1]-60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2)

            idx_color = config.GESTURE_READY_COLOR if idx_angle >= 140 else (
                0, 0, 255)
            cv2.putText(frame, f"Idx:{int(idx_angle)}°",
                       (lms[6][0]-30, lms[6][1]+30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, idx_color, 2)

            mid_color = config.GESTURE_READY_COLOR if mid_angle >= 140 else (
                0, 0, 255)
            cv2.putText(frame, f"Mid:{int(mid_angle)}°",
                       (lms[10][0]-30, lms[10][1]+30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, mid_color, 2)

        # ==================== Hand Side Label ====================
        status = "✓" if is_bracket else "✗"
        side_color = config.GESTURE_READY_COLOR if is_bracket else (0, 0, 255)
        cv2.putText(frame, f"{side} {status}",
                   (lms[0][0]-30, lms[0][1]-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, side_color, 2)

    # ==================== Overall Status Message ====================
    if left_bracket and right_bracket:
        cv2.putText(frame, "GESTURE DETECTED! <>", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.GESTURE_READY_COLOR, 3)
    else:
        cv2.putText(frame, "Form <> with BOTH hands!", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, config.TEXT_COLOR, 2)

    return frame


def camera_loop():
    """
    Main camera processing loop for web streaming
    Matches Phase 2 logic exactly
    """
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.FPS)
    
    if not cap.isOpened():
        print("[ERROR] Cannot open camera!")
        with state_lock:
            state['error'] = "Cannot open camera"
        return
    
    print("[OK] Camera opened successfully!")
    print("[INFO] Waiting for hands...\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame")
            break
        
        # Work on a copy for display
        display_frame = frame.copy()
        h, w, _ = display_frame.shape
        
        # ==================== Check Cooldown State ====================
        with state_lock:
            if state['cooldown_active']:
                elapsed = time.time() - state['cooldown_start']
                if elapsed >= COOLDOWN_SECONDS:
                    state['cooldown_active'] = False
                    state['capture_complete'] = False
                    state['gesture_detected'] = False
                    state['left_hand_ready'] = False
                    state['right_hand_ready'] = False
                    print("[INFO] ✓ Cooldown ended. Ready for next photo!")
            in_cooldown = state['cooldown_active']
            in_countdown = state['countdown_active']
        
        # ==================== Reset Detection Values ====================
        hands_count = 0
        left_bracket = False
        right_bracket = False
        left_angle = 0
        right_angle = 0
        hands = []
        
        # ==================== Gesture Detection (Phase 2 EXACT logic) ====================
        if not in_cooldown and not in_countdown and analyzer is not None:
            try:
                # Process frame through MediaPipe
                results = analyzer.process(frame)
                hands = analyzer.get_landmarks(results, w, h)
                hands_count = len(hands)
                
                # Debug output (like Phase 2)
                if hands_count > 0:
                    print(f"[DEBUG] Hands: {hands_count}", end='\r')
                
                for hand in hands:
                    lms = hand['landmarks']
                    side = hand['side']
                    
                    if len(lms) < 21:
                        continue
                    
                    try:
                        # ✅ EXACT Phase 2 detection
                        is_valid, bracket_angle, idx_angle, mid_angle, reason, tilt_angle, finger_states = \
                            analyzer.detect_bracket_gesture(lms, side)
                        
                        # ✅ Print detailed info like Phase 2
                        if finger_states:
                            fs = finger_states
                            print(f"[DEBUG] {side}: <>{bracket_angle:.0f}° T:{fs.get('thumb')} I:{fs.get('index')} M:{fs.get('middle')} {'✓' if is_valid else '✗'}", end='\r')
                        
                        if side == "Left":
                            left_angle = bracket_angle
                            if is_valid:
                                left_bracket = True
                                print(f"[DEBUG] ✓ Left: {bracket_angle:.0f}°", end='\r')
                        elif side == "Right":
                            right_angle = bracket_angle
                            if is_valid:
                                right_bracket = True
                                print(f"[DEBUG] ✓ Right: {bracket_angle:.0f}°", end='\r')
                                
                    except Exception as e:
                        print(f"[WARN] Detection error: {e}")
                        continue
                
                # ✅ BOTH hands must form <> (Phase 2)
                gesture_detected = left_bracket and right_bracket
                
                with state_lock:
                    state['gesture_detected'] = gesture_detected
                    state['left_hand_ready'] = left_bracket
                    state['right_hand_ready'] = right_bracket
                    state['hands_detected'] = hands_count
                    state['angles'] = {
                        'left_bracket': int(left_angle),
                        'right_bracket': int(right_angle)
                    }
                    
                    # ✅ Auto-trigger countdown (EXACT Phase 2 logic)
                    if (state['email'] and gesture_detected and 
                        not state['countdown_active'] and not state['cooldown_active']):
                        
                        state['gesture_hold_count'] += 1
                        
                        # Show progress like Phase 2
                        if state['gesture_hold_count'] % 3 == 0:
                            print(f"\n[HOLD] {state['gesture_hold_count']}/{config.GESTURE_HOLD_THRESHOLD}", end='\r')
                        
                        # ✅ Trigger after holding gesture
                        if state['gesture_hold_count'] >= config.GESTURE_HOLD_THRESHOLD:
                            print(f"\n✅ [GESTURE] <> Detected! Starting {COUNTDOWN_SECONDS}s countdown...")
                            print(f"    Left: {left_angle:.0f}°, Right: {right_angle:.0f}°")
                            state['countdown_active'] = True
                            state['countdown_value'] = COUNTDOWN_SECONDS
                            state['countdown_start'] = time.time()
                            state['gesture_hold_count'] = 0
                    else:
                        # Reset if gesture broken
                        if not gesture_detected and state['gesture_hold_count'] > 0:
                            print(f"\n[RESET] Gesture broken", end='\r')
                        state['gesture_hold_count'] = 0

            except Exception as e:
                print(f"[WARN] Gesture detection error: {e}")
        
        # ==================== Handle Countdown (timestamp-based, no sleep) ====================
        with state_lock:
            in_countdown = state['countdown_active']
        if in_countdown:
            with state_lock:
                val = state['countdown_value']
                start = state.get('countdown_start', 0)
            elapsed = time.time() - start
            if val > 0 and elapsed >= 1.0:
                with state_lock:
                    state['countdown_value'] -= 1
                    state['countdown_start'] = time.time()
            with state_lock:
                val = state['countdown_value']
            if val <= 0:
                with state_lock:
                    state['countdown_active'] = False
                ret, clean_frame = cap.read()
                if ret:
                    print("[CAPTURE] Saving clean photo...")
                    with state_lock:
                        email = state['email']
                    if save_capture(clean_frame, email):
                        with state_lock:
                            state['capture_complete'] = True
                            state['cooldown_active'] = True
                            state['cooldown_start'] = time.time()
                        print("[OK] Photo saved!")
                    else:
                        print("[ERROR] Failed to save")
        
        # ==================== Draw Landmarks (Phase 2 style) ====================
        display_frame = draw_landmarks(display_frame, hands, analyzer)
        
        # ==================== Countdown / Cooldown Overlay (read state under lock) ====================
        with state_lock:
            show_countdown = state['countdown_active']
            countdown_val = state['countdown_value']
            show_cooldown = state['cooldown_active']
            cooldown_start_ts = state['cooldown_start']
        if show_countdown:
            cv2.circle(display_frame, (w//2, h//4), 80, config.COUNTDOWN_COLOR, -1)
            cv2.putText(display_frame, str(countdown_val), (w//2-30, h//4+40),
                    cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 8)
        if show_cooldown:
            elapsed = time.time() - cooldown_start_ts
            remaining = max(0, int(COOLDOWN_SECONDS - elapsed) + 1)
            cv2.rectangle(display_frame, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.putText(display_frame, f"Wait {remaining}s...", (w//2-150, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 165, 255), 3)
        
        # ==================== Error Display ====================
        with state_lock:
            error_msg = state['error']
        
        if error_msg and analyzer is None:
            cv2.putText(display_frame, "ERROR: Model not loaded!", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # ==================== Encode and Stream ====================
        ret, buffer = cv2.imencode('.jpg', display_frame)
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.05)
    
    cap.release()
    print("[INFO] Camera released")

# ==================== Routes ====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(camera_loop(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/set_email', methods=['POST'])
def set_email():
    data = request.json
    email = data.get('email', '').strip()
    
    if not is_valid_email(email):
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    
    with state_lock:
        state['email'] = email
    
    print(f"[OK] Email set: {email}")
    return jsonify({'status': 'success', 'email': email})

@app.route('/status')
def status():
    with state_lock:
        return jsonify({
            'email_set': state['email'] is not None,
            'gesture_detected': state['gesture_detected'],
            'left_hand_ready': state['left_hand_ready'],
            'right_hand_ready': state['right_hand_ready'],
            'countdown_active': state['countdown_active'],
            'countdown_value': state['countdown_value'],
            'capture_complete': state['capture_complete'],
            'cooldown_active': state['cooldown_active'],
            'angles': state['angles'],
            'hands_detected': state['hands_detected'],
            'error': state['error']
        })

@app.route('/reset')
def reset():
    with state_lock:
        state['capture_complete'] = False
        state['cooldown_active'] = False
    return jsonify({'status': 'reset'})

# ==================== Main ====================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("   BracketClick - Phase 3")
    print("   GDG AI Committee")
    print("="*60)
    print(f"Server: http://localhost:5000")
    print(f"Model: {os.path.abspath(config.MODEL_PATH)}")
    print(f"Model exists: {os.path.exists(config.MODEL_PATH)}")
    print("="*60)
    
    if analyzer is None:
        print("\n[!] WARNING: HandAnalyzer not loaded!")
        print("    Check if hand_landmarker.task exists\n")
    
    print("\nStarting server...\n")
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)