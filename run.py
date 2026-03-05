# run.py - Choose which phase to run
# Place in C:\bracketclick\ (root level, NOT in src/)

import sys
import os

print("="*50)
print("   BracketClick - Choose Phase")
print("="*50)
print("1. Phase 1: Hand Tracking (Spacebar trigger)")
print("2. Phase 2: Gesture Detection (Auto trigger)")
print("="*50)

choice = input("Enter phase number (1 or 2): ").strip()

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if choice == "1":
    print("\n[INFO] Starting Phase 1...\n")
    import phase1_hand_tracking
    phase1_hand_tracking.main()
elif choice == "2":
    print("\n[INFO] Starting Phase 2...\n")
    import phase2_gesture_detection
    phase2_gesture_detection.main()
else:
    print("[ERROR] Invalid choice. Please enter 1 or 2.")
    sys.exit(1)