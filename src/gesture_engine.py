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
        print(
            f"[HandAnalyzer] Loading model from: {os.path.abspath(model_path)}")
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
            self.landmarker = vision.HandLandmarker.create_from_options(
                options)
            print("[OK] MediaPipe HandLandmarker loaded successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to load MediaPipe model: {e}")
            raise

    def process(self, frame):
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB, data=rgb_frame)
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
        a, b, c = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32), np.array(c, dtype=np.float32)

        ba = a - b
        bc = c - b

        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)

        # لو النقاط متطابقة/قريبة جدًا اعتبرها مستقيمة
        if norm_ba < 1e-5 or norm_bc < 1e-5:
            return 180.0

        ba = ba / norm_ba
        bc = bc / norm_bc

        dot = np.clip(np.dot(ba, bc), -1.0, 1.0)
        angle = np.degrees(np.arccos(dot))

        if np.isnan(angle):
            return 180.0

        return float(angle)

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
        """
        Joint angles (degrees) for fingers:
        index: 5-6-7
        middle: 9-10-11
        ring: 13-14-15
        pinky: 17-18-19
        thumb: 2-3-4 (approx bend at 3)
        """
        angles = {'idx': 0, 'mid': 0, 'ring': 0, 'pinky': 0, 'thumb': 0}
        if len(lms) < 21:
            return angles

        def safe(a, b, c, key):
            try:
                angles[key] = self._calculate_angle(lms[a], lms[b], lms[c])
            except Exception:
                pass

        safe(5, 6, 7, 'idx')
        safe(9, 10, 11, 'mid')
        safe(13, 14, 15, 'ring')
        safe(17, 18, 19, 'pinky')
        safe(2, 3, 4, 'thumb')  # thumb bend

        return angles

    def get_finger_states(self, landmarks):
        """Extended/curled state for each finger (rotation-robust)."""
        if len(landmarks) < 21:
            return None

        wrist = np.array(landmarks[0])

        fingers = {
            'thumb':  {'tip': 4,  'joint': 2,  'is_thumb': True},
            'index':  {'tip': 8,  'joint': 6,  'is_thumb': False},
            'middle': {'tip': 12, 'joint': 10, 'is_thumb': False},
            'ring':   {'tip': 16, 'joint': 14, 'is_thumb': False},
            'pinky':  {'tip': 20, 'joint': 18, 'is_thumb': False},
        }

        states = {}
        for name, points in fingers.items():
            tip = np.array(landmarks[points['tip']])
            joint = np.array(landmarks[points['joint']])

            if points['is_thumb']:
                # خله مثل ما هو عندك (بسيط)
                states[name] = abs(tip[0] - joint[0]) > 30
            else:
                # ✅ الإصبع مرفوع إذا طرفه أبعد عن الرسغ من مفصله
                states[name] = np.linalg.norm(
                    tip - wrist) > np.linalg.norm(joint - wrist)

        return states

    def detect_bracket_gesture(self, landmarks, handedness):
        """
        Same logic as Phase 2. Returns (is_valid, bracket_angle, idx_angle, mid_angle, reason, tilt_angle, finger_states).
        Bracket angle = angle between finger vectors (30-60°). Index/middle straight >= 140°.
        """
        if len(landmarks) < 21:
            return False, 0, 0, 0, "Too few landmarks", 0, None

         # ✅ لازم تحسبه هنا
        bracket_angle = self.get_finger_angle(landmarks)

        finger_states = self.get_finger_states(landmarks) or {}

        angles = self.get_joint_angles(landmarks)
        idx_angle   = angles.get('idx', 0)
        mid_angle   = angles.get('mid', 0)
        ring_angle  = angles.get('ring', 0)
        pinky_angle = angles.get('pinky', 0)
        thumb_angle = angles.get('thumb', 0)

        # ✅ الأصابع "down/curled" بالزوايا (أكثر ثباتًا من finger_states)
        FINGER_CURLED_MAX = 120  # جرّب 110-130 حسب تجربتك
        ring_down  = ring_angle  <= FINGER_CURLED_MAX
        pinky_down = pinky_angle <= FINGER_CURLED_MAX

        # thumb خله اختياري بالبداية عشان ما يطفي الجيستشر بالغلط
        thumb_down = thumb_angle <= FINGER_CURLED_MAX

        is_bracket_angle = config.BRACKET_ANGLE_MIN <= bracket_angle <= config.BRACKET_ANGLE_MAX
        is_index_straight = idx_angle >= config.FINGER_STRAIGHT_MIN
        is_middle_straight = mid_angle >= config.FINGER_STRAIGHT_MIN

        index_base, index_tip = landmarks[5], landmarks[8]
        middle_base, middle_tip = landmarks[9], landmarks[12]        
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
        HORIZONTAL_THRESHOLD = 15
        is_horizontal = abs_tilt <= HORIZONTAL_THRESHOLD

        DIRECTION_MARGIN = 8  # بيكسلات
        if handedness == "Left":
            correct_bracket = avg_vec_x < -DIRECTION_MARGIN
            expected_direction = "LEFT"
        elif handedness == "Right":
            correct_bracket = avg_vec_x > DIRECTION_MARGIN
            expected_direction = "RIGHT"
        else:
            correct_bracket = False
            expected_direction = "?"

        is_valid = (
            is_bracket_angle and
            is_index_straight and
            is_middle_straight and
            is_horizontal and
            correct_bracket and
            ring_down and
            pinky_down
            # thumb_down  # ✅ خله معطّل مؤقتًا
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
