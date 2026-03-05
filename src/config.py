# src/config.py
import os

# Get absolute path of this file
SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root is ONE level above src/
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Model is in PROJECT ROOT (C:\bracketclick\hand_landmarker.task)
MODEL_PATH = os.path.join(PROJECT_ROOT, 'hand_landmarker.task')

# Camera settings
CAMERA_INDEX = 0
FRAME_WIDTH = 800
FRAME_HEIGHT = 600
FPS = 30

# Folders (inside web/)
CAPTURE_FOLDER = os.path.join(PROJECT_ROOT, 'web', 'captures')
LOG_FOLDER = os.path.join(PROJECT_ROOT, 'web', 'logs')
LOG_FILE = os.path.join(LOG_FOLDER, 'participants.json')

# Gesture thresholds
BRACKET_ANGLE_MIN = 30
BRACKET_ANGLE_MAX = 60
FINGER_STRAIGHT_MIN = 140
GESTURE_HOLD_THRESHOLD = 5

# Colors (BGR)
TEXT_COLOR = (255, 255, 255)
GESTURE_READY_COLOR = (0, 255, 0)
COUNTDOWN_COLOR = (0, 215, 255)
VECTOR_COLOR = (0, 255, 255)

# Trigger keys
TRIGGER_KEYS = [32, ord('c'), ord('C')]

# ==================== Email Settings ====================
EMAIL_ENABLED = True  # Set to False to disable email sending

# Gmail SMTP (recommended)
EMAIL_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Load .env from project root if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
except ImportError:
    pass

# Credentials: use environment variables (never commit real values)
EMAIL_ADDRESS = os.getenv('GDG_EMAIL_ADDRESS', 'your-gdg-email@gmail.com')
EMAIL_PASSWORD = os.getenv('GDG_EMAIL_PASSWORD', 'your-app-password')
EMAIL_SUBJECT = "Your BracketClick Photo - GDG Workshop 📸"

# Disable email if default placeholder is still set
if EMAIL_ADDRESS == 'your-gdg-email@gmail.com' or EMAIL_PASSWORD == 'your-app-password':
    EMAIL_ENABLED = False
    print("[WARNING] Email not configured. Set GDG_EMAIL_ADDRESS and GDG_EMAIL_PASSWORD in .env")
    print("[WARNING] Email sending disabled until configured.")

# DEBUG - Remove this after testing
print(f"\n[CONFIG] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[CONFIG] MODEL_PATH: {MODEL_PATH}")
print(f"[CONFIG] Model exists: {os.path.exists(MODEL_PATH)}\n")