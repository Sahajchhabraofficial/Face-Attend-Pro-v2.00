"""
app.py — FaceAttend Pro  |  Flask + MySQL  |  v3.0
Run:  python app.py
Then open:  http://localhost:5000
"""

import os
import cv2
import base64
import threading
import numpy as np
from datetime import date
from flask import (Flask, render_template, request,
                   jsonify, Response, redirect, url_for)

from database        import StudentDB, AttendanceDB
from face_engine     import FaceEngine
from camera_manager  import CameraManager

import sys

# ── App setup ────────────────────────────────────────────────────────
app      = Flask(__name__)
engine   = FaceEngine()
cam_mgr  = CameraManager()
_lock    = threading.Lock()

# ── Verify MySQL connection on startup ───────────────────────────────
try:
    sdb = StudentDB()
    adb = AttendanceDB()
    sdb.total()
    print("✅ MySQL connected successfully.")
except Exception as e:
    print(f"⚠️ Database connection failed: {e}")
    
    # DON'T exit — just keep app running
    sdb = None
    adb = None


# ════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════
def decode_image(b64: str):
    """Base64 data-URL → OpenCV BGR ndarray (or None on failure)."""
    try:
        if "," in b64:
            b64 = b64.split(",")[1]
        buf = np.frombuffer(base64.b64decode(b64), np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception:
        return None


def cctv_stream_generator():
    """MJPEG generator: reads RTSP/webcam on server, annotates, streams."""
    src = cam_mgr.get_active_source()
    cap = cv2.VideoCapture(src)
    students = sdb.get_students()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if engine.is_trained:
                with _lock:
                    hits = engine.recognize(frame)
                for h in hits:
                    x, y, w, ht = h["bbox"]
                    if h["known"]:
                        s     = students.get(str(h["label"]))
                        name  = s["name"] if s else f"ID {h['label']}"
                        color = (0, 212, 160)
                        adb.mark(h["label"], name)
                    else:
                        name  = "Unknown"
                        color = (60, 60, 255)
                    cv2.rectangle(frame, (x, y), (x+w, y+ht), color, 2)
                    cv2.putText(frame, name, (x, y-8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + buf.tobytes() + b"\r\n")
    finally:
        cap.release()


# ════════════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ════════════════════════════════════════════════════════════════════
@app.route("/")
def dashboard():
    if not sdb or not adb:
        return "Database not connected"
    total   = sdb.total()
    present = adb.today_count()
    absent  = max(total - present, 0)
    rate    = adb.attendance_rate(total)
    records = adb.get_today()
    return render_template("dashboard.html",
                           total=total, present=present,
                           absent=absent, rate=rate,
                           records=records, today=date.today().isoformat())


@app.route("/attendance")
def attendance():
    active = cam_mgr.get_active()
    return render_template("attendance.html", active_cam=active)


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/students")
def students_page():
    all_s = sdb.get_students()
    return render_template("students.html", students=all_s)


@app.route("/records")
def records_page():
    dates    = adb.get_all_dates()
    selected = request.args.get("date", dates[0] if dates else None)
    recs     = adb.get_by_date(selected) if selected else []
    return render_template("records.html",
                           dates=dates, selected=selected, records=recs)


@app.route("/cameras")
def cameras_page():
    return render_template("cameras.html",
                           saved=cam_mgr.get_saved(),
                           active=cam_mgr.get_active())


# ════════════════════════════════════════════════════════════════════
#  API — FACE RECOGNITION
# ════════════════════════════════════════════════════════════════════
@app.route("/api/recognize", methods=["POST"])
def api_recognize():
    frame = decode_image(request.json.get("image", ""))
    if frame is None:
        return jsonify({"error": "bad image"}), 400

    with _lock:
        hits = engine.recognize(frame)

    students = sdb.get_students()
    out = []
    for h in hits:
        sid     = h["label"]
        student = students.get(str(sid)) if h["known"] else None
        name    = student["name"] if student else "Unknown"
        marked  = False
        if h["known"] and student:
            marked = adb.mark(sid, name)
        out.append({
            "name":            name,
            "confidence":      round(h["confidence"], 1),
            "known":           h["known"],
            "bbox":            list(h["bbox"]),
            "marked":          marked,
            "already_present": adb.already_marked(sid) if h["known"] else False,
        })
    return jsonify({"results": out})


# ════════════════════════════════════════════════════════════════════
#  API — REGISTRATION
# ════════════════════════════════════════════════════════════════════
@app.route("/api/registration/start", methods=["POST"])
def api_reg_start():
    return jsonify({"student_id": sdb.next_id()})


@app.route("/api/registration/sample", methods=["POST"])
def api_reg_sample():
    data       = request.json
    student_id = int(data["student_id"])
    frame      = decode_image(data.get("image", ""))
    if frame is None:
        return jsonify({"saved": False, "count": 0}), 400

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = engine.detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

    if len(faces) == 0:
        existing = len([f for f in os.listdir(engine.faces_dir)
                        if f.startswith(f"{student_id}_")])
        return jsonify({"saved": False, "count": existing})

    x, y, w, h = faces[0]
    roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
    existing = len([f for f in os.listdir(engine.faces_dir)
                    if f.startswith(f"{student_id}_")])
    new_count = existing + 1
    cv2.imwrite(os.path.join(engine.faces_dir,
                             f"{student_id}_{new_count}.jpg"), roi)
    return jsonify({"saved": True, "count": new_count, "done": new_count >= 30})


@app.route("/api/registration/finish", methods=["POST"])
def api_reg_finish():
    data       = request.json
    student_id = int(data["student_id"])
    name       = data.get("name", "").strip()
    roll       = data.get("roll", "").strip()

    if not name or not roll:
        return jsonify({"success": False, "error": "Name and roll required"})
    if sdb.roll_exists(roll):
        return jsonify({"success": False, "error": "Roll number already exists"})

    sdb.add_student(student_id, name, roll)
    with _lock:
        ok = engine.train()
    return jsonify({"success": ok, "name": name})


# ════════════════════════════════════════════════════════════════════
#  API — DATA
# ════════════════════════════════════════════════════════════════════
@app.route("/api/attendance/today")
def api_today():
    return jsonify({"records": adb.get_today(), "count": adb.today_count()})


@app.route("/api/stats")
def api_stats():
    total   = sdb.total()
    present = adb.today_count()
    return jsonify({
        "total":   total,
        "present": present,
        "absent":  max(total - present, 0),
        "rate":    adb.attendance_rate(total),
    })


# ════════════════════════════════════════════════════════════════════
#  API — CAMERA
# ════════════════════════════════════════════════════════════════════
@app.route("/api/stream/cctv")
def api_cctv_stream():
    return Response(cctv_stream_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/cameras")
def api_cameras():
    return jsonify({"saved": cam_mgr.get_saved(), "active": cam_mgr.get_active()})


@app.route("/api/cameras/add", methods=["POST"])
def api_cam_add():
    ok = cam_mgr.add_camera(request.json)
    return jsonify({"success": ok,
                    "error": "Label already exists" if not ok else ""})


@app.route("/api/cameras/set_active", methods=["POST"])
def api_cam_set_active():
    cam_mgr.set_active(request.json)
    return jsonify({"success": True})


@app.route("/api/cameras/delete", methods=["POST"])
def api_cam_delete():
    cam_mgr.delete_camera(request.json.get("label"))
    return jsonify({"success": True})


@app.route("/api/cameras/detect", methods=["POST"])
def api_cam_detect():
    found = cam_mgr.detect_webcams()
    added = sum(1 for c in found if cam_mgr.add_camera(c))
    return jsonify({"found": found, "added": added})


@app.route("/api/cameras/test", methods=["POST"])
def api_cam_test():
    cam = request.json
    ok, msg = cam_mgr.test_camera(cam, timeout=5)
    return jsonify({"success": ok, "message": msg})


# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
