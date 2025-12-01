import traceback
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="face_recognition_models")

import os
import csv
import math
import json
import re
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, date

# Added imports for duplicate-guarding
import threading
import time

# optional matplotlib for teacher graphs
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    matplotlib = None
    Figure = None
    FigureCanvasTkAgg = None

# local imports (student.py must define ManageStudentsTabs and AddStudentPage)
try:
    from student import ManageStudentsTabs, AddStudentPage
except Exception:
    tb = traceback.format_exc()
    try:
        messagebox.showerror("Import error", f"Failed to import from student.py:\n\n{tb}")
    except Exception:
        print("Failed to import from student.py. Traceback:\n", tb)
    raise

# attendance marking page
try:
    from attendance import MarkAttendancePage
except Exception:
    tb = traceback.format_exc()
    try:
        messagebox.showerror("Import error", f"Failed to import attendance.py:\n\n{tb}")
    except Exception:
        print("Failed to import attendance.py. Traceback:\n", tb)
    raise

# optional Pillow for profile images
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

# ============== CONFIG ==============
TOTAL_CLASSES = 50
TARGET_ATTENDANCE = 0.75
CSV_FILENAME = "Attendance.csv"
PROFILES_JSON = "profiles.json"
PROFILE_IMAGE_DIR = "profile_images"
STUDENTS_JSON = "students.json"
# =====================================


# ---------- Scrollable CTkFrame helper ----------
class ScrollableFrame(ctk.CTkFrame):
    """
    A CTkFrame containing an internal Canvas + vertical scrollbar and
    an inner CTkFrame where dashboard widgets are added.
    Use .inner as the parent for all widgets.
    """
    def __init__(self, parent, fg_color=None, **kwargs):
        super().__init__(parent, fg_color=fg_color or "#0e1117", **kwargs)

        self.canvas = tk.Canvas(self, bg=self.cget("fg_color"), highlightthickness=0)
        self.v_scroll = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)

        self.inner = ctk.CTkFrame(self.canvas, fg_color=self.cget("fg_color"))
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        def resize_inner(event):
            self.canvas.itemconfig(self.window, width=event.width)
        self.canvas.bind("<Configure>", resize_inner)

        def update_scroll(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.inner.bind("<Configure>", update_scroll)

        def mouse_scroll(event):
            delta = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(delta, "units")

        self.canvas.bind_all("<MouseWheel>", mouse_scroll)


def _here(*parts):
    return os.path.join(os.path.dirname(__file__), *parts)

def _profiles_path():
    return _here(PROFILES_JSON)

def _load_profiles():
    p = _profiles_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _guess_profile_image_path(username: str):
    if not username:
        return None
    try:
        profiles = _load_profiles()
        prof = profiles.get(username, {}) if isinstance(profiles, dict) else {}
        pic_val = prof.get("profile_pic") or prof.get("profilePic") or None
        if pic_val:
            candidate = pic_val if os.path.isabs(pic_val) else _here(pic_val)
            if os.path.exists(candidate):
                return candidate
    except Exception:
        pass
    try:
        base1 = _here(PROFILE_IMAGE_DIR)
        for ext in ("png", "jpg", "jpeg"):
            p = os.path.join(base1, f"{username}.{ext}")
            if os.path.exists(p):
                return p
    except Exception:
        pass
    try:
        base2 = _here("media", "profile_pics")
        for ext in ("png", "jpg", "jpeg"):
            p = os.path.join(base2, f"{username}.{ext}")
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return None

def _read_students_json():
    path = _here(STUDENTS_JSON)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return list(data.values())
            elif isinstance(data, list):
                return data
    except Exception:
        pass
    return []
def _count_students():
    return len(_read_students_json())

def _count_attendance_rows():
    path = _here(CSV_FILENAME)
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
            if not rows:
                return 0
            return max(0, len(rows) - 1)
    except Exception:
        return 0

def _parse_date_str(s):
    if not s:
        return None
    s = s.strip()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%Y/%m/%d", "%d %B %Y", "%Y-%m-%d %H:%M:%S")
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # Try to extract ISO date substring
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            pass
    # Try common dd/mm/yyyy patterns
    m2 = re.search(r"(\d{2}/\d{2}/\d{4})", s)
    if m2:
        try:
            return datetime.strptime(m2.group(1), "%d/%m/%Y").date()
        except Exception:
            pass
    return None

# ---------------- Username normalizer ----------------
def _normalize_username(u):
    if not u:
        return ""
    try:
        return str(u).strip().lower()
    except Exception:
        return str(u).strip()

def _today_attendance_stats(project_root=None, csv_filename=None, students_json=None, total_students_override=None):
    project_root = project_root or os.path.dirname(__file__)
    csv_filename = csv_filename or CSV_FILENAME
    students_json = students_json or STUDENTS_JSON

    csv_path = os.path.join(project_root, csv_filename)
    today_str = date.today().isoformat()  # 'YYYY-MM-DD'

    present_today_set = set()
    all_usernames_seen = set()
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                headers = [h.strip() for h in (reader.fieldnames or [])]
                headers_l = [h.lower() for h in headers]

                username_col = None
                date_col = None
                status_col = None
                for cand in ("username", "user", "user name", "fullname", "fullName", "FullName", "Username"):
                    if cand.lower() in headers_l:
                        username_col = headers[headers_l.index(cand.lower())]
                        break
                for cand in ("date", "day", "Date", "timestamp", "Datetime"):
                    if cand.lower() in headers_l:
                        date_col = headers[headers_l.index(cand.lower())]
                        break
                for cand in ("status", "Status", "presence", "Presence"):
                    if cand.lower() in headers_l:
                        status_col = headers[headers_l.index(cand.lower())]
                        break

                present_values = {
                    "present", "p", "1", "yes", "true", "y",
                    "present✓", "present✔", "present✅"
                }

                for row in reader:
                    username = (row.get(username_col) or "").strip() if username_col else (row.get(headers[0]) or "").strip()
                    row_date = (row.get(date_col) or "").strip() if date_col else ""
                    status = (row.get(status_col) or "").strip().lower() if status_col else ""

                    if username:
                        all_usernames_seen.add(_normalize_username(username))

                    if row_date and " " in row_date:
                        row_date = row_date.split(" ")[0]

                    if row_date == today_str and status in present_values:
                        present_today_set.add(_normalize_username(username))
        except Exception:
            present_today_set = set()

    present_today = len(present_today_set)

    total_students = None
    sj_path = os.path.join(project_root, students_json)
    if os.path.exists(sj_path):
        try:
            with open(sj_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            usernames = set()
            if isinstance(data, dict):
                for key, s in data.items():
                    if isinstance(s, dict):
                        u = s.get("username") or s.get("Username") or key
                        if u:
                            usernames.add(_normalize_username(u))
            elif isinstance(data, list):
                for s in data:
                    if isinstance(s, dict):
                        u = s.get("username") or s.get("Username")
                        if u:
                            usernames.add(_normalize_username(u))

            if usernames:
                total_students = len(usernames)
        except Exception:
            total_students = None

    if total_students_override is not None:
        try:
            total_students = int(total_students_override)
        except Exception:
            pass

    if total_students is None:
        if "TOTAL_STUDENTS" in globals() and isinstance(globals().get("TOTAL_STUDENTS"), int):
            total_students = globals().get("TOTAL_STUDENTS")
        else:
            total_students = max(1, len(all_usernames_seen))

    absent_today = max(0, total_students - present_today)
    present_pct = (present_today / total_students) if total_students else 0.0

    return present_today, absent_today, present_pct

def _last_attendance_rows(limit=5):
    csv_path = _here(CSV_FILENAME)
    if not os.path.exists(csv_path):
        return []
    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            if not reader:
                return []
            last = reader[-limit:]
            out = []
            for row in reversed(last):
                raw_username = (row.get("Username") or row.get("username") or row.get("User") or row.get("user") or "").strip()
                if not raw_username and len(row) > 0:
                    for v in row.values():
                        if v and str(v).strip():
                            raw_username = str(v).strip()
                            break

                d = row.get("Date") or row.get("date") or ""
                t = row.get("Time") or row.get("time") or ""
                parsed_date = _parse_date_str(d)
                parsed_time = None
                try:
                    parsed_time = datetime.strptime(t, "%H:%M:%S").time()
                except Exception:
                    parsed_time = None
                if parsed_date and parsed_time:
                    dt_str = datetime.combine(parsed_date, parsed_time).strftime("%Y-%m-%d %H:%M:%S")
                elif parsed_date:
                    dt_str = parsed_date.isoformat()
                elif d:
                    dt_str = d
                else:
                    dt_str = (row.get("Timestamp") or row.get("timestamp") or "").strip() or ""
                normalized = _normalize_username(raw_username)
                out.append({
                    "username": raw_username,
                    "username_norm": normalized,
                    "status": (row.get("Status") or row.get("status") or "").strip(),
                    "datetime": dt_str,
                    "raw": row
                })
            return out
    except Exception:
        return []

def _recent_students_activity(limit_students=4, rows_per_student=3):
    rows = _last_attendance_rows(limit=500)
    if not rows:
        return []
    picked = {}
    order = []
    for r in rows:
        uname_norm = r.get("username_norm") or ""
        if not uname_norm:
            uname_norm = _normalize_username(r.get("username") or "")
            # Skip rows where username is empty OR looks like a date (prevents the wrong card)
        if (not uname_norm) or re.match(r"\d{4}-\d{2}-\d{2}", uname_norm):
            continue

        if uname_norm not in picked:
            picked[uname_norm] = []
            order.append(uname_norm)
        if len(picked[uname_norm]) < rows_per_student:
            picked[uname_norm].append(r)
        if len(order) >= limit_students:
            full = all(len(picked[u]) >= rows_per_student for u in order[:limit_students])
            if full:
                break

    profiles = _load_profiles()
    profiles_norm = {}
    if isinstance(profiles, dict):
        for k,v in profiles.items():
            norm = _normalize_username(k)
            profiles_norm[norm] = v
            try:
                inner_un = v.get("username") or v.get("Username") or ""
                if inner_un:
                    profiles_norm[_normalize_username(inner_un)] = v
            except Exception:
                pass

    students = _read_students_json()
    by_un = {}
    if isinstance(students, list):
        for s in students:
            try:
                u = s.get("username") or s.get("Username") or s.get("user") or ""
            except Exception:
                u = ""
            if u:
                by_un[_normalize_username(u)] = s
    elif isinstance(students, dict):
        for k,s in students.items():
            if not isinstance(s, dict):
                continue
            u = s.get("username") or s.get("Username") or k
            if u:
                by_un[_normalize_username(u)] = s

    out = []
    for uname_norm in order[:limit_students]:
        activities = picked.get(uname_norm) or []
        full = ""
        try:
            prof = profiles_norm.get(uname_norm, {}) or {}
            full = prof.get("full_name") or prof.get("fullName") or prof.get("name") or ""
        except Exception:
            full = ""
        if not full:
            srec = by_un.get(uname_norm, {}) or {}
            full = srec.get("full_name") or srec.get("fullName") or srec.get("name") or ""
        if not full:
            first_act = activities[0] if activities else {}
            raw_un = first_act.get("username") or ""
            if raw_un:
                full = raw_un
            else:
                full = uname_norm or "<unknown>"
        activities_sorted = sorted(activities, key=lambda x: x.get("datetime") or "", reverse=True)
        out.append({"username": uname_norm, "full_name": full, "activities": activities_sorted})
    return out

# ---------------- attendance timeseries for graph ----------------
def _attendance_timeseries_for_user(username: str):
    csv_path = _here(CSV_FILENAME)
    if not os.path.exists(csv_path):
        return [], [], []
    present_values = {"present", "p", "1", "yes", "true", "y", "present✓", "present✔", "present✅"}
    per_date = {}
    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = [h.strip() for h in (reader.fieldnames or [])]
            hdr = {k.lower(): k for k in fields}
            col_user = hdr.get("username", "Username")
            col_status = hdr.get("status", "Status")
            col_date = hdr.get("date", "Date")
            for row in reader:
                user_val = (row.get(col_user) or "").strip()
                if user_val != (username or ""):
                    if _normalize_username(user_val) != _normalize_username(username):
                        continue
                status_val = (row.get(col_status) or "").strip().lower()
                date_val = (row.get(col_date) or "").strip()
                parsed = _parse_date_str(date_val)
                if not parsed:
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_val or "")
                    if m:
                        try:
                            parsed = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                        except Exception:
                            parsed = None
                if not parsed: continue
                flag = 1 if (status_val in present_values) else 0
                per_date[parsed] = max(per_date.get(parsed, 0), flag)
    except Exception:
        return [], [], []
    if not per_date:
        return [], [], []
    dates_sorted = sorted(per_date.keys())
    daily_present = [per_date[d] for d in dates_sorted]
    cum = 0
    cum_pct = []
    for v in daily_present:
        cum += v
        pct = (cum / TOTAL_CLASSES) * 100.0 if TOTAL_CLASSES else 0.0
        cum_pct.append(pct)
    return dates_sorted, daily_present, cum_pct

# --------------- UI class ----------------
class Face_Reconition_System:
    def __init__(self, root, authenticated=False, user_role=None, username=None, student_id=None):
        self.root = root
        self.user_role = user_role
        self.username = username
        self.login_username = username
        self.student_id = student_id
        self.target_attendance = TARGET_ATTENDANCE
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.cached_pages = {}
        self._topbar_avatar_img = None

        # bottom graph panel state
        self._teacher_graph_panel = None
        self._teacher_graph_fig = None
        self._teacher_graph_canvas = None
        self._teacher_graph_scrollcanvas = None
        self._selected_graph_username = None
        self._selected_graph_fullname = None
        self._teacher_graph_maximized = False
        # teacher KPI autos-refresh state (used by periodic updater)
        self._teacher_kpi_job = None
        self._teacher_kpi_widgets = {}
        # CSV watcher to detect external attendance writes and refresh KPIs (teacher view)
        self._csv_mtime = None
        self._csv_watcher_job = None
        self._csv_watcher_interval_ms = 2000  # check every 2s (adjust as desired)
        # UI element for visual refresh timestamp and toast
        self._kpi_last_refreshed_label = None
        self._kpi_toast_job = None

        # --- single-run guards & small cache to avoid duplicate heavy work ---
        self._encodings_lock = threading.Lock()
        self._encodings_loaded = False
        self.encodings = None

        # short-term cache for attendance lookups to avoid duplicate CSV reads (TTL in seconds)
        self._attendance_cache = {}   # username -> {'ts': float, 'result': (present_count, total_classes)}
        self._attendance_cache_ttl = 1.0  # seconds (tweak if needed)

        if not authenticated:
            from User_Authentication import User_Authentication
            self.clear_root()
            self._init_ttk_theme_once(self.root)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            User_Authentication(self.root)
            return

        self.root.geometry("1200x700+100+50")
        self.root.title("Student Management Dashboard")
        self.root.configure(bg="#0e1117")

        # theme colours
        self.sidebar_bg = "#0b1220"
        self.main_bg = "#0e1117"
        self.card_bg = "#1f252e"
        self.text_primary = "#e6edf3"
        self.text_secondary = "#a9b1ba"
        self.white = "#ffffff"
        self.accent = "#6f42c1"

        self._init_ttk_theme_once(self.root)
        self.setup_sidebar()
        self.setup_main_frame()
        self.select_menu("Dashboard")

    def _init_ttk_theme_once(self, root):
        try:
            style = ttk.Style(root)
            try:
                style.theme_use("clam")
            except Exception:
                pass
            style.configure("Solid.Treeview", background=self.main_bg, fieldbackground=self.main_bg, foreground=self.text_primary, rowheight=24)
            style.configure("Solid.Treeview.Heading", background=self.card_bg, foreground=self.text_primary)
        except Exception:
            pass

    def _on_close(self):
        try:
            # cancel periodic KPI job if running
            try:
                if getattr(self, "_teacher_kpi_job", None):
                    self.root.after_cancel(self._teacher_kpi_job)
                    self._teacher_kpi_job = None
            except Exception:
                pass
            # cancel csv watcher if running
            try:
                if getattr(self, "_csv_watcher_job", None):
                    self.root.after_cancel(self._csv_watcher_job)
                    self._csv_watcher_job = None
            except Exception:
                pass
            # cancel toast if running
            try:
                if getattr(self, "_kpi_toast_job", None):
                    self.root.after_cancel(self._kpi_toast_job)
                    self._kpi_toast_job = None
            except Exception:
                pass
            self.root.destroy()
        except Exception:
            os._exit(0)

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, fg_color=self.sidebar_bg, width=260, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", pady=(24, 8))
        ctk.CTkLabel(brand, text=" 🎓 CampusOne", font=("Segoe UI", 20, "bold"), text_color=self.white).pack(anchor="w", padx=20)

        # Add "View Records" into Teacher menu
        if self.user_role == "Student":
            menu_items = ["Dashboard", "Mark Attendance", "Attendance Record", "Logout"]
        elif self.user_role == "Teacher":
            menu_items = ["Dashboard", "Manage Students", "View Records", "Logout"]
        else:
            menu_items = ["Dashboard", "Logout"]

        self.menu_buttons = {}
        for item in menu_items:
            btn = ctk.CTkButton(self.sidebar, text=item, fg_color="transparent", hover_color="#111827", corner_radius=8, text_color=self.white, command=lambda name=item: self.select_menu(name))
            btn.pack(fill="x", padx=12, pady=6)
            self.menu_buttons[item] = btn

    def setup_main_frame(self):
        # main_frame will contain all content; bottom graph panel is placed inside dashboard page itself
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.main_bg)
        self.main_frame.pack(fill="both", expand=True)

    def _user_initials(self, username):
        if not username: return "U"
        parts = str(username).strip().split()
        if len(parts) == 1: return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def _redraw_topbar_profile(self):

        profiles = _load_profiles()
    # ✅ Always load using permanent login username
        if self.login_username in profiles:
            prof = profiles[self.login_username]
        else:
            prof = {}
            
        """
        Robustly set the topbar display name and avatar:
        - Prefer full_name from profiles.json (by key or inner username)
        - Fall back to students.json to find a matching username -> full_name
        - Fall back to the raw username
        - Draw profile image if available, else initials
        """
        display_name = self.username or "User"
        img_path = None
        try:
            profiles = _load_profiles() or {}
            # 1) direct key lookup
            prof = {}
            if isinstance(profiles, dict):
                prof = profiles.get(self.username, {}) or {}
            # 2) if no direct match, try to find a profile where inner username matches
            if not prof and isinstance(profiles, dict):
                target_norm = _normalize_username(self.username)
                for k, v in profiles.items():
                    if not isinstance(v, dict):
                        continue
                    inner_un = (v.get("username") or v.get("Username") or "").strip()
                    if inner_un and _normalize_username(inner_un) == target_norm:
                        prof = v
                        break
            # 3) extract full name and picture if present
            full = ""
            try:
                full = prof.get("full_name") or prof.get("fullName") or prof.get("name") or ""
            except Exception:
                full = ""
            if full:
                display_name = full

            pic = ""
            try:
                pic = prof.get("profile_pic") or prof.get("profilePic") or ""
                if pic:
                    candidate = pic if os.path.isabs(pic) else _here(pic)
                    if os.path.exists(candidate):
                        img_path = candidate
            except Exception:
                img_path = None

            # 4) if we still don't have a full name, search students.json
            if (not full) and os.path.exists(_here(STUDENTS_JSON)):
                try:
                    students = _read_students_json()
                    target_norm = _normalize_username(self.username)
                    # if students is a list of dicts
                    if isinstance(students, list):
                        for s in students:
                            if not isinstance(s, dict):
                                continue
                            u = (s.get("username") or s.get("Username") or "").strip()
                            if u and _normalize_username(u) == target_norm:
                                candidate_full = s.get("full_name") or s.get("fullName") or s.get("name") or ""
                                if candidate_full:
                                    display_name = candidate_full
                                    break
                    # if students is a dict keyed by id/username
                    elif isinstance(students, dict):
                        # try direct key
                        srec = students.get(self.username) or students.get(target_norm) or None
                        if isinstance(srec, dict):
                            candidate_full = srec.get("full_name") or srec.get("fullName") or srec.get("name") or ""
                            if candidate_full:
                                display_name = candidate_full
                        else:
                            # scan values for inner username match
                            for k, srec in students.items():
                                if not isinstance(srec, dict):
                                    continue
                                u = (srec.get("username") or srec.get("Username") or "").strip()
                                if u and _normalize_username(u) == target_norm:
                                    candidate_full = srec.get("full_name") or srec.get("fullName") or srec.get("name") or ""
                                    if candidate_full:
                                        display_name = candidate_full
                                        break
                except Exception:
                    pass

            # 5) If still no img_path, try the fallback guesser (covers profile_images/ and media/profile_pics)
            if not img_path:
                try:
                    img_path = _guess_profile_image_path(self.username or "")
                except Exception:
                    img_path = None
        except Exception:
            # paranoid fallback: try guesser only
            try:
                img_path = _guess_profile_image_path(self.username or "")
            except Exception:
                img_path = None

        # update name label if exists
        if hasattr(self, "_topbar_name_label") and self._topbar_name_label:
            try:
                self._topbar_name_label.configure(text=display_name)
            except Exception:
                pass

        # draw avatar onto the canvas (image preferred, else initials)
        if hasattr(self, "_topbar_avatar_canvas") and self._topbar_avatar_canvas:
            try:
                cv = self._topbar_avatar_canvas
                cv.delete("all")
                cv.create_oval(2,2,62,62, fill="#334155", outline="#334155")
                drew_image = False
                if img_path and Image is not None and ImageTk is not None:
                    try:
                        im = Image.open(img_path).convert("RGBA")
                        w,h = im.size
                        side = min(w,h)
                        left = (w-side)//2; top = (h-side)//2
                        im = im.crop((left,top,left+side,top+side)).resize((60,60))
                        self._topbar_avatar_img = ImageTk.PhotoImage(im)
                        cv.create_image(32,32, image=self._topbar_avatar_img)
                        drew_image = True
                    except Exception:
                        drew_image = False
                if not drew_image:
                    initials = self._user_initials(display_name)
                    cv.create_text(32,32, text=initials, fill="#e5e7eb", font=("Segoe UI", 14, "bold"))
            except Exception:
                pass

    def select_menu(self, name):
        for k,b in self.menu_buttons.items():
            b.configure(fg_color="#111827" if k==name else "transparent")
            
        if name == "Dashboard":
            self.show_dashboard()
        elif name == "Manage Students":
            if self.user_role == "Teacher":
                self.show_teacher_students_page()
            else:
                messagebox.showwarning("Access", "Only teachers can manage students.")
        elif name == "View Records":
            if self.user_role == "Teacher":
                self.show_attendance_records()
            else:
                messagebox.showwarning("Access", "Only teachers can view records.")
        elif name == "Mark Attendance" and self.user_role == "Student":
            self.show_student_attendance()
        elif name == "Attendance Record" and self.user_role == "Student":
            self.show_view_attendance()
        elif name == "Logout":
            self.logout()

    # ---------- Attendance counters ----------
    def get_attendance_counts(self, username: str):
        csv_path = _here(CSV_FILENAME)
        if not os.path.exists(csv_path):
            print(f"[Attendance] CSV not found at {csv_path}")
            return 0, TOTAL_CLASSES

        try:
            now = time.time()
            cache = self._attendance_cache.get(username)
            if cache and (now - cache.get("ts", 0.0)) < self._attendance_cache_ttl:
                return cache.get("result", (0, TOTAL_CLASSES))
        except Exception:
            pass

        def norm(v):
            try:
                return str(v).strip().lower()
            except Exception:
                return (v or "").strip().lower()

        target_norm = norm(username)
        target_student_id = (self.student_id or "").strip()

        present_values = {"present", "p", "1", "yes", "true", "y", "present✓", "present✔", "present✅"}

        matched_rows = []
        user_present_dates = set()

        try:
            with open(csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = [h.strip() for h in (reader.fieldnames or [])]
                hdr_l = [h.lower() for h in headers]

                col_user = None
                col_fullname = None
                col_reg = None
                col_date = None
                col_status = None

                for cand in ("username","user","user name","user_name","udid","Username"):
                    if cand.lower() in hdr_l:
                        col_user = headers[hdr_l.index(cand.lower())]
                        break
                for cand in ("fullname","full name","name","FullName","Full Name"):
                    if cand.lower() in hdr_l:
                        col_fullname = headers[hdr_l.index(cand.lower())]
                        break
                for cand in ("registration no","registration_no","reg no","regno","registration","student_id","student id","Registration No"):
                    if cand.lower() in hdr_l:
                        col_reg = headers[hdr_l.index(cand.lower())]
                        break
                for cand in ("date","day","Date","timestamp","Datetime"):
                    if cand.lower() in hdr_l:
                        col_date = headers[hdr_l.index(cand.lower())]
                        break
                for cand in ("status","Status","presence","Presence"):
                    if cand.lower() in hdr_l:
                        col_status = headers[hdr_l.index(cand.lower())]
                        break

                for r in reader:
                    raw_user = (r.get(col_user) or r.get(headers[0]) or "").strip() if col_user or headers else ""
                    raw_fullname = (r.get(col_fullname) or "").strip() if col_fullname else ""
                    raw_reg = (r.get(col_reg) or "").strip() if col_reg else ""
                    raw_date = (r.get(col_date) or "").strip() if col_date else ""
                    raw_status = (r.get(col_status) or "").strip().lower() if col_status else ""

                    matched = False
                    if raw_user and norm(raw_user) == target_norm and target_norm:
                        matched = True
                        match_by = "username"
                    elif raw_fullname and norm(raw_fullname) == target_norm and target_norm:
                        matched = True
                        match_by = "fullname"
                    elif target_student_id and raw_reg and raw_reg == target_student_id:
                        matched = True
                        match_by = "registration"
                    elif raw_user and target_norm and target_norm in norm(raw_user):
                        matched = True
                        match_by = "username_contains"
                    else:
                        match_by = None

                    if matched:
                        matched_rows.append({"raw_user": raw_user, "raw_fullname": raw_fullname, "raw_reg": raw_reg,
                                             "date": raw_date, "status": raw_status, "match_by": match_by})

                        parsed = None
                        try:
                            parsed_dt = _parse_date_str(raw_date)
                            if parsed_dt:
                                parsed = parsed_dt.isoformat()
                        except Exception:
                            parsed = None
                        if not parsed:
                            if raw_date and " " in raw_date:
                                parsed = raw_date.split(" ")[0].strip()
                            else:
                                parsed = raw_date or ""

                        if raw_status in present_values:
                            user_present_dates.add(parsed)

        except Exception as e:
            print("[Attendance] Error reading CSV:", e)
            return 0, TOTAL_CLASSES

        print(f"[Attendance DEBUG] login username='{username}' normalized='{target_norm}' student_id='{target_student_id}'")
        if matched_rows:
            print(f"[Attendance DEBUG] Found {len(matched_rows)} matched CSV row(s). Sample:")
            for i, mr in enumerate(matched_rows[:6]):
                print(f"  #{i+1}: match_by={mr['match_by']} reg='{mr['raw_reg']}' user='{mr['raw_user']}' full='{mr['raw_fullname']}' date='{mr['date']}' status='{mr['status']}'")
        else:
            print("[Attendance DEBUG] No matching CSV rows found for this user.")

        present_count = len([d for d in user_present_dates if d])

        try:
            self._attendance_cache[username] = {"ts": time.time(), "result": (present_count, TOTAL_CLASSES)}
        except Exception:
            pass

        return present_count, TOTAL_CLASSES

    # ---------- small helper to create KPI card used across teacher/student ----------
    def _stat_card_small(self, parent, icon, icon_color, title, value, subtitle=None, sparkline=None):
        card = ctk.CTkFrame(parent, fg_color=self.card_bg, corner_radius=14)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12,6))
        bubble = ctk.CTkFrame(header, fg_color="transparent")
        bubble.pack(side="left")
        try:
            ctk.CTkLabel(bubble, text=icon, font=("Segoe UI Emoji", 20), text_color=icon_color).pack()
        except Exception:
            ctk.CTkLabel(bubble, text=icon, font=("Segoe UI Emoji", 20), text_color=self.white).pack()
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 12, "bold"), text_color=self.text_secondary).pack(side="left", padx=(8,0))
        val_lbl = ctk.CTkLabel(card, text=str(value), font=("Segoe UI", 22, "bold"), text_color=self.white)
        val_lbl.pack(anchor="w", padx=12, pady=(8,6))
        if subtitle:
            ctk.CTkLabel(card, text=subtitle, font=("Segoe UI", 11), text_color=self.text_secondary).pack(anchor="w", padx=12, pady=(0,12))
        if sparkline and isinstance(sparkline, (list,tuple)) and len(sparkline) >= 2:
            cv = tk.Canvas(card, width=88, height=28, bg=self.card_bg, highlightthickness=0)
            cv.pack(anchor="e", padx=12, pady=(6,12))
            data = sparkline
            mn, mx = min(data), max(data)
            rng = mx-mn or 1
            w,h = 88,28; pad=6
            step = (w - pad*2) / (len(data)-1)
            pts = []
            for i,v in enumerate(data):
                x = pad + i*step
                y = h - pad - ((v-mn)/rng) * (h - pad*2)
                pts.extend([x,y])
            if pts:
                cv.create_line(*pts, width=2, fill=icon_color, smooth=True)
        return card

    # ---------- draw circular progress ----------
    def draw_circular_progress(self, canvas: tk.Canvas, pct: float, target: float):
        canvas.delete("all")

    # Get actual canvas size (fallback to 180)
        W = int(canvas.winfo_width() or 180)
        H = int(canvas.winfo_height() or 180)
    
        if W < 80: W = 180
        if H < 80: H = 180

        pad = 12
        r = (W - pad*2) // 2
        cx = W // 2
        cy = H // 2

        track = "#253044"
        good = "#22c55e"
        mid = "#f59e0b"
        bad = "#ef4444"

        pct = max(0.0, min(1.0, float(pct)))
        color = good if pct >= target else (mid if pct >= max(0.0, target - 0.15) else bad)

    # Background arc
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=track, width=18)

    # Progress arc
        extent = -pct * 360
        canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=extent,
                      style=tk.ARC, outline=color, width=18)

    # End dot
        end_ang = 90 - pct*360
        rad = math.radians(end_ang)
        end_x = cx + r * math.cos(rad)
        end_y = cy - r * math.sin(rad)

        canvas.create_oval(end_x-6, end_y-6, end_x+6, end_y+6,
                       fill=color, outline=color)

    # Target marker
        targ_ang = 90 - (target * 360)
        trad = math.radians(targ_ang)
        mark_r = r + 2

        x1 = cx + mark_r * math.cos(trad)
        y1 = cy - mark_r * math.sin(trad)
        x2 = cx + (mark_r - 16) * math.cos(trad)
        y2 = cy - (mark_r - 16) * math.sin(trad)

        canvas.create_line(x1, y1, x2, y2, fill="#94a3b8", width=3)

    # Text
        canvas.create_text(cx, cy-6, text=f"{round(pct*100)}%",
                       fill=self.white, font=("Segoe UI", 24, "bold"))
        canvas.create_text(cx, cy+18, text=f"of {TOTAL_CLASSES} classes",
                       fill=self.text_secondary, font=("Segoe UI", 10))


    # ---------- render teacher bottom panel (created once when dashboard built) ----------
    def _create_teacher_graph_panel(self, parent):
        if self._teacher_graph_panel is not None:
            return
        panel = ctk.CTkFrame(parent, fg_color=self.card_bg, corner_radius=12)
        self._teacher_graph_panel = panel

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10,6))
        self._graph_title_label = ctk.CTkLabel(header, text="", font=("Segoe UI", 14, "bold"), text_color=self.text_primary)
        self._graph_title_label.pack(side="left")

        self._graph_max_btn = ctk.CTkButton(header, text="Maximize", width=100, command=self._toggle_teacher_graph_maximize)
        self._graph_max_btn.pack(side="right", padx=(6,0))

        close_btn = ctk.CTkButton(header, text="Close", width=80, command=self._hide_teacher_graph_panel)
        close_btn.pack(side="right", padx=(6,0))

        outer = tk.Frame(panel, bg=self.card_bg)
        outer.pack(fill="both", expand=True, padx=8, pady=(0,8))

        scroll_canvas = tk.Canvas(outer, bg=self.card_bg, highlightthickness=0)
        scroll_canvas.pack(side="left", fill="both", expand=True)

        v_scroll = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = tk.Scrollbar(panel, orient="horizontal", command=scroll_canvas.xview)
        h_scroll.pack(side="bottom", fill="x")

        scroll_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        inner = tk.Frame(scroll_canvas, bg=self.card_bg)
        self._teacher_graph_inner = inner

        scroll_window = scroll_canvas.create_window((0,0), window=inner, anchor="nw")

        def _on_inner_config(event):
            try:
                scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            except Exception:
                pass

        inner.bind("<Configure>", _on_inner_config)

        def _on_mousewheel(event):
            delta = 0
            if event.num == 5 or event.delta < 0:
                delta = 1
            elif event.num == 4 or event.delta > 0:
                delta = -1
            try:
                scroll_canvas.yview_scroll(delta, "units")
            except Exception:
                pass

        scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        scroll_canvas.bind_all("<Button-4>", _on_mousewheel)
        scroll_canvas.bind_all("<Button-5>", _on_mousewheel)

        self._teacher_graph_scrollcanvas = scroll_canvas

    def _toggle_teacher_graph_maximize(self):
        if self._teacher_graph_panel is None:
            return
        parent_dashboard = self.cached_pages.get("dashboard")
        if parent_dashboard is None:
            return

        if getattr(self, "_teacher_graph_maximized", False):
            try:
                self._teacher_graph_panel.place_forget()
            except Exception:
                pass
            try:
                self._teacher_graph_panel.pack(fill="both", padx=16, pady=(6,16), ipady=8)
            except Exception:
                pass
            self._teacher_graph_maximized = False
            try:
                self._graph_max_btn.configure(text="Maximize")
            except Exception:
                pass
            try:
                self._teacher_graph_scrollcanvas.configure(scrollregion=self._teacher_graph_scrollcanvas.bbox("all"))
            except Exception:
                pass
            return

        try:
            self._teacher_graph_panel.pack_forget()
        except Exception:
            pass
        try:
            self._teacher_graph_panel.place(relx=0.04, rely=0.08, relwidth=0.92, relheight=0.84)
        except Exception:
            try:
                self._teacher_graph_panel.pack(fill="both", padx=16, pady=(6,16), ipady=8)
            except Exception:
                pass
        self._teacher_graph_maximized = True
        try:
            self._graph_max_btn.configure(text="Restore")
        except Exception:
            pass
        try:
            self._teacher_graph_scrollcanvas.configure(scrollregion=self._teacher_graph_scrollcanvas.bbox("all"))
        except Exception:
            pass

    def _show_teacher_graph_panel(self, container_parent):
        if self._teacher_graph_panel is None:
            self._create_teacher_graph_panel(container_parent)
        panel = self._teacher_graph_panel
        if str(panel.winfo_ismapped()) == "1":
            return
        panel.pack(fill="both", padx=16, pady=(6,16), ipady=8)

    def _hide_teacher_graph_panel(self):
        try:
            if self._teacher_graph_canvas:
                try:
                    self._teacher_graph_canvas.get_tk_widget().destroy()
                except Exception:
                    pass
                self._teacher_graph_canvas = None
                self._teacher_graph_fig = None
            if self._teacher_graph_panel:
                try:
                    self._teacher_graph_panel.place_forget()
                except Exception:
                    pass
                try:
                    self._teacher_graph_panel.pack_forget()
                except Exception:
                    pass
            self._teacher_graph_maximized = False
            self._selected_graph_username = None
            self._selected_graph_fullname = None
            if hasattr(self, "_graph_title_label"):
                try: self._graph_title_label.configure(text="")
                except Exception: pass
            if hasattr(self, "_graph_max_btn"):
                try: self._graph_max_btn.configure(text="Maximize")
                except Exception: pass
        except Exception:
            pass

    def _render_student_graph_in_panel(self, username, full_name):
        if matplotlib is None or FigureCanvasTkAgg is None:
            messagebox.showerror("Missing dependency", "Matplotlib is required to show graphs in-panel. Install with:\n\npip install matplotlib")
            return
        dates, daily_present, cum_pct = _attendance_timeseries_for_user(username)
        if not dates:
            messagebox.showinfo("No data", f"No attendance records for '{username}'.")
            return
        parent = self._teacher_graph_panel
        if parent is None:
            return

        if self._teacher_graph_canvas:
            try:
                self._teacher_graph_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self._teacher_graph_canvas = None
            self._teacher_graph_fig = None

        fig = Figure(figsize=(10.8, 4.0), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(dates, daily_present, width=0.6, alpha=0.6, label="Present (daily)")
        ax2 = ax.twinx()
        ax2.plot(dates, cum_pct, marker="o", linewidth=2, label="Cumulative %")
        ax.set_ylim(-0.1, 1.1)
        ax.set_ylabel("Present (0/1)")
        ax2.set_ylabel("Cumulative % of total classes")
        ax.set_title(f"{full_name or username} — Attendance over time")
        try:
            ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            fig.autofmt_xdate(rotation=30)
        except Exception:
            pass
        ax.legend(loc="upper left"); ax2.legend(loc="upper right")

        canvas = FigureCanvasTkAgg(fig, master=self._teacher_graph_inner)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=6, pady=6)

        try:
            self._teacher_graph_scrollcanvas.configure(scrollregion=self._teacher_graph_scrollcanvas.bbox("all"))
        except Exception:
            pass

        self._teacher_graph_fig = fig
        self._teacher_graph_canvas = canvas
        try:
            self._graph_title_label.configure(text=f"Student Graph — {full_name or username}")
        except Exception:
            pass

        self._show_teacher_graph_panel(self.cached_pages.get("dashboard"))

    # ---------- Dashboard page ----------
    def show_dashboard(self):
        if "dashboard" not in self.cached_pages:
            scroll = ScrollableFrame(self.main_frame, fg_color=self.main_bg)
            scroll.place(relx=0, rely=0, relwidth=1, relheight=1)

            frame = scroll.inner 

            # topbar
            topbar = ctk.CTkFrame(frame, fg_color=self.card_bg, height=68)
            topbar.pack(fill="x")
            ctk.CTkLabel(topbar, text="📊 Dashboard Overview", fg_color=self.card_bg, text_color=self.text_primary, font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=14)
            right = ctk.CTkFrame(topbar, fg_color="transparent")
            right.pack(side="right", padx=12, pady=8)
            self._topbar_avatar_canvas = tk.Canvas(right, width=64, height=64, bg=self.card_bg, highlightthickness=0)
            self._topbar_avatar_canvas.pack(side="right", padx=(8,0))
            self._topbar_name_label = ctk.CTkLabel(right, text=self.username or "User", text_color=self.text_primary, font=("Segoe UI", 12, "bold"), fg_color="transparent")
            self._topbar_name_label.pack(side="right", padx=(0,10), pady=(14,0))
            self._redraw_topbar_profile()

            # ⭐ Click avatar or name → Open Profile Page ⭐
# ⭐ Only teachers can open profile page ⭐
            if self.user_role == "Teacher":
                self._topbar_avatar_canvas.bind("<Button-1>", lambda e: self.show_profile_page())
                self._topbar_name_label.bind("<Button-1>", lambda e: self.show_profile_page())
            else:
    # Remove binding so clicking does nothing
                self._topbar_avatar_canvas.unbind("<Button-1>")
                self._topbar_name_label.unbind("<Button-1>")



            # TEACHER: recent activity + last attendance + teacher KPIs
            if self.user_role == "Teacher":
                recent_container = ctk.CTkFrame(frame, fg_color="transparent")
                recent_container.pack(fill="x", padx=16, pady=(12,6))
                recent_container.grid_columnconfigure((0,1), weight=1)
                leftc = ctk.CTkFrame(recent_container, fg_color="transparent"); leftc.grid(row=0,column=0, sticky="nsew", padx=(0,8))
                rightc = ctk.CTkFrame(recent_container, fg_color="transparent"); rightc.grid(row=0,column=1, sticky="nsew", padx=(8,0))
                ctk.CTkLabel(rightc, text="Recent Attendance Activity", font=("Segoe UI", 14, "bold"), text_color=self.text_primary).pack(anchor="w")

                # recent students cards container (4 in a row)
                cards_frame = ctk.CTkFrame(rightc, fg_color="transparent")
                cards_frame.pack(fill="x", expand=False, padx=4, pady=6)
                for col_ix in range(4):
                    cards_frame.grid_columnconfigure(col_ix, weight=1, uniform="recent_cols")

                recent_students = _recent_students_activity(limit_students=4, rows_per_student=3)
                card_target_width = 240

                for idx in range(4):
                    col = idx
                    card = ctk.CTkFrame(cards_frame, fg_color=self.card_bg, corner_radius=12, width=card_target_width)
                    card.grid(row=0, column=col, sticky="nsew", padx=8, pady=6)
                    try:
                        card.grid_propagate(False)
                    except Exception:
                        pass

                    if idx < len(recent_students):
                        entry = recent_students[idx]
                        full = entry.get("full_name") or entry.get("username") or "<unknown>"
                        uname = entry.get("username") or ""
                        activities = entry.get("activities") or []

                        hdr = ctk.CTkFrame(card, fg_color="transparent")
                        hdr.pack(fill="x", padx=8, pady=(8, 4))
                        ctk.CTkLabel(hdr, text=full, font=("Segoe UI", 12, "bold"), text_color=self.text_primary).pack(side="left", anchor="w")
                        ctk.CTkLabel(hdr, text=f"@{uname}", font=("Segoe UI", 10), text_color=self.text_secondary).pack(side="right", anchor="e")

                        sep = tk.Canvas(card, height=1, bg=self.card_bg, highlightthickness=0)
                        sep.pack(fill="x", padx=8, pady=(0, 6))

                        for act in activities:
                            dt = act.get("datetime") or ""
                            st = act.get("status") or ""
                            rowf = ctk.CTkFrame(card, fg_color="transparent")
                            rowf.pack(fill="x", padx=8, pady=4)
                            ctk.CTkLabel(rowf, text=(dt or "—"), font=("Segoe UI", 10), text_color=self.text_secondary).pack(side="left", anchor="w")
                            ctk.CTkLabel(rowf, text=(st or ""), font=("Segoe UI", 10, "bold"), text_color=self.text_primary).pack(side="right", anchor="e")

                        btn_row = ctk.CTkFrame(card, fg_color="transparent")
                        btn_row.pack(fill="x", padx=8, pady=(6, 8))
                        view_btn = ctk.CTkButton(
                            btn_row, text="View Graph", width=110, corner_radius=8,
                            command=lambda u=uname, f=full: self._on_teacher_view_graph_click(u, f)
                        )
                        view_btn.pack(side="right")
                    else:
                        ctk.CTkLabel(card, text="No data", font=("Segoe UI", 12, "bold"), text_color=self.text_secondary).pack(expand=True, pady=28)

                # last attendance label
                last_rows = _last_attendance_rows(limit=1)
                last_time_val = last_rows[0].get("datetime") if last_rows else "N/A"
                footer = ctk.CTkFrame(rightc, fg_color="transparent"); footer.pack(fill="x", padx=6, pady=(6,0))
                ctk.CTkLabel(footer, text=f"Last attendance: {last_time_val}", font=("Segoe UI", 11), text_color=self.text_secondary).pack(anchor="w")

                # teacher KPI row
                stats_wrap = ctk.CTkFrame(frame, fg_color="transparent"); stats_wrap.pack(fill="x", padx=16, pady=(12,18))
                stats_wrap.grid_columnconfigure((0,1,2,3), weight=1)
                total_students = _count_students()
                total_records = _count_attendance_rows()
                present_today, absent_today, present_pct = _today_attendance_stats()
                pct_text = f"{round(present_pct*100)}%"
                def _big_card(parent, emoji, color, title, value):
                    c = ctk.CTkFrame(parent, fg_color=self.card_bg, corner_radius=14)
                    header = ctk.CTkFrame(c, fg_color="transparent"); header.pack(fill="x", pady=(8,4), padx=8)
                    bubble = ctk.CTkFrame(header, fg_color="transparent"); bubble.pack(side="left")
                    try:
                        ctk.CTkLabel(bubble, text=emoji, font=("Segoe UI Emoji", 28), text_color=color).pack()
                    except:
                        ctk.CTkLabel(bubble, text=emoji, font=("Segoe UI Emoji", 28), text_color=self.white).pack()
                    ctk.CTkLabel(header, text=title, font=("Segoe UI", 13, "bold"), text_color=self.text_secondary).pack(side="left", padx=(8,0))
                    val_lbl = ctk.CTkLabel(c, text=str(value), font=("Segoe UI", 18, "bold"), text_color=self.white)
                    val_lbl.pack(anchor="w", padx=8, pady=(6,12))
                    return c, val_lbl
                k1_frame, k1_val = _big_card(stats_wrap, "🎒", "#F59E0B", "Total Students", total_students); k1_frame.grid(row=0,column=0, padx=6, pady=6, sticky="nsew")
                k2_frame, k2_val = _big_card(stats_wrap, "🗂️", "#60A5FA", "Attendance Records", total_records); k2_frame.grid(row=0,column=1, padx=6, pady=6, sticky="nsew")
                k3_frame, k3_val = _big_card(stats_wrap, "📈", "#34D399", "Today's Present %", pct_text); k3_frame.grid(row=0,column=2, padx=6,pady=6, sticky="nsew")
                k4_frame, k4_val = _big_card(stats_wrap, "❌", "#F87171", "Today's Absent", absent_today); k4_frame.grid(row=0,column=3, padx=6,pady=6, sticky="nsew")

                refresh_wrap = ctk.CTkFrame(frame, fg_color="transparent")
                refresh_wrap.pack(fill="x", padx=18, pady=(0,6))
                refresh_wrap.grid_columnconfigure(0, weight=1)
                self._kpi_last_refreshed_label = ctk.CTkLabel(refresh_wrap, text=f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}", font=("Segoe UI", 10), text_color=self.text_secondary, fg_color="transparent")
                self._kpi_last_refreshed_label.pack(anchor="w", padx=(6,0))
            
                # ===================== WARNING PANEL (under red area) =====================
                warning_panel = ctk.CTkFrame(frame, fg_color=self.card_bg, corner_radius=12)
                warning_panel.pack(fill="x", padx=16, pady=(12, 20))

                ctk.CTkLabel(
                    warning_panel,
                    text="⚠ Student Warnings",
                    font=("Segoe UI", 15, "bold"),
                    text_color=self.white
                ).pack(anchor="w", padx=12, pady=(12, 6))
                
# --- Send Warning Button ---
                send_btn = ctk.CTkButton(warning_panel, text="Send Warning", width=150, command=self._open_warning_popup)
                send_btn.pack(anchor="w", padx=12, pady=(0, 12))

# List container
                self.warning_list_container = ctk.CTkFrame(warning_panel, fg_color="transparent")
                self.warning_list_container.pack(fill="x", padx=12, pady=(0, 12))

# Initially load warnings
                self._refresh_warning_list()


                self._teacher_kpi_widgets["total_students"] = k1_val
                self._teacher_kpi_widgets["attendance_records"] = k2_val
                self._teacher_kpi_widgets["present_pct"] = k3_val
                self._teacher_kpi_widgets["absent_today"] = k4_val

                try:
                    self.update_teacher_kpis(schedule_next=True, interval_ms=3000)
                except Exception:
                    pass
                try:
                    self._start_csv_watcher()
                except Exception:
                    pass

                self._create_teacher_graph_panel(frame)

            # STUDENT: Large Attendance Progress card + small KPI cards beneath
            if self.user_role == "Student":

                att_card = ctk.CTkFrame(frame, fg_color=self.card_bg, corner_radius=16)
                att_card.pack(fill="x", padx=16, pady=(12,12))
                att_card.grid_columnconfigure((0,1), weight=1)
                header = ctk.CTkFrame(att_card, fg_color="transparent"); header.pack(fill="x", padx=20, pady=(6,4))
                ctk.CTkLabel(header, text="Attendance Progress", font=("Segoe UI", 18, "bold"), text_color=self.text_primary).pack(side="left")
                ctk.CTkLabel(header, text=f"🎯 Target {int(self.target_attendance*100)}% of {TOTAL_CLASSES}", font=("Segoe UI", 12, "bold"), text_color=self.text_secondary).pack(side="right")

                container = ctk.CTkFrame(att_card, fg_color=self.card_bg); container.pack(fill="x", padx=18, pady=(4,8))
                container.grid_columnconfigure((0,1), weight=1)

                self.progress_canvas = tk.Canvas(container, width=220, height=220, bg=self.card_bg, highlightthickness=0)
                self.progress_canvas.grid(row=0, column=0, sticky="w", padx=(6,24), pady=6)

                right_area = ctk.CTkFrame(container, fg_color="transparent")
                right_area.grid(row=0, column=1, sticky="nsew", padx=(6,24))
                self.title_label = ctk.CTkLabel(right_area, text="Your currently standing", font=("Segoe UI", 16, "bold"), text_color=self.text_primary)
                self.title_label.pack(anchor="nw", pady=(10,8))
                self.subtitle_label = ctk.CTkLabel(right_area, text="", font=("Segoe UI", 12), text_color=self.text_secondary)
                self.subtitle_label.pack(anchor="nw", pady=(0,8))

                stats_row = ctk.CTkFrame(att_card, fg_color="transparent")
                stats_row.pack(fill="x", padx=28, pady=(4,6))
                stats_row.grid_columnconfigure((0,1,2), weight=1)
                self.stat_present = self._inline_stat_cell(stats_row, "Present (Unique Days)", "0", col=0)
                self.stat_total = self._inline_stat_cell(stats_row, "Total Classes", str(TOTAL_CLASSES), col=1)
                self.stat_needed = self._inline_stat_cell(stats_row, "Needed to Hit Target", "0", col=2)

                kpi_wrap = ctk.CTkFrame(frame, fg_color="transparent")
                kpi_wrap.pack(fill="x", padx=16, pady=(6,6))
                kpi_wrap.grid_columnconfigure((0,1,2,3), weight=1)

                present_count, total = self.get_attendance_counts(self.username)
                absent_derived = max(0, total - present_count)
                pct = (present_count / total) if total else 0.0
                pct_txt = f"{round(pct*100)}%"

                dates, daily_present, cum_pct = _attendance_timeseries_for_user(self.username)
                recent_trend = (cum_pct[-6:] if cum_pct else [round(pct*100)]*6) if cum_pct else [round(pct*100)]*6

                c1 = self._stat_card_small(kpi_wrap, "🏫", "#64748b", "Total Classes", total, subtitle="Term target baseline")
                c1.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

                c2 = self._stat_card_small(kpi_wrap, "🙋🏻‍♂️", "#10B981", "Present (Unique Days)", present_count, subtitle="Unique dates marked present", sparkline=recent_trend)
                c2.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

                c3 = self._stat_card_small(kpi_wrap, "❗", "#F59E0B", "Absent (Derived)", absent_derived, subtitle="Based on fixed total classes")
                c3.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)

                c4 = self._stat_card_small(kpi_wrap, "🎯", "#6366F1", "Progress to Target", pct_txt, subtitle=f"Need {max(0, int(self.target_attendance*TOTAL_CLASSES + 0.9999) - present_count)} more to hit {int(self.target_attendance*100)}%")
                c4.grid(row=0, column=3, sticky="nsew", padx=8, pady=8)



# ==========================================
#     ⚠ STUDENT WARNING BOX (ADD HERE)
# ==========================================
                warnings_data = self._load_warnings()
                user_warnings = warnings_data.get(self.username, [])

                warn_frame = ctk.CTkFrame(frame, fg_color=self.card_bg, corner_radius=16)
                warn_frame.pack(fill="x", padx=16, pady=(6, 20))

                ctk.CTkLabel(
                    warn_frame,
                    text="⚠ Warnings From Teacher",
                    font=("Segoe UI", 16, "bold"),
                    text_color=self.white
                ).pack(anchor="w", padx=16, pady=(10, 6))

                if not user_warnings:
                    ctk.CTkLabel(
                        warn_frame,
                        text="No warnings 😊",
                        font=("Segoe UI", 13),
                        text_color=self.text_secondary
                    ).pack(anchor="w", padx=16, pady=(4, 10))
                else:
                    for item in user_warnings:
                        teacher_username = item.get("from", "teacher1")
                        teacher_display = self._get_teacher_display_name(teacher_username)

                        row = ctk.CTkFrame(warn_frame, fg_color="#111827", corner_radius=10)
                        row.pack(fill="x", padx=12, pady=6)

                    ctk.CTkLabel(
                        row,
                        text=f"⚠ Warning From {teacher_display}",
                        font=("Segoe UI", 13, "bold"),
                        text_color="#fbbf24"
                    ).pack(anchor="w", padx=10, pady=(2, 0))


                    

                    ctk.CTkLabel(
                        row,
                        text=item.get("message", ""),
                        font=("Segoe UI", 12),
                        text_color=self.white
                    ).pack(anchor="w", padx=10, pady=(0, 0))

                    ctk.CTkLabel(
                        row,
                        text=item.get("time", ""),
                        font=("Segoe UI", 10),
                        text_color=self.text_secondary
                    ).pack(anchor="e", padx=12, pady=(0, 2))



# (KEEP THESE LINES AFTER WARNING BOX)
                self.cached_pages["dashboard"] = frame
                frame.lower()

        else:
            try:
                self._redraw_topbar_profile()
            except Exception:
                pass

        if self.user_role == "Student":
            self.update_attendance_progress()
        self._show_page("dashboard")
# ==================== WARNING SYSTEM STORAGE ====================
    def _warnings_path(self):
        return _here("warnings.json")

    def _load_warnings(self):
        """Load warning messages from warnings.json"""
        path = self._warnings_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except:
            return {}

    def _save_warnings(self, data):
        """Save warnings to warnings.json"""
        path = self._warnings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except:
            pass

    def _refresh_warning_list(self):
        for w in self.warning_list_container.winfo_children():
            w.destroy()

        warnings_data = self._load_warnings() or {}

        students = _read_students_json()

        for user, warns in warnings_data.items():
            if not warns:
                continue

        # get full name of this user
            full_name = next((s.get("full_name") for s in students if s.get("username") == user), user)

            for item in warns:
                row = ctk.CTkFrame(self.warning_list_container, fg_color="#111827", corner_radius=8)
                row.pack(fill="x", padx=4, pady=4)

                ctk.CTkLabel(
                    row,
                    text=full_name,
                    text_color="#60a5fa",
                    font=("Segoe UI", 12, "bold")
                ).pack(side="left", padx=8)

                ctk.CTkLabel(
                    row,
                    text=item.get("message", ""),
                    text_color=self.white,
                    font=("Segoe UI", 12)
                ).pack(side="left", padx=8)

                ctk.CTkLabel(
                    row,
                    text=item.get("time", ""),
                    text_color="#a1a1aa",
                    font=("Segoe UI", 10)
                ).pack(side="right", padx=8)
    def _get_teacher_display_name(self, username):
        """
        Returns formatted teacher name, e.g.:
        Mr. Rahul Sir
        Ms. Ahana Ma’am
        """
        try:
            profiles = _load_profiles()
            teacher = profiles.get(username, {})
        except:
            teacher = {}

        full = teacher.get("full_name", username)
        gender = teacher.get("gender", "male").lower()

        if gender == "female":
            title = "Ms."
            suffix = "Ma’am"
        else:
            title = "Mr."
            suffix = "Sir"

        return f"{title} {full} {suffix}"

    def _open_warning_popup(self):

    # Close old panel if exists
        try:
            self.warning_panel.destroy()
        except:
            pass

    # Create warning panel inside the dashboard (NOT new window)
        self.warning_panel = ctk.CTkFrame(self.main_frame, fg_color="#0e1117", corner_radius=14)
        self.warning_panel.place(relx=0.5, rely=0.5, anchor="center")

    # Title
        ctk.CTkLabel(
            self.warning_panel,
            text="Send Warning",
            font=("Segoe UI", 18, "bold"),
            text_color="white"
        ).pack(pady=(10, 5))

    # ---------- Select Student ----------
        ctk.CTkLabel(
            self.warning_panel,
            text="Select Student:",
            text_color="white",
            font=("Segoe UI", 13)
        ).pack(pady=(10, 5))

        students = _read_students_json()

    # Display FULL NAME, but keep username inside parentheses
        student_display = [
            f"{s.get('full_name')} ({s.get('username')})"
            for s in students
        ]

        selected_student = ctk.StringVar()

        dropdown = ctk.CTkOptionMenu(
            self.warning_panel,
            values=student_display,
            variable=selected_student,
            width=250
        )
        dropdown.pack(pady=5)

    # ---------- Message ----------
        ctk.CTkLabel(
            self.warning_panel,
            text="Warning Message:",
            text_color="white",
            font=("Segoe UI", 13)
        ).pack(pady=(10, 5))

        msg_box = ctk.CTkTextbox(self.warning_panel, width=300, height=110)
        msg_box.pack(pady=5)

    # ---------- Submit ----------
        def submit_warning():
            selected = selected_student.get()
            message = msg_box.get("0.0", "end").strip()

            if "(" not in selected:
                messagebox.showerror("Error", "Please select a student.")
                return

        # Extract username from the dropdown value
            username = selected.split("(")[-1].replace(")", "").strip()

            if not message:
                messagebox.showerror("Error", "Enter a message!")
                return

            warnings = self._load_warnings()

            if username not in warnings:
                warnings[username] = []

            warnings[username].append({
                "message": message,
                "from": self.username,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            self._save_warnings(warnings)

        # Close panel
            self.warning_panel.destroy()
            self._refresh_warning_list()

        ctk.CTkButton(
            self.warning_panel,
            text="Send Warning",
            width=200,
            command=submit_warning
        ).pack(pady=(10, 5))

    # ---------- Close Button ----------
        ctk.CTkButton(
            self.warning_panel,
            text="Close",
            fg_color="#333333",
            hover_color="#444444",
            width=150,
            command=lambda: self.warning_panel.destroy()
        ).pack(pady=(0, 12))


    def _on_teacher_view_graph_click(self, username, full_name):
        if matplotlib is None or FigureCanvasTkAgg is None:
            messagebox.showerror("Missing dependency", "Matplotlib is required to show graphs in-panel. Install with:\n\npip install matplotlib")
            return
        dashboard_frame = self.cached_pages.get("dashboard")
        if dashboard_frame is None:
            self._show_student_graph_in_popup(username, full_name)
            return
        if self._teacher_graph_panel is None:
            self._create_teacher_graph_panel(dashboard_frame)
        self._render_student_graph_in_panel(username, full_name)

    def _show_student_graph_in_popup(self, username, full_name):
        if matplotlib is None or FigureCanvasTkAgg is None:
            messagebox.showerror("Missing dependency", "Matplotlib is required to show graphs. Install with:\n\npip install matplotlib")
            return
        dates, daily_present, cum_pct = _attendance_timeseries_for_user(username)
        if not dates:
            messagebox.showinfo("No data", f"No attendance records for '{username}'.")
            return
        top = tk.Toplevel(self.root)
        top.title(f"Attendance Graph — {full_name or username}")
        top.geometry("900x420")
        fig = Figure(figsize=(9, 4.0), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(dates, daily_present, width=0.6, alpha=0.6, label="Present (daily)")
        ax2 = ax.twinx()
        ax2.plot(dates, cum_pct, marker="o", linewidth=2, label="Cumulative %")
        ax.set_ylim(-0.1, 1.1)
        ax.set_ylabel("Present (0/1)")
        ax2.set_ylabel("Cumulative % of total classes")
        ax.set_title(f"{full_name or username} — Attendance over time")
        try:
            ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            fig.autofmt_xdate(rotation=30)
        except Exception:
            pass
        ax.legend(loc="upper left"); ax2.legend(loc="upper right")
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _inline_stat_cell(self, parent, label, value, col=0):
        cell = ctk.CTkFrame(parent, fg_color=self.card_bg)
        cell.grid(row=0, column=col, sticky="nsew", padx=8)
        ctk.CTkLabel(cell, text=label, text_color=self.text_secondary, font=("Segoe UI", 12, "bold")).pack(anchor="center", pady=(6,4))
        v = ctk.CTkLabel(cell, text=value, text_color=self.white, font=("Segoe UI", 20, "bold"))
        v.pack(anchor="center", pady=(2,12))
        return v

    def _show_page(self, key):
        for name, page_obj in self.cached_pages.items():
            container = getattr(page_obj, "frame", page_obj)
            if name == key:
                container.lift()
            else:
                container.lower()

    def update_attendance_progress(self):
        if self.user_role != "Student":
            return
        present, total = self.get_attendance_counts(self.username)
        pct = (present / total) if total else 0.0
        pct = max(0.0, min(1.0, pct))
        try:
            if hasattr(self, "progress_canvas"):
                self.draw_circular_progress(self.progress_canvas, pct, self.target_attendance)
        except Exception as e:
            print("Progress drawing error:", e)

    # --- calculate needed classes ---
    # TOTAL_CLASSES must exist globally or in class
        target_needed = int((self.target_attendance * TOTAL_CLASSES) + 0.9999)
        needed = max(0, target_needed - present)

        subtitle_text = (
            f"Need {needed} more class{'es' if needed != 1 else ''} "
            f"to reach {int(self.target_attendance * 100)}%."
        )

    # --- update subtitle label ---
        if hasattr(self, "subtitle_label"):
            try:
                self.subtitle_label.configure(text=subtitle_text)
            except Exception:
                pass

    # --- update stat cards ---
        try:
            if hasattr(self, "stat_present"):
                self.stat_present.configure(text=str(present))

            if hasattr(self, "stat_total"):
                self.stat_total.configure(text=str(TOTAL_CLASSES))

            if hasattr(self, "stat_needed"):
                self.stat_needed.configure(text=str(needed))

        except Exception:
            pass
    # Teacher KPI periodic updater (auto-refresh)
    def update_teacher_kpis(self, schedule_next=True, interval_ms=3000, show_toast=False):
        if self.user_role != "Teacher":
            return

        total_students = _count_students()
        total_records = _count_attendance_rows()
        present_today, absent_today, present_pct = _today_attendance_stats()
        pct_text = f"{round(present_pct*100)}%"

        try:
            w = self._teacher_kpi_widgets
            if "total_students" in w:
                w["total_students"].configure(text=str(total_students))
            if "attendance_records" in w:
                w["attendance_records"].configure(text=str(total_records))
            if "present_pct" in w:
                w["present_pct"].configure(text=pct_text)
            if "absent_today" in w:
                w["absent_today"].configure(text=str(absent_today))
            try:
                if self._kpi_last_refreshed_label:
                    self._kpi_last_refreshed_label.configure(text=f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
            except Exception:
                pass
            if show_toast:
                self._show_kpi_toast("KPIs refreshed")
        except Exception:
            pass

        try:
            if self._teacher_kpi_job:
                self.root.after_cancel(self._teacher_kpi_job)
                self._teacher_kpi_job = None
        except Exception:
            pass

        if schedule_next:
            try:
                self._teacher_kpi_job = self.root.after(interval_ms, lambda: self.update_teacher_kpis(True, interval_ms))
            except Exception:
                self._teacher_kpi_job = None

    def _show_kpi_toast(self, text, duration_ms=1300):
        try:
            if getattr(self, "_kpi_toast_label", None):
                try:
                    self._kpi_toast_label.destroy()
                except Exception:
                    pass
                self._kpi_toast_label = None
            top_frame = self.cached_pages.get("dashboard")
            if not top_frame:
                return
            toast = ctk.CTkLabel(top_frame, text=text, font=("Segoe UI", 10), text_color=self.text_primary, fg_color="#065f46", corner_radius=8)
            toast.place(relx=0.82, rely=0.02)
            self._kpi_toast_label = toast
            try:
                if self._kpi_toast_job:
                    self.root.after_cancel(self._kpi_toast_job)
                    self._kpi_toast_job = None
            except Exception:
                pass
            self._kpi_toast_job = self.root.after(duration_ms, lambda: self._destroy_kpi_toast())
        except Exception:
            pass

    def _destroy_kpi_toast(self):
        try:
            if getattr(self, "_kpi_toast_label", None):
                try:
                    self._kpi_toast_label.destroy()
                except Exception:
                    pass
                self._kpi_toast_label = None
            if getattr(self, "_kpi_toast_job", None):
                try:
                    self.root.after_cancel(self._kpi_toast_job)
                except Exception:
                    pass
                self._kpi_toast_job = None
        except Exception:
            pass

    def _check_csv_mtime(self):
        try:
            csv_path = _here(CSV_FILENAME)
            if not os.path.exists(csv_path):
                self._csv_mtime = None
            else:
                try:
                    m = os.path.getmtime(csv_path)
                except Exception:
                    m = None
                if self._csv_mtime is None:
                    self._csv_mtime = m
                else:
                    if m and self._csv_mtime != m:
                        self._csv_mtime = m
                        try:
                            self.update_teacher_kpis(schedule_next=False, show_toast=True)
                        except Exception:
                            pass
            try:
                self._csv_watcher_job = self.root.after(self._csv_watcher_interval_ms, self._check_csv_mtime)
            except Exception:
                self._csv_watcher_job = None
        except Exception:
            try:
                self._csv_watcher_job = self.root.after(self._csv_watcher_interval_ms, self._check_csv_mtime)
            except Exception:
                self._csv_watcher_job = None

    def _start_csv_watcher(self):
        try:
            if self.user_role == "Teacher" and getattr(self, "_csv_watcher_job", None) is None:
                try:
                    csv_path = _here(CSV_FILENAME)
                    self._csv_mtime = os.path.getmtime(csv_path) if os.path.exists(csv_path) else None
                except Exception:
                    self._csv_mtime = None
                self._csv_watcher_job = self.root.after(self._csv_watcher_interval_ms, self._check_csv_mtime)
        except Exception:
            pass

    # Optional idempotent encodings loader
    def load_encodings_once(self):
        if getattr(self, "_encodings_loaded", False):
            return self.encodings

        with self._encodings_lock:
            if getattr(self, "_encodings_loaded", False):
                return self.encodings

            try:
                self.encodings = getattr(self, "encodings", None)
            except Exception:
                self.encodings = getattr(self, "encodings", None)
            finally:
                self._encodings_loaded = True

        return self.encodings

    # Teacher / Manage Students pages
    def show_teacher_students_page(self):
        if "teacher_students" not in self.cached_pages:
            frame = ctk.CTkFrame(self.main_frame, fg_color=self.main_bg)
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            ctk.CTkLabel(frame, text="Student Management (Teacher View)", font=("Segoe UI", 24, "bold"), text_color=self.text_primary).pack(pady=18)
            try:
                ManageStudentsTabs(frame, on_students_changed=self.refresh_all_views)
            except Exception:
                try:
                    AddStudentPage(frame)
                except Exception:
                    pass
            self.cached_pages["teacher_students"] = frame
            frame.lower()
        self._show_page("teacher_students")

    # ---------- NEW: Attendance Records page (teacher) ----------
    def show_attendance_records(self):
        """
        Teacher-only: show a page with a table of attendance CSV rows.
        Starts empty; teacher must search by Name or Registration to populate.
        """
        if self.user_role != "Teacher":
            messagebox.showwarning("Access Denied", "Only teachers can view attendance records.")
            return

        if "attendance_records" not in self.cached_pages:
            frame = ctk.CTkFrame(self.main_frame, fg_color=self.main_bg)
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

            # topbar area
            topbar = ctk.CTkFrame(frame, fg_color=self.card_bg, height=68)
            topbar.pack(fill="x")
            ctk.CTkLabel(topbar, text="🗂 Attendance Records", fg_color=self.card_bg, text_color=self.text_primary, font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=14)
            right = ctk.CTkFrame(topbar, fg_color="transparent")
            right.pack(side="right", padx=12, pady=8)
            self._topbar_avatar_canvas = tk.Canvas(right, width=64, height=64, bg=self.card_bg, highlightthickness=0)
            self._topbar_avatar_canvas.pack(side="right", padx=(8,0))
            self._topbar_name_label = ctk.CTkLabel(right, text=self.username or "User", text_color=self.text_primary, font=("Segoe UI", 12, "bold"), fg_color="transparent")
            self._topbar_name_label.pack(side="right", padx=(0,10), pady=(14,0))
            self._redraw_topbar_profile()

            # Controls: search by name / registration + search & clear
            ctrl_row = ctk.CTkFrame(frame, fg_color="transparent")
            ctrl_row.pack(fill="x", padx=18, pady=(12,6))
            left_ctrl = ctk.CTkFrame(ctrl_row, fg_color="transparent")
            left_ctrl.pack(side="left", anchor="w")

            ctk.CTkLabel(left_ctrl, text="Search Name:", font=("Segoe UI", 11), text_color=self.text_secondary, fg_color="transparent").pack(side="left", padx=(0,8))
            name_entry = ctk.CTkEntry(left_ctrl, placeholder_text="Enter student name (partial allowed)", width=300)
            name_entry.pack(side="left", padx=(0,12))

            ctk.CTkLabel(left_ctrl, text="Registration No:", font=("Segoe UI", 11), text_color=self.text_secondary, fg_color="transparent").pack(side="left", padx=(0,8))
            reg_entry = ctk.CTkEntry(left_ctrl, placeholder_text="Enter reg. no", width=180)
            reg_entry.pack(side="left", padx=(0,12))

            # search / clear buttons on right
            right_ctrl = ctk.CTkFrame(ctrl_row, fg_color="transparent")
            right_ctrl.pack(side="right", anchor="e")
            search_btn = ctk.CTkButton(right_ctrl, text="Search", width=100)
            clear_btn = ctk.CTkButton(right_ctrl, text="Clear", width=100)

            search_btn.pack(side="right", padx=(6,0))
            clear_btn.pack(side="right", padx=(6,0))

            # Treeview container
            tree_wrap = tk.Frame(frame, bg=self.main_bg)
            tree_wrap.pack(fill="both", expand=True, padx=16, pady=6)

            cols = ("date", "time", "username", "fullname", "regno", "status")
            tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", style="Solid.Treeview")
            tree.heading("date", text="Date")
            tree.heading("time", text="Time")
            tree.heading("username", text="Username")
            tree.heading("fullname", text="Full Name")
            tree.heading("regno", text="Reg/ID")
            tree.heading("status", text="Status")
            tree.column("date", width=120, anchor="w")
            tree.column("time", width=100, anchor="w")
            tree.column("username", width=140, anchor="w")
            tree.column("fullname", width=220, anchor="w")
            tree.column("regno", width=120, anchor="w")
            tree.column("status", width=100, anchor="w")
            tree.pack(side="left", fill="both", expand=True)

            vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
            vsb.pack(side="right", fill="y")
            tree.configure(yscrollcommand=vsb.set)

            # behavior: start empty; populate only after search
            def _do_search():
                q_name = (name_entry.get() or "").strip()
                q_reg = (reg_entry.get() or "").strip()
                # if both empty, don't populate (keep empty)
                if not q_name and not q_reg:
                    messagebox.showinfo("Search", "Enter Name and/or Registration to search.")
                    return
                self._populate_attendance_tree_filtered(tree, q_name, q_reg)

            def _do_clear():
                # clear inputs and empty tree
                name_entry.delete(0, "end")
                reg_entry.delete(0, "end")
                for r in tree.get_children():
                    tree.delete(r)

            search_btn.configure(command=_do_search)
            clear_btn.configure(command=_do_clear)

            # store references for later (optional)
            frame._att_tree = tree
            frame._att_name_entry = name_entry
            frame._att_reg_entry = reg_entry

            self.cached_pages["attendance_records"] = frame
            frame.lower()

        # show the page
        self._show_page("attendance_records")

    def _populate_attendance_tree(self, treeview):
        # Legacy helper (full populate) - used elsewhere if needed
        for r in treeview.get_children():
            treeview.delete(r)

        path = _here(CSV_FILENAME)
        if not os.path.exists(path):
            return

        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = [h.strip() for h in (reader.fieldnames or [])]
                lower = [h.lower() for h in fieldnames]
                for row in reader:
                    raw_date = ""
                    raw_time = ""
                    # pick date/time
                    for cand in ("date","day","timestamp"):
                        if cand in lower:
                            raw_date = row.get(fieldnames[lower.index(cand)], "") or ""
                            break
                    for cand in ("time","timestamp"):
                        if cand in lower:
                            raw_time = row.get(fieldnames[lower.index(cand)], "") or ""
                            break
                    # fallback split timestamp
                    if raw_date and not raw_time and isinstance(raw_date, str) and " " in raw_date:
                        parts = raw_date.split(" ")
                        raw_date = parts[0]
                        raw_time = parts[1] if len(parts) > 1 else ""
                    raw_user = ""
                    raw_full = ""
                    raw_status = ""
                    raw_reg = ""
                    # find user/full/reg/status columns
                    for cand in ("username","user","user name","user_name","Username","User"):
                        if cand in row and row.get(cand):
                            raw_user = str(row.get(cand)).strip()
                            break
                    for cand in ("fullname","full name","name","FullName"):
                        if cand in row and row.get(cand):
                            raw_full = str(row.get(cand)).strip()
                            break
                    for cand in ("registration","registration no","regno","reg no","student_id","student id","Registration No"):
                        if cand in row and row.get(cand):
                            raw_reg = str(row.get(cand)).strip()
                            break
                    for cand in ("status","presence","Status","Presence"):
                        if cand in row and row.get(cand):
                            raw_status = str(row.get(cand)).strip()
                            break
                    if not raw_user:
                        for v in row.values():
                            if v and str(v).strip():
                                raw_user = str(v).strip()
                                break
                    treeview.insert("", "end", values=(raw_date, raw_time, raw_user, raw_full, raw_reg, raw_status))
        except Exception as e:
            print("[Records] Failed populating attendance tree:", e)

    def _populate_attendance_tree_filtered(self, treeview, name_query: str, reg_query: str):
        """
        Populate tree only with rows matching name_query (substring, case-insensitive)
        or reg_query (substring, exact-ish). If both provided, match either column (OR).
        """
        # clear tree first
        for r in treeview.get_children():
            treeview.delete(r)

        path = _here(CSV_FILENAME)
        if not os.path.exists(path):
            return

        qn = (name_query or "").strip().lower()
        qr = (reg_query or "").strip().lower()

        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = [h.strip() for h in (reader.fieldnames or [])]
                lower = [h.lower() for h in fieldnames]

                # heuristics: identify candidate column names
                date_col = None; time_col = None; user_col = None; full_col = None; reg_col = None; status_col = None
                for cand in ("date","day","timestamp"):
                    if cand in lower:
                        date_col = fieldnames[lower.index(cand)]
                        break
                for cand in ("time","timestamp"):
                    if cand in lower:
                        time_col = fieldnames[lower.index(cand)]
                        break
                for cand in ("username","user","user name","user_name","Username","User"):
                    if cand in lower and user_col is None:
                        user_col = fieldnames[lower.index(cand)]
                for cand in ("fullname","full name","name","FullName"):
                    if cand in lower:
                        full_col = fieldnames[lower.index(cand)]
                        break
                for cand in ("registration","registration no","regno","reg no","student_id","student id","Registration No"):
                    if cand in lower:
                        reg_col = fieldnames[lower.index(cand)]
                        break
                for cand in ("status","presence","Status","Presence"):
                    if cand in lower:
                        status_col = fieldnames[lower.index(cand)]
                        break

                for row in reader:
                    raw_date = (row.get(date_col) or "") if date_col else ""
                    raw_time = (row.get(time_col) or "") if time_col else ""
                    # fallback splitting
                    if raw_date and not raw_time and isinstance(raw_date, str) and " " in raw_date:
                        parts = raw_date.split(" ")
                        raw_date = parts[0]; raw_time = parts[1] if len(parts) > 1 else ""
                    raw_user = (row.get(user_col) or "").strip() if user_col else ""
                    raw_full = (row.get(full_col) or "").strip() if full_col else ""
                    raw_reg = (row.get(reg_col) or "").strip() if reg_col else ""
                    raw_status = (row.get(status_col) or "").strip() if status_col else ""

                    # fallback attempts to pull values if heuristics didn't find columns
                    if not raw_user:
                        for key in row:
                            val = row.get(key)
                            if val and str(val).strip():
                                raw_user = str(val).strip()
                                break
                    if not raw_full:
                        # try to find something that looks like a full name (two words)
                        for key in row:
                            val = row.get(key)
                            if val and isinstance(val, str) and len(val.split()) >= 2:
                                raw_full = val.strip()
                                break

                    norm_user = (raw_user or "").lower()
                    norm_full = (raw_full or "").lower()
                    norm_reg = (raw_reg or "").lower()

                    matches = False
                    if qn:
                        if qn in norm_full or qn in norm_user:
                            matches = True
                    if qr:
                        if qr in norm_reg or qr in norm_user:
                            matches = True

                    if matches:
                        treeview.insert("", "end", values=(raw_date, raw_time, raw_user, raw_full, raw_reg, raw_status))
        except Exception as e:
            print("[Records] Filtered populate failed:", e)

    def show_student_attendance(self):
        refresh_callback = None
        if "view_attendance" in self.cached_pages:
            view_page = self.cached_pages["view_attendance"]
            if hasattr(view_page, "load_attendance"):
                refresh_callback = view_page.load_attendance
        if "mark_attendance" not in self.cached_pages:
            page = MarkAttendancePage(self.main_frame, student_username=self.username, refresh_callback=refresh_callback)
            container = getattr(page, "frame", page)
            container.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.cached_pages["mark_attendance"] = page
            container.lower()
        self._show_page("mark_attendance")

    def show_view_attendance(self):
        from view_attendance import ViewAttendancePage
        if "view_attendance" not in self.cached_pages:
            page = ViewAttendancePage(self.main_frame, self.username)
            container = getattr(page, "frame", page)
            container.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.cached_pages["view_attendance"] = page
            container.lower()
        self._show_page("view_attendance")

    def refresh_all_views(self):
        try:
            self._redraw_topbar_profile()
        except Exception:
            pass
        if "view_attendance" in self.cached_pages:
            view_page = self.cached_pages["view_attendance"]
            if hasattr(view_page, "load_attendance"):
                try:
                    view_page.load_attendance()
                except Exception:
                    pass
        if "dashboard" in self.cached_pages and self.user_role == "Student":
            try:
                self.update_attendance_progress()
            except Exception:
                pass

        try:
            if self.user_role == "Teacher" and "dashboard" in self.cached_pages:
                self.update_teacher_kpis(schedule_next=True)
        except Exception:
            pass

    def logout(self):
        from User_Authentication import User_Authentication
        self.clear_root()
        self._init_ttk_theme_once(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        User_Authentication(self.root)

    def clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()


    def show_profile_page(self):
        """Open a beautiful modern Teacher Profile Page."""
        if "profile_page" not in self.cached_pages:

# ----- Scrollable Profile Page -----
            canvas = tk.Canvas(self.main_frame, bg=self.main_bg, highlightthickness=0)
            scroll_y = tk.Scrollbar(self.main_frame, orient="vertical", command=canvas.yview)
            frame = ctk.CTkFrame(canvas, fg_color=self.main_bg)

            canvas.create_window((0,0), window=frame, anchor="nw")
            canvas.configure(yscrollcommand=scroll_y.set)

            canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
            scroll_y.place(relx=0.98, rely=0, relheight=1)

            def _on_frame_config(event):
                canvas.configure(scrollregion=canvas.bbox("all"))

            frame.bind("<Configure>", _on_frame_config)


            # ================= HEADER ==================
            header = ctk.CTkFrame(frame, fg_color=self.card_bg, height=80, corner_radius=16)
            header.pack(fill="x", padx=20, pady=(15, 5))

            ctk.CTkLabel(
                header,
                text="👨‍🏫 Teacher Profile",
                font=("Segoe UI", 24, "bold"),
                text_color=self.white
            ).pack(anchor="w", padx=25, pady=20)

            # Load Data
            profiles = _load_profiles()
            teacher = profiles.get(self.login_username, {})
            full = teacher.get("full_name", self.username)
            email = teacher.get("email", "")
            mobile = teacher.get("mobile", "")
            gender = teacher.get("gender", "Male")

            # =============== MAIN CARD ================
            card = ctk.CTkFrame(frame, fg_color="#1c2430", corner_radius=20)
            card.pack(padx=30, pady=20, fill="x")

            # -------------- Avatar Section --------------
            avatar_section = ctk.CTkFrame(card, fg_color="transparent")
            avatar_section.pack(pady=20)

            avatar_canvas = tk.Canvas(
                avatar_section,
                width=140, height=140,
                bg="#1c2430",
                highlightthickness=0
            )
            avatar_canvas.pack()

            img_path = _guess_profile_image_path(self.username)
            self._profile_preview_img = None

            def update_avatar(path):
                avatar_canvas.delete("all")
                avatar_canvas.create_oval(5, 5, 135, 135, fill="#2d3748", outline="")

                if path and Image:
                    try:
                        im = Image.open(path).convert("RGBA")
                        w, h = im.size
                        side = min(w, h)
                        im = im.crop(((w-side)//2, (h-side)//2,
                                      (w+side)//2, (h+side)//2))
                        im = im.resize((130, 130))
                        self._profile_preview_img = ImageTk.PhotoImage(im)
                        avatar_canvas.create_image(70, 70, image=self._profile_preview_img)
                        return
                    except:
                        pass

                initials = self._user_initials(full)
                avatar_canvas.create_text(
                    70, 70, text=initials,
                    fill="white", font=("Segoe UI", 40, "bold")
                )

            update_avatar(img_path)

            # Upload/Remove Buttons
            btnrow = ctk.CTkFrame(card, fg_color="transparent")
            btnrow.pack(pady=(5, 20))

            def upload_photo():
                import tkinter.filedialog as fd
                path = fd.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
                if not path:
                    return

                folder = _here("profile_images")
                os.makedirs(folder, exist_ok=True)
                ext = os.path.splitext(path)[1]
                target = os.path.join(folder, f"{self.username}{ext}")

                try:
                    import shutil
                    shutil.copy(path, target)
                    update_avatar(target)
                except:
                    messagebox.showerror("Error", "Failed to upload image")

            def remove_photo():
                folder = _here("profile_images")
                found = False
                for ext in ("png", "jpg", "jpeg"):
                    f = os.path.join(folder, f"{self.username}.{ext}")
                    if os.path.exists(f):
                        os.remove(f)
                        found = True
                update_avatar(None)
                if not found:
                    messagebox.showinfo("Info", "No profile photo found")

            ctk.CTkButton(btnrow, text="Upload Photo", corner_radius=12,
                          fg_color="#4b6cb7", hover_color="#3e5aa1",
                          command=upload_photo).pack(side="left", padx=8)

            ctk.CTkButton(btnrow, text="Remove", corner_radius=12,
                          fg_color="#444", hover_color="#333",
                          command=remove_photo).pack(side="left", padx=8)

            # ================= FORM FIELDS ==================
            form = ctk.CTkFrame(card, fg_color="transparent")
            form.pack(fill="x", padx=30, pady=10)

            def label(t):
                return ctk.CTkLabel(form, text=t, text_color=self.text_secondary,
                                    font=("Segoe UI", 13, "bold"))

            # Full Name
            label("Full Name").pack(anchor="w", pady=(10, 1))
            full_entry = ctk.CTkEntry(form, placeholder_text="Enter full name", width=400)
            full_entry.insert(0, full)
            full_entry.pack(pady=5)

            # Email
            label("Email").pack(anchor="w", pady=(10, 1))
            email_entry = ctk.CTkEntry(form, placeholder_text="Enter email", width=400)
            email_entry.insert(0, email)
            email_entry.pack(pady=5)

            # Mobile
            label("Mobile Number").pack(anchor="w", pady=(10, 1))
            mobile_entry = ctk.CTkEntry(form, placeholder_text="Enter mobile number", width=400)
            mobile_entry.insert(0, mobile)
            mobile_entry.pack(pady=5)

            # Gender
            label("Gender").pack(anchor="w", pady=(10, 1))
            gender_opt = ctk.CTkOptionMenu(form, values=["Male", "Female"])
            gender_opt.set(gender)
            gender_opt.pack(pady=5)

# ========== BUTTON ROW (Edit + Save) ==========
            button_row = ctk.CTkFrame(card, fg_color="transparent")
            button_row.pack(pady=25)

# Disable/Enable fields
            def set_editable(state):
                mode = "normal" if state else "disabled"
                full_entry.configure(state=mode)
                email_entry.configure(state=mode)
                mobile_entry.configure(state=mode)
                gender_opt.configure(state=mode)

# By default fields are locked
            set_editable(False)

# Enable edit mode
            def enable_edit():
                set_editable(True)
                save_btn.configure(state="normal")
                edit_btn.configure(fg_color="#444")   # grey when active

# Save profile
            def save_profile():
                profiles = _load_profiles()
                if self.login_username not in profiles:
                    profiles[self.login_username] = {}

                profiles[self.login_username]["full_name"] = full_entry.get().strip()
                profiles[self.login_username]["email"] = email_entry.get().strip()
                profiles[self.login_username]["mobile"] = mobile_entry.get().strip()
                profiles[self.login_username]["gender"] = gender_opt.get()

                with open(_profiles_path(), "w", encoding="utf-8") as f:
                    json.dump(profiles, f, indent=4)

                set_editable(False)
                save_btn.configure(state="disabled")
                messagebox.showinfo("Saved", "Profile successfully updated.")
                self._redraw_topbar_profile()

# ---------- Buttons ---------
            edit_btn = ctk.CTkButton(
                button_row,
                text="✏ Edit",
                fg_color="#4b6cb7",
                hover_color="#3e5aa1",
                corner_radius=10,
                width=160,
                command=enable_edit
            )
            edit_btn.pack(side="left", padx=10)

            save_btn = ctk.CTkButton(
                button_row,
                text="💾 Save",
                fg_color="#6a11cb",
                hover_color="#501a9e",
                corner_radius=10,
                width=160,
                state="disabled",     # disabled until Edit pressed
                command=save_profile
            )
            save_btn.pack(side="left", padx=10)


# ============== Run App ==============
if __name__ == "__main__":
    try:
        root = ctk.CTk()
        Face_Reconition_System(root, authenticated=False)  # starts User_Authentication and app
        try:
            root.mainloop()
        except KeyboardInterrupt:
            try:
                root.destroy()
            except Exception:
                pass
    except Exception:
        tb = traceback.format_exc()
        try:
            messagebox.showerror("Startup failed", f"Startup failed. Traceback:\n\n{tb}")
        except Exception:
            print("Startup failed. Traceback:\n", tb)
        raise
