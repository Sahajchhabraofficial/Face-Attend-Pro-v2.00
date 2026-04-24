"""
camera_manager.py — Camera Detection & Configuration Manager

Handles:
  - Auto-detecting all connected webcams (index 0..9)
  - Saving / loading CCTV / IP cameras (RTSP URLs)
  - Testing any camera connection
  - Returning the active camera source to use in VideoCapture
"""

import cv2
import json
import os
import threading

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "data", "cameras.json")

# ── Default config structure ──────────────────────────────────────────
DEFAULT_CONFIG = {
    "active": {"type": "webcam", "index": 0, "label": "Default Webcam"},
    "saved":  []
}


class CameraManager:
    """
    Manages multiple camera sources.

    Config file schema (cameras.json):
    {
      "active": {
        "type":  "webcam" | "cctv",
        "index": 0,                      ← only for webcam
        "url":   "rtsp://...",           ← only for cctv
        "label": "My Camera"
      },
      "saved": [
        {"type": "webcam", "index": 0, "label": "Built-in Webcam"},
        {"type": "cctv",   "url": "rtsp://admin:pass@192.168.1.64:554/stream",
         "label": "Classroom Cam"}
      ]
    }
    """

    def __init__(self):
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
        if not os.path.exists(CONFIG_FILE):
            self._write(DEFAULT_CONFIG)

    # ── internal ─────────────────────────────────────────────────────
    def _read(self) -> dict:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # ── webcam auto-detection ────────────────────────────────────────
    def detect_webcams(self) -> list[dict]:
        """
        Scans indices 0-9 and returns a list of available webcams.
        Each entry: {"type": "webcam", "index": i, "label": "Camera i"}
        This can take a few seconds — run in a thread.
        """
        found = []
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)   # CAP_DSHOW = faster on Windows
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    found.append({
                        "type":  "webcam",
                        "index": i,
                        "label": f"Webcam {i}" if i > 0 else "Default Webcam"
                    })
            cap.release()
        return found

    # ── test any camera ──────────────────────────────────────────────
    def test_camera(self, cam: dict, timeout: float = 5.0) -> tuple[bool, str]:
        """
        Tries to open the camera and grab one frame.
        Returns (success: bool, message: str)
        """
        src = self._source(cam)
        result = [False, "Timeout — camera not responding"]

        def _try():
            try:
                cap = cv2.VideoCapture(src)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))
                if not cap.isOpened():
                    result[0] = False
                    result[1]  = "Could not open camera source"
                    return
                ret, _ = cap.read()
                cap.release()
                if ret:
                    result[0] = True
                    result[1]  = "✅  Connection successful!"
                else:
                    result[0] = False
                    result[1]  = "Camera opened but no frame received"
            except Exception as e:
                result[0] = False
                result[1]  = f"Error: {e}"

        t = threading.Thread(target=_try, daemon=True)
        t.start()
        t.join(timeout + 1)
        return result[0], result[1]

    # ── saved cameras CRUD ───────────────────────────────────────────
    def get_saved(self) -> list[dict]:
        return self._read().get("saved", [])

    def add_camera(self, cam: dict) -> bool:
        """Add a camera to saved list. Returns False if duplicate label."""
        data = self._read()
        for s in data["saved"]:
            if s["label"].lower() == cam["label"].lower():
                return False
        data["saved"].append(cam)
        self._write(data)
        return True

    def delete_camera(self, label: str):
        data = self._read()
        data["saved"] = [c for c in data["saved"] if c["label"] != label]
        self._write(data)

    # ── active camera ────────────────────────────────────────────────
    def get_active(self) -> dict:
        return self._read().get("active", DEFAULT_CONFIG["active"])

    def set_active(self, cam: dict):
        data = self._read()
        data["active"] = cam
        self._write(data)

    def get_active_source(self):
        """
        Returns the value to pass directly into cv2.VideoCapture().
        For webcam → int index
        For CCTV   → rtsp:// string
        """
        return self._source(self.get_active())

    # ── helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _source(cam: dict):
        if cam.get("type") == "cctv":
            return cam["url"]
        return cam.get("index", 0)

    @staticmethod
    def label_for(cam: dict) -> str:
        t = "📹 CCTV" if cam.get("type") == "cctv" else "💻 Webcam"
        return f"{t}  —  {cam.get('label', 'Unknown')}"
