# BracketClick Photo Booth

Gesture-triggered photo booth — GDG AI Committee Project 01.

## Quick start

```bash
# From project root
pip install -r requirements.txt
python web/app.py
# Open http://localhost:5000
```

## Email setup (send photo to user after capture)

1. **Gmail App Password**
   - Google Account → Security → 2-Step Verification (must be on)
   - App passwords → Generate for "Mail" / "Other (Custom name)"
   - Copy the 16-character password

2. **Configure credentials**
   ```bash
   copy .env.example .env
   # Edit .env and set:
   # GDG_EMAIL_ADDRESS=your-gdg-email@gmail.com
   # GDG_EMAIL_PASSWORD=your-16-char-app-password
   ```

3. **Test email (optional)**
   ```bash
   python -c "from src.email_service import test_email_connection; test_email_connection()"
   ```

4. Run the app and capture a photo; the watermarked image is sent to the user’s email.

**Security:** Never commit `.env` or real passwords. `.env` is in `.gitignore`.

## Requirements

- Python 3.8+
- Camera
- `hand_landmarker.task` in project root (see GDG project docs)
