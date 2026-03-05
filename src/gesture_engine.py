# src/gesture_engine.py
# Shared HandAnalyzer: MUST match Phase 2 logic so web (Phase 3) triggers countdown.
# Bracket angle = angle BETWEEN index and middle finger vectors (5->8, 9->12), not line tip-to-tip.
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np
import os

from src import config

class HandAnalyzer:
    def __init__(self, model_path):
        print(f"[HandAnalyzer] Loading model from: {os.path.abspath(model_path)}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=0.3,
                min_hand_presence_confidence=0.3,
                min_tracking_confidence=0.3
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
            print("[OK] MediaPipe HandLandmarker loaded successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to load MediaPipe model: {e}")
            raise

    def process(self, frame):
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            return self.landmarker.detect(mp_image)
        except Exception as e:
            print(f"[ERROR] Process failed: {e}")
            return None

    def get_landmarks(self, results, width, height):
        hands = []
        if results and results.hand_landmarks:
            for i, lms in enumerate(results.hand_landmarks):
                pts = [(int(lm.x * width), int(lm.y * height)) for lm in lms]
                side = results.handedness[i][0].category_name if results.handedness else "Unknown"
                hands.append({"landmarks": pts, "side": side})
        return hands

    def _calculate_angle(self, a, b, c):
        """Angle at b between ba and bc (degrees)."""
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        norm_ba = ba / (np.linalg.norm(ba) + 1e-8)
        norm_bc = bc / (np.linalg.norm(bc) + 1e-8)
        dot = np.clip(np.dot(norm_ba, norm_bc), -1.0, 1.0)
        return float(np.degrees(np.arccos(dot)))

    def get_finger_angle(self, landmarks):
        """Angle BETWEEN index and middle finger directions (PDF: bracket 30-60°).
        Vectors: index 5->8, middle 9->12. Same as Phase 2."""
        if len(landmarks) < 13:
            return 0
        index_vec = np.array(landmarks[8]) - np.array(landmarks[5])
        middle_vec = np.array(landmarks[12]) - np.array(landmarks[9])
        idx_norm = index_vec / (np.linalg.norm(index_vec) + 1e-8)
        mid_norm = middle_vec / (np.linalg.norm(middle_vec) + 1e-8)
        dot = np.clip(np.dot(idx_norm, mid_norm), -1.0, 1.0)
        return float(np.degrees(np.arccos(dot)))

    def get_angles(self, lms):
        """Alias for get_joint_angles (Phase 1 compatibility)."""
        return self.get_joint_angles(lms)

    def get_joint_angles(self, lms):
        """Joint angles for index (5-6-7) and middle (9-10-11)."""
        angles = {'idx': 0, 'mid': 0}
        if len(lms) < 21:
            return angles
        try:
            angles['idx'] = self._calculate_angle(lms[5], lms[6], lms[7])
        except Exception:
            pass
        try:
            angles['mid'] = self._calculate_angle(lms[9], lms[10], lms[11])
        except Exception:
            pass
        return angles

    def get_finger_states(self, landmarks):
        """Extended/curled state for each finger."""
        if len(landmarks) < 21:
            return None
        fingers = {
            'thumb': {'tip': 4, 'joint': 2, 'is_thumb': True},
            'index': {'tip': 8, 'joint': 6, 'is_thumb': False},
            'middle': {'tip': 12, 'joint': 10, 'is_thumb': False},
            'ring': {'tip': 16, 'joint': 14, 'is_thumb': False},
            'pinky': {'tip': 20, 'joint': 18, 'is_thumb': False}
        }
        states = {}
        for name, points in fingers.items():
            tip_x, tip_y = landmarks[points['tip']][0], landmarks[points['tip']][1]
            joint_x, joint_y = landmarks[points['joint']][0], landmarks[points['joint']][1]
            if points['is_thumb']:
                is_extended = abs(tip_x - joint_x) > 30
            else:
                is_extended = tip_y < joint_y
            states[name] = is_extended
        return states

    def detect_bracket_gesture(self, landmarks, handedness):
        """
        Same logic as Phase 2. Returns (is_valid, bracket_angle, idx_angle, mid_angle, reason, tilt_angle, finger_states).
        Bracket angle = angle between finger vectors (30-60°). Index/middle straight >= 140°.
        """
        if len(landmarks) < 13:
            return False, 0, 0, 0, "Too few landmarks", 0, None

        finger_states = self.get_finger_states(landmarks)
        bracket_angle = self.get_finger_angle(landmarks)
        angles = self.get_joint_angles(landmarks)
        idx_angle = angles.get('idx', 0)
        mid_angle = angles.get('mid', 0)

        is_bracket_angle = config.BRACKET_ANGLE_MIN <= bracket_angle <= config.BRACKET_ANGLE_MAX
        is_index_straight = idx_angle >= config.FINGER_STRAIGHT_MIN
        is_middle_straight = mid_angle >= config.FINGER_STRAIGHT_MIN

        index_base, index_tip = landmarks[5], landmarks[7]
        middle_base, middle_tip = landmarks[10], landmarks[12]
        index_vec_x = index_tip[0] - index_base[0]
        index_vec_y = index_tip[1] - index_base[1]
        middle_vec_x = middle_tip[0] - middle_base[0]
        middle_vec_y = middle_tip[1] - middle_base[1]
        avg_vec_x = (index_vec_x + middle_vec_x) / 2
        avg_vec_y = (index_vec_y + middle_vec_y) / 2
        tilt_angle_deg = np.degrees(np.arctan2(avg_vec_y, avg_vec_x))
        abs_tilt = abs(tilt_angle_deg)
        if abs_tilt > 90:
            abs_tilt = 180 - abs_tilt
        HORIZONTAL_THRESHOLD = 30
        is_horizontal = abs_tilt <= HORIZONTAL_THRESHOLD

        if handedness == "Left":
            correct_bracket = avg_vec_x < 30
            expected_direction = "LEFT"
        elif handedness == "Right":
            correct_bracket = avg_vec_x > -30
            expected_direction = "RIGHT"
        else:
            correct_bracket = False
            expected_direction = "?"

        is_valid = (
            is_bracket_angle and
            is_index_straight and
            is_middle_straight and
            is_horizontal and
            correct_bracket
        )

        if not is_bracket_angle:
            reason = f"Bracket {bracket_angle:.0f}° (need {config.BRACKET_ANGLE_MIN}-{config.BRACKET_ANGLE_MAX}°)"
        elif not is_index_straight:
            reason = f"Index {idx_angle:.0f}° (need >{config.FINGER_STRAIGHT_MIN}°)"
        elif not is_middle_straight:
            reason = f"Middle {mid_angle:.0f}° (need >{config.FINGER_STRAIGHT_MIN}°)"
        elif not is_horizontal:
            reason = f"Tilt {abs_tilt:.0f}° (need ≤{HORIZONTAL_THRESHOLD}°)"
        elif not correct_bracket:
            reason = f"Wrong direction! Need {expected_direction}"
        else:
            reason = "Perfect <>!"

        return is_valid, bracket_angle, idx_angle, mid_angle, reason, abs_tilt, finger_states