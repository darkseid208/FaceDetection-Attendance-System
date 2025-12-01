"""
attendance.py

Optimized variant: larger UI preview and smoother camera while keeping recognition fast.
Changes made:
 - Separate UI preview size (preview_width/height) from recognition resize scale.
 - Default recognition FRAME_RESIZE_SCALE set to 0.35 (fast enough on most laptops).
 - PROCESS_EVERY_N_FRAMES defaults to 2 (skip every other frame for recognition).
 - UI_UPDATE_EVERY_N_FRAMES = 1 (update preview each cycle) and preview sized to 640x360.
 - Capture uses CAP_DSHOW when available and requests 1280x720 camera resolution.
 - Prefer ImageTk.PhotoImage for preview (generally faster than CTkImage on many systems).

If this is still slow, lower FRAME_RESIZE_SCALE (e.g. 0.25) or increase PROCESS_EVERY_N_FRAMES (e.g. 3).
"""

import os
import threading
import csv
import time
import traceback
from datetime import datetime

# ---------- Optional third-party imports (defensive) ----------
CV2_AVAILABLE = True
FR_AVAILABLE = True
PIL_AVAILABLE = True
CTKIMAGE_AVAILABLE = True

try:
    import cv2
except Exception:
    cv2 = None
    CV2_AVAILABLE = False

try:
    import numpy as np
except Exception:
    np = None

try:
    import face_recognition
except Exception:
    face_recognition = None
    FR_AVAILABLE = False

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
    PIL_AVAILABLE = False

# Some UIs import CTkImage from customtkinter; if not available we still import customtkinter above.
try:
    from customtkinter import CTkImage
except Exception:
    CTkImage = None
    CTKIMAGE_AVAILABLE = False

# customtkinter and tkinter's messagebox are required for UI, still surface friendly error if missing
try:
    import customtkinter as ctk
    from tkinter import messagebox
except Exception:
    # If CTk not available at import time, create minimal placeholders to allow import.
    ctk = None
    messagebox = None

# ---------- Configuration ----------
IMAGES_DIR = "images"
ATTENDANCE_CSV = "Attendance.csv"
PROFILES_JSON = "profiles.json"
CAMERA_INDEX = 0  # Default webcam

# mapping login username -> expected full uppercase name (used when ENFORCE_MAPPING True)
USER_FACE_MAP = {
    "student1": "SAMIR PRASAD",
    "student2": "SACHIN PRASAD",
    "student3": "ANINDITA BAIRAGI",
    "student4": "AHANA ROY",
}

FR_TOLERANCE = 0.45
ENFORCE_MAPPING = True

# Performance tuning (adjust to taste)
# NOTE: preview size controls how large the UI image appears; recognition uses a separate smaller scale.
FRAME_RESIZE_SCALE = 0.35        # scale applied when creating encodings/recognition (smaller -> faster)
PROCESS_EVERY_N_FRAMES = 2       # do recognition on every Nth frame
UI_UPDATE_EVERY_N_FRAMES = 1     # update shown UI image every N frames (1 = every time)

# Preview target size (UI) - larger -> clearer preview; does not affect recognition cost significantly
PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 360

# ---------- Helper: safe messagebox ----------
def _safe_show_error(title, message):
    try:
        if messagebox:
            messagebox.showerror(title, message)
        else:
            print(f"[ERROR] {title}: {message}")
    except Exception:
        print(f"[ERROR] {title}: {message}")


def _safe_show_info(title, message):
    try:
        if messagebox:
            messagebox.showinfo(title, message)
        else:
            print(f"[INFO] {title}: {message}")
    except Exception:
        print(f"[INFO] {title}: {message}")


def _safe_show_warning(title, message):
    try:
        if messagebox:
            messagebox.showwarning(title, message)
        else:
            print(f"[WARNING] {title}: {message}")
    except Exception:
        print(f"[WARNING] {title}: {message}")

# ---------- small utility to load profiles.json ----------
def _load_profiles_dict():
    try:
        p = os.path.join(os.path.dirname(__file__), PROFILES_JSON)
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            data = None
            try:
                import json
                data = json.load(f)
            except Exception:
                return {}
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                out = {}
                for s in data:
                    if isinstance(s, dict):
                        u = s.get("username") or s.get("Username") or ""
                        if u:
                            out[str(u).strip()] = s
                return out
    except Exception:
        pass
    return {}

# ---------- Main class (always defined) ----------
class MarkAttendancePage:
    def __init__(self, parent_frame, student_username=None, refresh_callback=None):
        # if CTk not available, raise a friendly import-time error when constructing UI
        if ctk is None:
            raise RuntimeError(
                "customtkinter is required for the attendance UI. Install it with:\n\n"
                "pip install customtkinter\n"
                "Then restart the application."
            )

        # UI layout
        self.frame = ctk.CTkFrame(parent_frame, fg_color="#0e1117")
        self.frame.pack(fill="both", expand=True)

        self.student_username = student_username
        self.refresh_callback = refresh_callback

        ctk.CTkLabel(
            self.frame,
            text="🎓 Mark Attendance",
            text_color="#e6edf3",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)

        self.last_info_frame = ctk.CTkFrame(self.frame, fg_color="#111827", corner_radius=10)
        self.last_info_frame.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            self.last_info_frame,
            text="Last Attendance",
            text_color="#e5e7eb",
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        self.last_info_label = ctk.CTkLabel(
            self.last_info_frame,
            text="Fetching…",
            text_color="#cbd5e1",
            font=("Segoe UI", 12),
            justify="left"
        )
        self.last_info_label.grid(row=1, column=0, sticky="w", padx=10, pady=(4, 10))

        refresh_btn = ctk.CTkButton(
            self.last_info_frame,
            text="↻ Refresh",
            width=100,
            height=30,
            fg_color="#374151",
            hover_color="#4b5563",
            text_color="#e5e7eb",
            command=self.auto_fetch_last_attendance_info
        )
        refresh_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=10, pady=10)
        self.last_info_frame.grid_columnconfigure(0, weight=1)

        self.start_btn = ctk.CTkButton(
            self.frame,
            text="Start Camera",
            command=self.start_recognition,
            fg_color="#4A6CF7",
            text_color="white",
            font=("Segoe UI", 15, "bold"),
            height=40,
            width=200
        )
        self.start_btn.pack(pady=10)

        self.stop_btn = ctk.CTkButton(
            self.frame,
            text="Stop Camera",
            command=self.stop_recognition,
            fg_color="#d9534f",
            text_color="white",
            font=("Segoe UI", 15, "bold"),
            height=40,
            width=200
        )
        self.stop_btn.pack(pady=10)

        self.video_label = ctk.CTkLabel(self.frame, fg_color="#0e1117")
        self.video_label.pack(pady=20)

        # Internal state
        self.cap = None
        self.running = False
        self.marked = False
        self.encodeListKnown = []
        self.student_info = {}
        self.classNames = []
        self.last_seen = {}
        self.detection_delay = 0.1

        # Threading & sync
        self._capture_thread = None
        self._process_thread = None
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._stop_event = threading.Event()
        self._frame_counter = 0

        # If face_recognition or cv2 aren't available, we will not attempt camera operations.
        if not CV2_AVAILABLE or not FR_AVAILABLE or not PIL_AVAILABLE:
            msg = "Missing dependencies for camera / face recognition:\n"
            if not CV2_AVAILABLE:
                msg += "- opencv-python (cv2)\n"
            if not FR_AVAILABLE:
                msg += "- face_recognition\n"
            if not PIL_AVAILABLE:
                msg += "- Pillow\n"
            msg += "\nInstall required packages and restart the app.\n\nExample:\n  pip install opencv-python face_recognition Pillow"
            # Show once in UI
            _safe_show_warning("Missing Dependencies", msg)

        # Load known faces in background (will be a no-op if cv2/face_recognition missing)
        threading.Thread(target=self.load_known_faces, daemon=True).start()
        # Populate last-attendance info
        self.auto_fetch_last_attendance_info()

    # ---------------- Attendance info helpers ----------------
    def auto_fetch_last_attendance_info(self):
        try:
            if not self.student_username:
                self._set_last_info_label("No user is logged in.", "#fca5a5")
                return

            csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ATTENDANCE_CSV))
            if not os.path.exists(csv_path):
                self._set_last_info_label("No attendance file found yet.", "#cbd5e1")
                return

            # get the most relevant last row (may lack registration)
            last_row = self._get_last_record_for_user(csv_path, self.student_username)
            if not last_row:
                self._set_last_info_label("No attendance for this user yet.", "#cbd5e1")
                return

            # Try to extract FullName + Registration + Dept from the chosen row (check many variants)
            def _pick_row_field(row, candidates):
                for c in candidates:
                    v = row.get(c)
                    if v and str(v).strip():
                        return str(v).strip()
                return ""

            full_name = _pick_row_field(last_row, ["FullName", "Fullname", "full_name", "Name", "name"])
            student_id = _pick_row_field(last_row, ["Registration", "Registration No", "RegistrationNo", "regno",
                                                    "StudentID", "studentid", "registration"])
            dept = _pick_row_field(last_row, ["Department", "Dept", "department", "course"])

            # If registration or dept missing in this row, try scanning other rows for same user/fullname
            if (not student_id) or (not dept):
                try:
                    with open(csv_path, "r", encoding="utf-8", newline="") as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                except Exception:
                    rows = []

                uname_search = str(self.student_username).strip().lower()
                candidate_sid = ""
                candidate_dept = ""
                # iterate reversed to prefer later entries
                for row in reversed(rows):
                    r_uname = (row.get("Username") or row.get("username") or "").strip().lower()
                    r_full = (row.get("FullName") or row.get("Fullname") or row.get("full_name") or row.get("Name") or "").strip()
                    matched = False
                    if r_uname and uname_search and (r_uname == uname_search):
                        matched = True
                    elif r_full and full_name and (str(r_full).strip().lower() == str(full_name).strip().lower()):
                        matched = True

                    if not matched:
                        continue

                    if not candidate_sid:
                        candidate_sid = (row.get("Registration") or row.get("Registration No") or row.get("RegistrationNo")
                                         or row.get("StudentID") or row.get("studentid") or row.get("regno") or "").strip()
                    if not candidate_dept:
                        candidate_dept = (row.get("Department") or row.get("Dept") or row.get("department") or row.get("course") or "").strip()
                    if candidate_sid and candidate_dept:
                        break

                if not student_id and candidate_sid:
                    student_id = candidate_sid
                if not dept and candidate_dept:
                    dept = candidate_dept

            # Final fallback: profiles.json (try by username then by normalized full name)
            if (not student_id) or (not dept):
                try:
                    profiles = _load_profiles_dict()
                    prof = profiles.get(self.student_username, {}) if isinstance(profiles, dict) else {}
                    if prof:
                        student_id = student_id or prof.get("student_id") or prof.get("studentId") or prof.get("studentID") or prof.get("registration") or ""
                        dept = dept or prof.get("department") or prof.get("dept") or prof.get("course") or ""
                    # also try lookup by full name key in profiles (some users store profiles keyed by name)
                    if (not student_id or not dept) and full_name:
                        # search profiles dict values for matching full_name (case-insensitive)
                        for k,v in (profiles.items() if isinstance(profiles, dict) else []):
                            try:
                                vn = (v.get("full_name") or v.get("fullName") or v.get("name") or "").strip().lower()
                                if vn and vn == full_name.strip().lower():
                                    student_id = student_id or v.get("student_id") or v.get("studentId") or v.get("registration") or ""
                                    dept = dept or v.get("department") or v.get("dept") or v.get("course") or ""
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass

            student_id = student_id or "Unknown"
            dept = dept or "Unknown"
            full_name = full_name or (last_row.get("FullName") or last_row.get("Fullname") or last_row.get("Name") or "Unknown")

            date_v = last_row.get("Date", "-")
            time_v = last_row.get("Time", "-")
            status = last_row.get("Status", "-")

            text = (
                f"Name: {full_name}\n"
                f"Registration No: {student_id}     Dept: {dept}\n"
                f"Date: {date_v}    Time: {time_v}      Status: {status}"
            )
            self._set_last_info_label(text)
        except Exception as e:
            self._set_last_info_label(f"Error: {e}", "#fca5a5")

    def _get_last_record_for_user(self, csv_path, username):
        """
        Robustly find the most recent attendance row for username.
        Fallback strategy:
          1) If CSV has 'Username' column -> use exact match (preferred).
          2) Else search rows and pick the latest match by Registration or FullName using profiles.json fallback.
        """
        last_row, last_dt = None, None
        try:
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception:
            return None

        # Normalize username we are searching for
        uname_search = str(username).strip() if username else ""

        # 1) Try Username column first (if exists)
        if rows:
            first_row = rows[0]
            # check existence of a username-like column
            username_col_name = None
            for cand in ("Username", "username", "User", "user"):
                if cand in first_row:
                    username_col_name = cand
                    break
            if username_col_name:
                for row in rows:
                    if (row.get(username_col_name, "").strip() or "") != uname_search:
                        continue
                    date_str = (row.get("Date") or "").strip()
                    time_str = (row.get("Time") or "").strip()
                    if not date_str:
                        continue
                    try:
                        dt = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        # try parsing date only
                        try:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                        except Exception:
                            continue
                    if last_dt is None or dt > last_dt:
                        last_dt, last_row = dt, row
                if last_row:
                    return last_row

        # 2) No Username column OR didn't find any row for username -> try by Registration or fullname using profiles.json
        profiles = _load_profiles_dict()
        prof = profiles.get(uname_search, {}) if isinstance(profiles, dict) else {}

        pid = prof.get("student_id") or prof.get("studentId") or prof.get("studentID") or prof.get("registration") or ""
        pname = prof.get("full_name") or prof.get("fullName") or prof.get("name") or ""

        # Search by registration/student id if available
        if pid:
            for row in rows:
                candidate = (
                    row.get("Registration") or row.get("Registration No") or row.get("registration") or
                    row.get("StudentID") or row.get("studentid") or row.get("regno") or ""
                )
                if str(candidate).strip() != str(pid).strip():
                    continue
                date_str = (row.get("Date") or "").strip()
                time_str = (row.get("Time") or "").strip()
                if not date_str:
                    continue
                try:
                    dt = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        continue
                if last_dt is None or dt > last_dt:
                    last_dt, last_row = dt, row
            if last_row:
                return last_row

        # 3) Search by full name fallback (case-insensitive)
        if pname:
            for row in rows:
                cand_name = row.get("FullName") or row.get("Fullname") or row.get("full_name") or row.get("Name") or ""
                if str(cand_name).strip().lower() != str(pname).strip().lower():
                    continue
                date_str = (row.get("Date") or "").strip()
                time_str = (row.get("Time") or "").strip()
                if not date_str:
                    continue
                try:
                    dt = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        continue
                if last_dt is None or dt > last_dt:
                    last_dt, last_row = dt, row
            if last_row:
                return last_row

        # 4) As a last resort: try matching any row by full name derived from username mapping
        alt_name = USER_FACE_MAP.get(username, "")
        if alt_name:
            for row in rows:
                cand_name = row.get("FullName") or row.get("Fullname") or row.get("full_name") or row.get("Name") or ""
                if str(cand_name).strip().upper() != str(alt_name).strip().upper():
                    continue
                date_str = (row.get("Date") or "").strip()
                time_str = (row.get("Time") or "").strip()
                if not date_str:
                    continue
                try:
                    dt = datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        continue
                if last_dt is None or dt > last_dt:
                    last_dt, last_row = dt, row
            if last_row:
                return last_row

        # 5) Nothing found
        return None

    def _set_last_info_label(self, text, fg="#cbd5e1"):
        try:
            self.last_info_label.configure(text=text, text_color=fg)
        except Exception:
            # schedule on main thread
            try:
                self.frame.after(0, lambda: self.last_info_label.configure(text=text, text_color=fg))
            except Exception:
                print("[WARN] Could not update last info label")

    # ---------------- Load encodings ----------------
    def load_known_faces(self, path=IMAGES_DIR):
        """
        Loads face encodings from images folder. Expected filename format:
            FULLNAME_STUDENTID_DEPT.jpg
        This function is defensive and will skip if cv2/face_recognition missing.
        """
        encodings = []
        info = {}
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass

        if not CV2_AVAILABLE or not FR_AVAILABLE:
            print("[WARN] load_known_faces skipped: cv2 or face_recognition not available.")
            self.encodeListKnown = []
            self.student_info = {}
            self.classNames = []
            return

        for fname in os.listdir(path):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            base = os.path.splitext(fname)[0]
            parts = base.split("_")
            if len(parts) >= 3:
                fullname, student_id, dept = parts[:3]
            else:
                fullname, student_id, dept = parts[0], "Unknown", "Unknown"

            img_path = os.path.join(path, fname)
            img = cv2.imread(img_path) if cv2 else None
            if img is None:
                print(f"[WARN] Could not read image {img_path}")
                continue

            try:
                small = cv2.resize(img, (0, 0), fx=FRAME_RESIZE_SCALE, fy=FRAME_RESIZE_SCALE)
                rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                encs = face_recognition.face_encodings(rgb_small) if face_recognition else []
                if not encs:
                    print(f"[WARN] No face found in {fname}")
                    continue
                encodings.append(encs[0])
                info[fullname.strip().upper()] = (student_id.strip(), dept.strip())
            except Exception as e:
                print(f"[ERROR] loading {fname}: {e}")
                traceback.print_exc()

        self.encodeListKnown = encodings
        self.student_info = info
        self.classNames = list(info.keys())
        print("[INFO] Loaded encodings for:", self.classNames)

    # ---------------- Start recognition ----------------
    def start_recognition(self):
        # If libs missing, show guidance
        if not CV2_AVAILABLE or not FR_AVAILABLE or not PIL_AVAILABLE:
            missing = []
            if not CV2_AVAILABLE: missing.append("opencv-python (cv2)")
            if not FR_AVAILABLE: missing.append("face_recognition")
            if not PIL_AVAILABLE: missing.append("Pillow")
            msg = "Cannot start camera — missing dependencies:\n - " + "\n - ".join(missing) + \
                  "\n\nInstall them and restart the app:\n  pip install opencv-python face_recognition Pillow"
            _safe_show_error("Missing dependencies", msg)
            return

        if self.running:
            return
        if not self.encodeListKnown:
            _safe_show_info("Info", "Face encodings are still loading or none found in images/; please add images and wait.")
            return

        self._stop_event.clear()
        self._frame_counter = 0
        self._latest_frame = None

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)

        self._capture_thread.start()
        self._process_thread.start()

        self.running = True
        self.marked = False
        print("[INFO] Camera threads started.")

    def _capture_loop(self):
        try:
            cap = None
            try:
                # prefer CAP_DSHOW on Windows for lower-latency
                cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
            except Exception:
                cap = cv2.VideoCapture(CAMERA_INDEX)

            if not cap or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(CAMERA_INDEX)
                except Exception:
                    cap = None

            if not cap or not cap.isOpened():
                self.frame.after(0, lambda: _safe_show_error("Error", "Could not open webcam."))
                return

            # request a reasonable camera resolution (driver may ignore)
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
            except Exception:
                pass

            self.cap = cap

            ui_update_counter = 0

            while not self._stop_event.is_set():
                success, frame = cap.read()
                if not success or frame is None:
                    time.sleep(0.01)
                    continue

                # store latest frame for processing thread
                with self._frame_lock:
                    self._latest_frame = frame.copy()

                # Update UI (preview) - produce preview sized image (maintain aspect ratio)
                ui_update_counter = (ui_update_counter + 1) % UI_UPDATE_EVERY_N_FRAMES
                if ui_update_counter == 0:
                    try:
                        preview = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
                        rgb_preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb_preview)
                        # Prefer ImageTk.PhotoImage for speed on many platforms
                        if ImageTk is not None:
                            tk_img = ImageTk.PhotoImage(pil_img)
                            self.frame.after(0, lambda img=tk_img: self._set_tk_video_image(img))
                        elif CTKIMAGE_AVAILABLE:
                            ctki = CTkImage(light_image=pil_img, dark_image=pil_img, size=(PREVIEW_WIDTH, PREVIEW_HEIGHT))
                            self.frame.after(0, lambda ctki=ctki: self._set_video_image(ctki))
                    except Exception:
                        pass

                # small sleep to yield
                time.sleep(0.005)
        except Exception as e:
            print(f"[ERROR] capture loop: {e}")
            traceback.print_exc()
        finally:
            try:
                if cap and getattr(cap, "isOpened", lambda: False)():
                    cap.release()
            except Exception:
                pass
            self.cap = None
            print("[INFO] Capture loop ended.")

    def _set_video_image(self, ctki):
        try:
            self.video_label.configure(image=ctki)
            self.video_label.image = ctki
        except Exception:
            pass

    def _set_tk_video_image(self, tk_img):
        try:
            self.video_label.configure(image=tk_img)
            self.video_label.image = tk_img
        except Exception:
            pass

    # ---------------- Processing loop ----------------
    def _process_loop(self):
        try:
            while not self._stop_event.is_set():
                frame = None
                with self._frame_lock:
                    if self._latest_frame is not None:
                        frame = self._latest_frame.copy()
                if frame is None:
                    time.sleep(0.02)
                    continue

                self._frame_counter += 1
                if self._frame_counter % max(1, PROCESS_EVERY_N_FRAMES) != 0:
                    time.sleep(0.003)
                    continue

                try:
                    # resize for recognition (smaller => faster)
                    small_img = cv2.resize(frame, (0, 0), fx=FRAME_RESIZE_SCALE, fy=FRAME_RESIZE_SCALE)
                    rgb_small = cv2.cvtColor(small_img, cv2.COLOR_BGR2RGB)

                    faces = face_recognition.face_locations(rgb_small)
                    if len(faces) != 1:
                        self.last_seen.clear()
                        time.sleep(0.003)
                        continue

                    encs = face_recognition.face_encodings(rgb_small, faces)
                    if not encs:
                        self.last_seen.clear()
                        time.sleep(0.003)
                        continue

                    current_time = time.time()

                    for encodeFace, faceLoc in zip(encs, faces):
                        matches = face_recognition.compare_faces(self.encodeListKnown, encodeFace, tolerance=FR_TOLERANCE)
                        faceDis = face_recognition.face_distance(self.encodeListKnown, encodeFace)
                        if len(faceDis) == 0:
                            continue

                        matchIndex = int(np.argmin(faceDis))
                        best_distance = float(faceDis[matchIndex])
                        is_match = bool(matches[matchIndex]) and (best_distance <= FR_TOLERANCE)

                        if is_match:
                            detected_name = self.classNames[matchIndex].upper()
                            expected_name = (USER_FACE_MAP.get(self.student_username, "") or "").upper()

                            print(f"[DEBUG] Detected face: {detected_name}, Logged in as: {self.student_username}")

                            if ENFORCE_MAPPING and not expected_name:
                                self.frame.after(0, lambda: _safe_show_warning(
                                    "Access Denied",
                                    f"No face mapping found for login '{self.student_username}'.")) 
                                self._stop_event.set()
                                break

                            if expected_name and expected_name != detected_name:
                                msg = f"Detected face: {detected_name}\nThis login is only for {self.student_username}."
                                self.frame.after(0, lambda m=msg: _safe_show_warning("Access Denied", m))
                                self._stop_event.set()
                                break

                            if detected_name not in self.last_seen:
                                self.last_seen[detected_name] = current_time
                            elif (current_time - self.last_seen[detected_name]) >= self.detection_delay:
                                # mark attendance on main thread to keep UI consistent
                                self.frame.after(0, lambda dn=detected_name: self._mark_and_stop(dn))
                                self._stop_event.set()
                                break
                        else:
                            self.last_seen.clear()
                except Exception as e:
                    print(f"[ERROR] process loop inner: {e}")
                    traceback.print_exc()

                time.sleep(0.003)
        except Exception as e:
            print(f"[ERROR] process loop: {e}")
            traceback.print_exc()
        finally:
            print("[INFO] Process loop ended.")

    # ---------------- Mark and force-stop ----------------
    def _mark_and_stop(self, detected_name):
        try:
            self.mark_attendance(detected_name)
        except Exception as e:
            print(f"[ERROR] marking attendance in _mark_and_stop: {e}")
        finally:
            try:
                self._stop_event.set()
                if self.cap:
                    try:
                        if getattr(self.cap, "isOpened", lambda: False)():
                            self.cap.release()
                    except Exception:
                        pass
                    self.cap = None
                try:
                    self.video_label.configure(image=None)
                    self.video_label.image = None
                except Exception:
                    pass
                self.running = False
                print("[INFO] Camera force-closed immediately after attendance.")
            except Exception as e:
                print(f"[WARN] _mark_and_stop cleanup error: {e}")

    # ---------------- Stop recognition ----------------
    def stop_recognition(self, clear_label=True):
        self._stop_event.set()
        try:
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self._process_thread and self._process_thread.is_alive():
                self._process_thread.join(timeout=1.0)
        except Exception:
            pass

        try:
            if self.cap:
                if getattr(self.cap, "isOpened", lambda: False)():
                    self.cap.release()
        except Exception:
            pass
        self.cap = None

        if clear_label:
            try:
                self.video_label.configure(image=None)
                self.video_label.image = None
            except Exception:
                pass

        self.running = False
        print("[INFO] Camera stopped and released.")

    # ---------------- Mark attendance (CSV) ----------------
    def mark_attendance(self, detected_name):
        """
        Mark attendance row. Enhancements:
         - If student_info doesn't contain Registration/Department, attempt to read from profiles.json
         - already_present check is robust: checks by Registration (preferred) OR Username (if available)
        """
        if self.marked:
            return

        # get Registration and Department from loaded encodings info (key = FULLNAME UPPER)
        student_id, dept = self.student_info.get(detected_name, ("Unknown", "Unknown"))
        username = self.student_username or "Unknown"
        csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ATTENDANCE_CSV))
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # --- NEW: fallback to profiles.json if dept or registration unknown ---
        if (not student_id or str(student_id).strip() == "" or student_id == "Unknown") or (not dept or str(dept).strip() == "" or dept == "Unknown"):
            try:
                profiles = _load_profiles_dict()
                prof = profiles.get(username, {}) if isinstance(profiles, dict) else {}
                # try fields commonly used
                student_id = student_id or prof.get("student_id") or prof.get("studentId") or prof.get("studentID") or prof.get("registration") or ""
                dept = dept or prof.get("department") or prof.get("dept") or prof.get("course") or ""
            except Exception:
                pass

        # ensure CSV header (use Registration No label)
        if not os.path.exists(csv_path):
            try:
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    csv.writer(f).writerow(["Registration No", "FullName", "Username", "Department", "Date", "Time", "Status"])
            except Exception as e:
                _safe_show_error("Error", f"Could not create attendance CSV: {e}")
                return

        # already_present check: accept presence if either Registration (preferred) OR Username already has a present record for today
        already_present = False
        try:
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # normalize candidate values
                    row_sid = (
                        (row.get("Registration") or row.get("Registration No") or row.get("RegistrationNo")) or
                        (row.get("StudentID") or row.get("studentid") or row.get("registration")) or
                        ""
                    )
                    row_sid = str(row_sid).strip()
                    row_uname = (row.get("Username") or row.get("username") or "").strip()
                    row_date = (row.get("Date") or "").strip()
                    if row_date != date_str:
                        continue
                    # check by Registration if we have one
                    if student_id and student_id != "Unknown" and row_sid and row_sid == str(student_id).strip():
                        already_present = True
                        break
                    # otherwise fallback to username match
                    if username and row_uname and row_uname == str(username).strip():
                        already_present = True
                        break
        except FileNotFoundError:
            already_present = False
        except Exception:
            already_present = False

        if already_present:
            _safe_show_info("Info", f"{detected_name.title()} already marked present today.")
            # refresh last info to show correct data
            self.auto_fetch_last_attendance_info()
            return

        try:
            # final fallback: ensure non-empty fields written
            write_sid = student_id if student_id and student_id != "Unknown" else ""
            write_dept = dept if dept and dept != "Unknown" else ""
            with open(csv_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([write_sid, detected_name.title(), username, write_dept, date_str, time_str, "Present"])
            self.marked = True
            _safe_show_info("Success", f"Attendance marked for {detected_name.title()}")
            self.auto_fetch_last_attendance_info()
            print(f"[INFO] Attendance marked for {detected_name.title()} (Reg: {write_sid}, User: {username}, Dept: {write_dept})")
        except Exception as e:
            print(f"[ERROR] could not write CSV: {e}")
            traceback.print_exc()
            _safe_show_error("Error", f"Failed to mark attendance: {e}")

        # refresh callback if present
        if self.refresh_callback:
            try:
                self.refresh_callback()
            except Exception as e:
                print(f"[WARN] Could not refresh view: {e}")

# ---------------------- Test harness ----------------------
if __name__ == "__main__":
    # if run standalone we require customtkinter; if not available, inform user
    if ctk is None:
        print("customtkinter not installed. Run: pip install customtkinter")
    else:
        root = ctk.CTk()
        root.geometry("800x720")
        root.title("Mark Attendance - Test (Robust & Smooth)")

        page = MarkAttendancePage(root, student_username="student1")

        help_text = (
            "Test harness:\n"
            "- Ensure you have an 'images' folder next to this script.\n"
            "- Add images named: FULLNAME_STUDENTID_DEPT.jpg\n"
            "  Example: SAMIR PRASAD_S101_CSE.jpg\n"
            "- Click Start Camera and show the same person's face."
        )

        ctk.CTkLabel(root, text=help_text, wraplength=760, justify="left").pack(side="bottom", pady=8)
        root.mainloop()
