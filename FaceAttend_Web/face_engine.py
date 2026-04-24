"""
face_engine.py — Face Detection & Recognition Engine
Uses OpenCV LBPH (Local Binary Pattern Histogram) recognizer.

Requirements: opencv-contrib-python (NOT opencv-python)
"""

import cv2
import numpy as np
import os

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "data", "faces")
MODEL_PATH = os.path.join(BASE_DIR, "data", "model.yml")

os.makedirs(FACES_DIR, exist_ok=True)

# ── Confidence threshold ──────────────────────────────────────────────
# LBPH: lower value = better match.  Tune this if you get false positives.
CONFIDENCE_THRESHOLD = 70


class FaceEngine:
    def __init__(self):
        # Haar cascade for face detection
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        # LBPH recognizer for face identification
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.faces_dir   = FACES_DIR
        self.is_trained  = False

        # Load existing model if available
        if os.path.exists(MODEL_PATH):
            try:
                self.recognizer.read(MODEL_PATH)
                self.is_trained = True
            except Exception:
                self.is_trained = False

    # ── helpers ──────────────────────────────────────────────────────
    def detect(self, frame):
        """Return (gray_frame, list_of_face_rects).
        face_rects = [(x, y, w, h), ...]
        """
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        return gray, faces

    # ── training ─────────────────────────────────────────────────────
    def train(self) -> bool:
        """Re-train the model with ALL face images stored on disk.
        Returns True if training succeeded.
        """
        faces, labels = [], []

        for filename in os.listdir(FACES_DIR):
            if not filename.lower().endswith(".jpg"):
                continue
            try:
                student_id = int(filename.split("_")[0])
            except ValueError:
                continue
            img = cv2.imread(os.path.join(FACES_DIR, filename), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                labels.append(student_id)

        if len(faces) == 0:
            return False

        self.recognizer.train(faces, np.array(labels))
        self.recognizer.save(MODEL_PATH)
        self.is_trained = True
        return True

    # ── recognition ──────────────────────────────────────────────────
    def recognize(self, frame):
        """Detect and recognize faces in a BGR frame.

        Returns list of dicts:
            {
              "label":      int   (student id, or -1 if unknown),
              "confidence": float (lower = better for LBPH),
              "known":      bool,
              "bbox":       (x, y, w, h)
            }
        """
        if not self.is_trained:
            return []

        gray, faces = self.detect(frame)
        results = []

        for (x, y, w, h) in faces:
            roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
            label, confidence = self.recognizer.predict(roi)
            results.append({
                "label":      label,
                "confidence": confidence,
                "known":      confidence < CONFIDENCE_THRESHOLD,
                "bbox":       (x, y, w, h),
            })

        return results

    # ── delete student faces ──────────────────────────────────────────
    def delete_faces(self, student_id: int):
        """Remove all face images for a student (used on delete)."""
        for f in os.listdir(FACES_DIR):
            if f.startswith(f"{student_id}_"):
                os.remove(os.path.join(FACES_DIR, f))
