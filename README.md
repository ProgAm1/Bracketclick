# BracketClick Photo Booth

Gesture-triggered photo booth — GDG AI Committee Project 01.  
Captures a photo when both hands form the `<>` gesture, saves it locally, and (optionally) emails it to the user.

---

## Quick start (Windows / PowerShell)

```powershell
# 1) Clone
git clone https://github.com/ProgAm1/Bracketclick.git
cd Bracketclick

# 2) Create & activate venv
python -m venv venv
.\venv\Scripts\activate

# 3) Install requirements
pip install -r requirements.txt

# 4) Run
python web\app.py

# Open:
# http://127.0.0.1:5000

# How it works
1- User enters their email
2- Camera detects the <> gesture
3- Photo is captured
4- Photo is saved locally
5- Photo is sent to the user's email

# Requirements
1- Python 3.8+
2- Webcam
3- Internet connection (first run downloads the AI model automatically)
