"""
student.py

Tabbed UI: Add Student | Student List | Edit Student | Delete Student
Local JSON storage (students.json) + profiles.json sync.
This version shows the two-column Add Student UI and includes a __main__
launcher that opens the Add Student form standalone for testing.
"""

import os
import json
import shutil
import traceback
from datetime import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox

# Directories / filenames
STUDENTS_JSON = "students.json"
PROFILES_JSON = "profiles.json"
MEDIA_DIR = os.path.join("media", "profile_pics")
os.makedirs(MEDIA_DIR, exist_ok=True)

DEFAULT_TARGET_ATTENDANCE = 0.75

# ----------------- helpers for JSON storage -----------------

def _here(*parts):
    return os.path.join(os.path.dirname(__file__), *parts)

def _students_path():
    return _here(STUDENTS_JSON)

def _profiles_path():
    return _here(PROFILES_JSON)

def _load_students():
    p = _students_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            # support list form (older) -> convert to dict keyed by username
            if isinstance(data, list):
                out = {}
                for s in data:
                    uname = (s.get("username") or "").strip()
                    if uname:
                        out[uname] = s
                return out
    except Exception:
        traceback.print_exc()
    return {}

def _save_students(data: dict):
    p = _students_path()
    try:
        # ensure deterministic order
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        traceback.print_exc()
        try:
            messagebox.showerror("Error", f"Failed to save students.json:\n{e}")
        except Exception:
            pass
        return False

def _load_profiles():
    p = _profiles_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        traceback.print_exc()
    return {}

def _save_profiles(data: dict):
    p = _profiles_path()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        traceback.print_exc()
        try:
            messagebox.showerror("Error", f"Failed to save profiles.json.")
        except Exception:
            pass
        return False

# ----------------- profile sync -----------------

def _normalize_profile_pic_path(path):
    """Return absolute path if file exists; else None."""
    if not path:
        return None
    if os.path.isabs(path) and os.path.exists(path):
        return path
    # if relative: interpret relative to project dir
    candidate = _here(path)
    if os.path.exists(candidate):
        return candidate
    return None

def _sync_profile_for_student(student: dict, old_username: str = None):
    """
    Merge student fields into profiles.json entry.
    Preserve is_certified and target_attendance if present.
    Ensures profile_pic path is stored (absolute if inside project).
    """
    try:
        if not student:
            return False
        uname = (student.get("username") or "").strip()
        if not uname:
            return False

        profiles = _load_profiles()
        # If username changed, move existing flags if any
        if old_username and old_username != uname and old_username in profiles:
            src = profiles.pop(old_username)
            dest = profiles.get(uname, {})
            for k in ("is_certified", "target_attendance"):
                if k in src and k not in dest:
                    dest[k] = src[k]
            profiles[uname] = dest

        existing = profiles.get(uname, {})
        is_cert = existing.get("is_certified", False)
        targ_att = existing.get("target_attendance", DEFAULT_TARGET_ATTENDANCE)

        merged = dict(existing)
        merged.update({
            "username": uname,
            "student_id": student.get("student_id", ""),
            "full_name": student.get("full_name", ""),
            "email": student.get("email", ""),
            "phone": student.get("phone", ""),
            "department": student.get("department", ""),
            "course": student.get("course", "")
        })

        # profile_pic: prefer student.profile_pic if exists, otherwise keep existing
        pic = student.get("profile_pic") or existing.get("profile_pic") or ""
        normalized = _normalize_profile_pic_path(pic)
        if normalized:
            merged["profile_pic"] = normalized
        else:
            # if the existing one is normalized, keep it
            existing_pic = existing.get("profile_pic")
            if existing_pic and _normalize_profile_pic_path(existing_pic):
                merged["profile_pic"] = _normalize_profile_pic_path(existing_pic)
            else:
                merged["profile_pic"] = ""

        merged["is_certified"] = is_cert
        merged["target_attendance"] = targ_att

        profiles[uname] = merged
        return _save_profiles(profiles)
    except Exception:
        traceback.print_exc()
        return False

# ----------------- image helpers -----------------

def _make_profile_image_for_username(src_path: str, username: str):
    """
    Copy/normalize image into MEDIA_DIR/<username>.<ext>.
    Returns destination path or empty string.
    """
    if not src_path or not os.path.exists(src_path) or not username:
        return ""
    try:
        _, ext = os.path.splitext(src_path)
        ext = ext.lower() if ext else ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
            ext = ".png"
        dest = os.path.join(MEDIA_DIR, f"{username}{ext}")
        # If file already exists but is different ext, prefer png output if possible
        try:
            # Try to copy; if you have Pillow you could normalize to PNG - but keep it simple
            shutil.copyfile(src_path, dest)
            return dest
        except Exception:
            # fallback: try to copy with different ext
            try:
                alt = os.path.join(MEDIA_DIR, f"{username}.png")
                shutil.copyfile(src_path, alt)
                return alt
            except Exception:
                traceback.print_exc()
                return ""
    except Exception:
        traceback.print_exc()
        return ""

# ----------------- Find helpers -----------------

def _find_student(student_id=None, username=None, students=None):
    students = students if students is not None else _load_students()
    if not students:
        return None
    if username:
        return students.get(username)
    if student_id:
        for s in students.values():
            if str(s.get("student_id", "")).strip() == str(student_id).strip():
                return s
    return None

# ----------------- UI classes -----------------

class AddStudentPage:
    """
    Two-column Add / Edit student page that matches the screenshot:
    - 'Personal Details' labelframe with two-column fields
    - 'Student Picture' area with long readonly path + purple 'Browse Image' button
    - Large green 'Save Student' and gray 'Clear' buttons
    - Keeps the same save/edit logic as before
    """
    def __init__(self, parent, student=None, on_saved=None):
        self.parent = parent
        self.on_saved = on_saved
        self.editing = bool(student)
        self._orig_student = student or {}

        self.frame = Frame(parent, bg="#f8f9ff")
        self.frame.pack(fill=BOTH, expand=True)

        header = Frame(self.frame, bg="#ffffff", height=68)
        header.pack(fill=X)
        self.title_label = Label(header, text="Edit Student" if self.editing else "Add Student",
                                 font=("Helvetica", 26, "bold"), bg="#ffffff", fg="#000000")
        self.title_label.pack(side=LEFT, padx=20, pady=14)

        # ---------- Personal Details (two column grid) ----------
        personal = LabelFrame(self.frame, text="Personal Details",
                              font=("Helvetica", 14, "bold"), bg="#f8f9ff", fg="#4b4b4b",
                              padx=12, pady=12)
        personal.pack(fill=X, padx=18, pady=(12, 6))

        # configure a 4-column grid so each label+entry pair is two columns
        for c in range(4):
            personal.columnconfigure(c, weight=1, minsize=80)

        def labelled_entry(ltext, r, c, attr, show=""):
            Label(personal, text=f"{ltext}:", font=("Helvetica", 11, "bold"), bg="#f8f9ff").grid(row=r, column=c*2, sticky="w", padx=(8,6), pady=6)
            e = Entry(personal, width=28)
            if show:
                e.config(show=show)
            e.grid(row=r, column=c*2+1, sticky="we", padx=(0,12), pady=6)
            setattr(self, attr, e)

        # Row 0
        labelled_entry("First Name", 0, 0, "first_name")
        labelled_entry("Registration Number", 0, 1, "student_id")

        # Row 1
        labelled_entry("Surname", 1, 0, "surname")
        # Faculty combobox on the right column
        Label(personal, text="Faculty:", font=("Helvetica", 11, "bold"), bg="#f8f9ff").grid(row=1, column=2, sticky="w", padx=(8,6), pady=6)
        self.faculty = ttk.Combobox(personal, values=["Select Faculty", "Engineering", "Commerce", "Arts"], state="readonly", width=26)
        self.faculty.current(0)
        self.faculty.grid(row=1, column=3, sticky="we", padx=(0,12), pady=6)

        # Row 2
        labelled_entry("Username", 2, 0, "username")
        labelled_entry("Course", 2, 1, "course")  # course is a simple entry here to match screenshot combobox look

        # Row 3
        labelled_entry("Password", 3, 0, "password", show="*")
        labelled_entry("Phone", 3, 1, "phone")

        # Row 4
        labelled_entry("Email Address", 4, 0, "email")
        labelled_entry("Parent Phone", 4, 1, "parent_phone")

        # Address spans both columns (full width)
        Label(personal, text="Address:", font=("Helvetica", 11, "bold"), bg="#f8f9ff").grid(row=5, column=0, sticky="w", padx=(8,6), pady=(8,2))
        self.address = Entry(personal)
        # span across the remaining 3 grid cells to get a long address field similar to screenshot
        self.address.grid(row=6, column=0, columnspan=4, sticky="we", padx=(8,12), pady=(0,8))

        # ---------- Student Picture ----------
        picture = LabelFrame(self.frame, text="Student Picture",
                             font=("Helvetica", 14, "bold"), bg="#f8f9ff", fg="#4b4b4b",
                             padx=12, pady=18)
        picture.pack(fill=X, padx=18, pady=(8, 12))

        Label(picture, text="Select or capture a profile picture", font=("Helvetica", 12), bg="#f8f9ff").grid(row=0, column=0, columnspan=3, sticky="w", padx=(8,6), pady=(4,10))

        self.selected_image_path = StringVar(value="")
        # long readonly entry for path
        path_entry = Entry(picture, textvariable=self.selected_image_path, width=60, state="readonly", readonlybackground="#f3f3f3")
        path_entry.grid(row=1, column=0, sticky="we", padx=(8,6), pady=(0,8))
        picture.columnconfigure(0, weight=1)

        # purple browse button to the right
        browse_btn = Button(picture, text="📁  Browse Image", command=self.browse_image,
                            font=("Helvetica", 11, "bold"), bg="#8e79ff", fg="white",
                            activebackground="#7a68e6", relief="flat", padx=16, pady=8)
        browse_btn.grid(row=1, column=1, sticky="e", padx=(8,12), pady=(0,8))

        # ---------- Actions (big buttons) ----------
        actions = Frame(self.frame, bg="#f8f9ff")
        actions.pack(fill=X, padx=18, pady=(6, 18))

        # Save button: large green like screenshot
        self.submit_btn = Button(actions, text=("Update Student" if self.editing else "Save Student"),
                                 font=("Helvetica", 14, "bold"), bg="#5cb85c", fg="white", activebackground="#4e9a48",
                                 relief="flat", padx=24, pady=12, command=self.save_student)
        self.submit_btn.pack(side=LEFT, padx=(6, 16))

        # Clear button: small grey
        clear_btn = Button(actions, text="Clear", command=self.clear_form,
                           font=("Helvetica", 13, "bold"), bg="#e6e6e6", fg="#000", relief="flat", padx=18, pady=12)
        clear_btn.pack(side=LEFT)

        # populate fields when editing
        if self.editing:
            self._load_student_into_form(self._orig_student)

    # small helpers (these remain simple and reuse existing logic)
    def browse_image(self):
        path = filedialog.askopenfilename(title="Select Profile Picture", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")])
        if path:
            self.selected_image_path.set(path)

    def clear_form(self):
        for attr in ("first_name", "surname", "username", "password", "email", "student_id", "phone", "parent_phone"):
            w = getattr(self, attr, None)
            if w:
                try:
                    w.delete(0, END)
                except Exception:
                    pass
        try:
            self.faculty.current(0)
        except Exception:
            pass
        try:
            # if course is a combobox, reset; if entry, clear it
            if hasattr(self.course, "current"):
                self.course.current(0)
            else:
                self.course.delete(0, END)
        except Exception:
            pass
        try:
            self.address.delete(0, END)
        except Exception:
            pass
        self.selected_image_path.set("")
        self.editing = False
        self._orig_student = {}
        try:
            self.title_label.config(text="Add Student")
            self.submit_btn.config(text="Save Student")
        except Exception:
            pass

    def _load_student_into_form(self, student):
        try:
            if not student:
                return
            # split full name into two fields
            full = (student.get("full_name") or "").strip()
            parts = full.split(None, 1) if full else ["", ""]
            self.first_name.delete(0, END); self.first_name.insert(0, parts[0] if parts else "")
            self.surname.delete(0, END); self.surname.insert(0, parts[1] if len(parts) > 1 else "")
            self.username.delete(0, END); self.username.insert(0, student.get("username") or "")
            self.password.delete(0, END)
            self.email.delete(0, END); self.email.insert(0, student.get("email") or "")
            self.student_id.delete(0, END); self.student_id.insert(0, student.get("student_id") or "")
            self.phone.delete(0, END); self.phone.insert(0, student.get("phone") or "")
            self.parent_phone.delete(0, END); self.parent_phone.insert(0, student.get("parent_phone") or "")
            self.address.delete(0, END); self.address.insert(0, student.get("address") or "")
            try:
                fac = student.get("department") or "Select Faculty"
                vals = ["Select Faculty", "Engineering", "Commerce", "Arts"]
                if fac in vals:
                    self.faculty.current(vals.index(fac))
                else:
                    self.faculty.current(0)
            except Exception:
                pass
            try:
                course = student.get("course") or "Select Course"
                # if course is a combobox settable, set it; otherwise populate entry
                if hasattr(self.course, "values"):
                    vals = list(self.course["values"]) if hasattr(self.course, "values") else []
                    if course in vals:
                        self.course.set(course)
                else:
                    self.course.delete(0, END); self.course.insert(0, course)
            except Exception:
                pass
            # profile_pic (save path or empty)
            self.selected_image_path.set(student.get("profile_pic") or "")
        except Exception:
            traceback.print_exc()

    def save_student(self):
        # gather fields
        first = (self.first_name.get() or "").strip()
        last = (self.surname.get() or "").strip()
        username = (self.username.get() or "").strip()
        password = (self.password.get() or "").strip()
        email = (self.email.get() or "").strip()
        student_id = (self.student_id.get() or "").strip()
        faculty = (self.faculty.get() or "").strip()
        try:
            course = (self.course.get() or "").strip()
        except Exception:
            course = ""
        phone = (self.phone.get() or "").strip()
        parent_phone = (self.parent_phone.get() or "").strip()
        address = (self.address.get() or "").strip()
        full_name = f"{first} {last}".strip()

        missing = []
        if not first: missing.append("First Name")
        if not last: missing.append("Surname")
        if not username: missing.append("Username")
        if not self.editing and not password: missing.append("Password")
        if not student_id: missing.append("Registration Number")

        if missing:
            messagebox.showerror("Missing fields", "Please fill: " + ", ".join(missing))
            return False

        # load students
        students = _load_students()

        # If adding and username already exists, error
        if not self.editing and username in students:
            messagebox.showerror("Duplicate", "Username already exists. Choose another.")
            return False

        old_username = (self._orig_student.get("username") or "").strip() if self.editing else None
        old_student_id = (self._orig_student.get("student_id") or "").strip() if self.editing else None

        # If editing and username changed, ensure no conflict with a different student
        if self.editing and old_username != username:
            if username in students:
                existing = students.get(username) or {}
                existing_sid = str(existing.get("student_id") or "").strip()
                if existing_sid != str(old_student_id):
                    messagebox.showerror("Duplicate", "New username conflicts with existing user.")
                    return False

        # handle picture copy/normalize
        pic_src = (self.selected_image_path.get() or "").strip()
        profile_pic = self._orig_student.get("profile_pic") if self.editing else ""
        if pic_src:
            dest = _make_profile_image_for_username(pic_src, username)
            if dest:
                profile_pic = dest

        # Build student record
        student = {
            "username": username,
            "student_id": student_id,
            "full_name": full_name,
            "password": password if password else self._orig_student.get("password", ""),
            "email": email,
            "phone": phone,
            "parent_phone": parent_phone,
            "department": faculty,
            "course": course,
            "address": address,
            "profile_pic": profile_pic,
            "updated_at": datetime.utcnow().isoformat()
        }

        try:
            if self.editing:
                key_to_remove = None
                if old_username and old_username in students:
                    key_to_remove = old_username
                
                else:
                    for k, v in list(students.items()):
                        try:
                            v_un = (v.get("username") or "").strip()
                            v_sid = str(v.get("student_id") or "").strip()
                        except Exception:
                            v_un = ""; v_sid = ""
                        if old_username and v_un == old_username:
                            key_to_remove = k
                            break
                        if old_student_id and v_sid == old_student_id:
                            key_to_remove = k
                            break
                
                if key_to_remove and key_to_remove != username:
                    try:
                        students.pop(key_to_remove, None)
                    except Exception:
                        pass
                # add new
                students[username] = student
                ok = _save_students(students)
                if ok:
                    messagebox.showinfo("Success", f"Student '{full_name}' added.")
                    # sync profiles.json
                    try:
                        _sync_profile_for_student(student, old_username)
                    except Exception:
                        traceback.print_exc()
                    # notify parent
                    if callable(self.on_saved):
                        try:
                            self.on_saved(student_id, username)
                        except Exception:
                            pass
                    return True
                else:
                    return False
            else:

                existing_key_for_sid = None
                for k, v in list(students.items()):
                    try:
                        v_sid = str(v.get("student_id") or "").strip()
                    except Exception:
                        v_sid = ""
                    if v_sid and v_sid == str(student_id):
                        existing_key_for_sid = k
                        break
                    if existing_key_for_sid and existing_key_for_sid != username:
                        try:
                            students.pop(existing_key_for_sid, None)
                        except Exception:
                            pass

                    students[username] = student
                    ok = _save_students(students)
                    if ok:
                        messagebox.showinfo("Success", f"Student '{full_name}' added.")
                        try:
                            _sync_profile_for_student(student, None)

                        except Exception:
                            traceback.print_exc()
                        if callable(self.on_saved):
                            try:
                                self.on_saved(student_id, username)
                            except Exception:
                                pass
                        self.clear_form()
                        return True
                    else:
                        return False
        except Exception as e:
            traceback.print_exc()
            try:
                messagebox.showerror("Error", f"Failed to save student:\n{e}")
            except Exception:
                pass 
            return False



class StudentListFrame:
    """Shows list and raises edit/delete callbacks."""
    def __init__(self, parent, on_edit=None, on_delete=None):
        self.parent = parent
        self.on_edit = on_edit
        self.on_delete = on_delete

        self.frame = Frame(parent, bg="#f8f9ff")
        self.frame.pack(fill=BOTH, expand=True)

        header = Frame(self.frame, bg="#ffffff", height=68)
        header.pack(fill=X)
        Label(header, text="Student List", font=("Helvetica", 20, "bold"), bg="#ffffff").pack(side=LEFT, padx=16, pady=16)

        ctrl = Frame(self.frame, bg="#f8f9ff")
        ctrl.pack(fill=X, padx=16, pady=(6, 0))
        Label(ctrl, text="Search:", bg="#f8f9ff").pack(side=LEFT)
        self.search_var = StringVar()
        Entry(ctrl, textvariable=self.search_var, width=36).pack(side=LEFT, padx=(8, 8))
        Button(ctrl, text="🔍", command=self.on_search).pack(side=LEFT)
        Button(ctrl, text="Refresh", command=self.load_students).pack(side=LEFT, padx=8)
        Button(ctrl, text="Edit -> Tab", command=self.trigger_edit_tab).pack(side=LEFT)
        Button(ctrl, text="Delete -> Tab", command=self.trigger_delete_tab).pack(side=LEFT, padx=8)
        Button(ctrl, text="View Picture", command=self.view_picture).pack(side=LEFT)

        cols = ("student_id", "username", "full_name", "department", "course", "email", "phone")
        self.tree = ttk.Treeview(self.frame, columns=cols, show="headings", selectmode="browse")
        headings = {"student_id": "Registration No", "username": "Username", "full_name": "Full Name",
                    "department": "Faculty", "course": "Course", "email": "Email", "phone": "Phone"}
        for c in cols:
            self.tree.heading(c, text=headings.get(c, c))
            self.tree.column(c, width=120, anchor="w")

        vsb = ttk.Scrollbar(self.frame, orient=VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self.frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(fill=BOTH, expand=True, padx=16, pady=12)
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)

        self.tree.bind("<Double-1>", self.on_double_click)
        self._rows = []
        self.load_students()

    def load_students(self):
        # clear tree
        for r in self.tree.get_children():
            self.tree.delete(r)
        self._rows = []

        students = _load_students()
        if not students:
            # placeholder
            try:
                if hasattr(self, "_placeholder"):
                    self._placeholder.destroy()
            except Exception:
                pass
            self._placeholder = Label(self.frame, text="No students found.\nAdd students in the 'Add Student' tab.",
                                       bg="#f8f9ff", fg="#444", font=("Helvetica", 12), justify=CENTER)
            self._placeholder.pack(fill=BOTH, expand=True, padx=20, pady=20)
            return
        else:
            try:
                if hasattr(self, "_placeholder"):
                    self._placeholder.destroy()
            except Exception:
                pass

        # Insert rows
        for uname, s in sorted(students.items(), key=lambda kv: (kv[1].get("full_name") or "").lower()):
            student_id = s.get("student_id", "")
            username = s.get("username", uname)
            full_name = s.get("full_name", "")
            department = s.get("department", "")
            course = s.get("course", "")
            email = s.get("email", "")
            phone = s.get("phone", "")
            profile_pic = s.get("profile_pic", "")
            display_row = (student_id, username, full_name, department, course, email, phone)
            iid = self.tree.insert("", "end", values=display_row)
            self._rows.append({
                "iid": iid,
                "student_id": student_id,
                "username": username,
                "full_name": full_name,
                "department": department,
                "course": course,
                "email": email,
                "phone": phone,
                "profile_pic": profile_pic,
                "raw": s
            })

    def on_search(self):
        q = (self.search_var.get() or "").strip().lower()
        if not q:
            self.load_students()
            return
        # simple filter
        for r in self.tree.get_children():
            self.tree.delete(r)
        for item in self._rows:
            if (q in (item.get("student_id") or "").lower()
                or q in (item.get("username") or "").lower()
                or q in (item.get("full_name") or "").lower()
                or q in (item.get("department") or "").lower()
                or q in (item.get("course") or "").lower()):
                display = (item["student_id"], item["username"], item["full_name"],
                           item["department"], item["course"], item["email"], item["phone"])
                self.tree.insert("", "end", values=display)

    def get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        for item in self._rows:
            if item["iid"] == iid:
                return item
        vals = self.tree.item(iid, "values")
        if vals:
            sid = vals[0]
            for item in self._rows:
                if str(item.get("student_id")) == str(sid):
                    return item
        return None

    def trigger_edit_tab(self):
        item = self.get_selected_row()
        if not item:
            messagebox.showinfo("No selection", "Please select a student to edit.")
            return
        if callable(self.on_edit):
            self.on_edit(item)

    def trigger_delete_tab(self):
        item = self.get_selected_row()
        if not item:
            messagebox.showinfo("No selection", "Please select a student to delete.")
            return
        if callable(self.on_delete):
            self.on_delete(item)

    def view_picture(self):
        item = self.get_selected_row()
        if not item:
            messagebox.showinfo("No selection", "Please select a student first.")
            return
        path = item.get("profile_pic")
        if not path:
            messagebox.showinfo("No picture", "This student does not have a profile picture.")
            return
        # normalize path
        if not os.path.isabs(path):
            path = _here(path)
        if not os.path.exists(path):
            messagebox.showwarning("Missing file", f"Picture file not found:\n{path}")
            return
        self._show_image_window(path, title=item.get("full_name") or item.get("username"))

    def _show_image_window(self, image_path, title="Picture"):
        w = Toplevel(self.parent)
        w.title(title)
        try:
            from PIL import Image, ImageTk
            im = Image.open(image_path)
            im.thumbnail((600, 600))
            photo = ImageTk.PhotoImage(im)
            lbl = Label(w, image=photo)
            lbl.image = photo
            lbl.pack(padx=8, pady=8)
        except Exception:
            traceback.print_exc()
            try:
                messagebox.showerror("Image Error", "Failed to open image.")
            except Exception:
                pass
            w.destroy()

    def on_double_click(self, event):
        item = self.get_selected_row()
        if not item:
            return
        pic = item.get("profile_pic")
        if pic and (os.path.exists(pic) or os.path.exists(_here(pic))):
            path = pic if os.path.isabs(pic) else _here(pic)
            try:
                self._show_image_window(path, title=item.get("full_name") or item.get("username"))
                return
            except Exception:
                traceback.print_exc()
        # fallback to edit
        self.trigger_edit_tab()


class DeleteStudentFrame:
    def __init__(self, parent, on_delete_confirm=None):
        self.parent = parent
        self.on_delete_confirm = on_delete_confirm
        self.frame = Frame(parent, bg="#fff6f6")
        self.frame.pack(fill=BOTH, expand=True)
        header = Frame(self.frame, bg="#ffffff", height=68)
        header.pack(fill=X)
        Label(header, text="Delete Student", font=("Helvetica", 20, "bold"), bg="#ffffff", fg="#b00000").pack(side=LEFT, padx=16, pady=16)
        self.info_lbl = Label(self.frame, text="Select a student in Student List and click 'Delete -> Tab'", bg="#fff6f6", fg="#333", font=("Helvetica", 12))
        self.info_lbl.pack(padx=20, pady=20)
        btn = Button(self.frame, text="Confirm Delete", bg="#d9534f", fg="white", font=("Helvetica", 14, "bold"), command=self._confirm)
        btn.pack(pady=10)
        self._current = None

    def load_student(self, student):
        self._current = student
        if not student:
            self.info_lbl.config(text="No student selected.")
        else:
            self.info_lbl.config(text=f"Delete: {student.get('full_name') or student.get('username')} ({student.get('student_id')})")

    def _confirm(self):
        if not self._current:
            messagebox.showinfo("No selection", "No student selected to delete.")
            return
        name = self._current.get("full_name") or self._current.get("username")
        if not messagebox.askyesno("Confirm Delete", f"Delete student '{name}'? This cannot be undone."):
            return
        try:
            students = _load_students()
            uname = (self._current.get("username") or "").strip()
            if uname and uname in students:
                # remove profile picture file if present
                pic = students[uname].get("profile_pic")
                if pic:
                    try:
                        p = pic if os.path.isabs(pic) else _here(pic)
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
                students.pop(uname, None)
                _save_students(students)
            # remove from profiles.json
            try:
                profiles = _load_profiles()
                if uname and uname in profiles:
                    profiles.pop(uname, None)
                    _save_profiles(profiles)
            except Exception:
                traceback.print_exc()

            try:
                messagebox.showinfo("Deleted", f"Student '{name}' deleted.")
            except Exception:
                pass

            try:
                w = getattr(self, 'frame', None)
                while w is not None:
                    if hasattr(w, 'on_students_changed') and callable(getattr(w, 'on_students_changed')):
                        try:
                            w.on_students_changed()
                        except Exception:
                            pass
                        break
                    w = getattr(w, 'master', None)

            except Exception:
                pass
            if callable(self.on_delete_confirm):
                try:
                    self.on_delete_confirm(self._current)
                except Exception:
                    pass
        except Exception:
            traceback.print_exc()
            try:
                messagebox.showerror("Error", "Failed to delete student.")
            except Exception:
                pass


class ManageStudentsTabs:
    """
    Tabbed UI combining Add, List, Edit, Delete.
    on_students_changed: optional callback invoked when data changed (so main app can refresh dashboard).
    """
    def __init__(self, parent, on_students_changed=None):
        self.parent = parent
        self.on_students_changed = on_students_changed

        self.container = Frame(parent, bg="#f8f9ff")
        self.container.pack(fill=BOTH, expand=True)
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill=BOTH, expand=True, padx=6, pady=6)

        self.tab_add = Frame(self.notebook, bg="#f8f9ff")
        self.tab_list = Frame(self.notebook, bg="#f8f9ff")
        self.tab_edit = Frame(self.notebook, bg="#f8f9ff")
        self.tab_delete = Frame(self.notebook, bg="#fff6f6")

        self.notebook.add(self.tab_add, text="Add Student")
        self.notebook.add(self.tab_list, text="Student List")
        self.notebook.add(self.tab_edit, text="Edit Student")
        self.notebook.add(self.tab_delete, text="Delete Student")

        # instantiate pages
        self.add_page = AddStudentPage(self.tab_add, on_saved=lambda sid, uname: self._on_child_saved(sid, uname))
        self.list_page = StudentListFrame(self.tab_list, on_edit=self.open_edit_tab_for, on_delete=self.open_delete_tab_for)
        self.edit_page = AddStudentPage(self.tab_edit, on_saved=lambda sid, uname: self._on_child_saved(sid, uname))
        self.delete_page = DeleteStudentFrame(self.tab_delete, on_delete_confirm=self._delete_confirmed)

        try:
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        except Exception:
            pass

    def _on_tab_changed(self, event):
        try:
            selected = event.widget.select()
            if event.widget.tab(selected, "text") == "Student List":
                try:
                    self.list_page.load_students()
                except Exception:
                    pass
        except Exception:
            pass

    def open_edit_tab_for(self, student_item):
        try:
            # student_item is the dict created in StudentListFrame._rows
            student_raw = student_item.get("raw") if isinstance(student_item, dict) else None
            if not student_raw:
                # try load by username
                uname = student_item.get("username") if isinstance(student_item, dict) else None
                student_raw = _find_student(username=uname)
            if not student_raw:
                messagebox.showerror("Error", "Could not load selected student.")
                return
            self.edit_page.clear_form()
            self.edit_page.editing = True
            self.edit_page._orig_student = student_raw.copy()
            self.edit_page.title_label.config(text="Edit Student")
            self.edit_page.submit_btn.config(text="Update Student")
            self.edit_page._load_student_into_form(student_raw)
            self.notebook.select(self.tab_edit)
        except Exception:
            traceback.print_exc()
            try:
                messagebox.showerror("Error", "Could not open edit tab.")
            except Exception:
                pass

    def open_delete_tab_for(self, student_item):
        try:
            student_raw = student_item.get("raw") if isinstance(student_item, dict) else None
            if not student_raw:
                uname = student_item.get("username") if isinstance(student_item, dict) else None
                student_raw = _find_student(username=uname)
            if not student_raw:
                messagebox.showerror("Error", "Could not load selected student.")
                return
            # pass a minimal dict structure expected by DeleteStudentFrame
            data = {
                "student_id": student_raw.get("student_id"),
                "username": student_raw.get("username"),
                "full_name": student_raw.get("full_name"),
                "profile_pic": student_raw.get("profile_pic")
            }
            self.delete_page.load_student(data)
            self.notebook.select(self.tab_delete)
        except Exception:
            traceback.print_exc()
            try:
                messagebox.showerror("Error", "Could not open delete tab.")
            except Exception:
                pass

    def _on_child_saved(self, sid, uname):
        """
        Called after a child Add/Edit page reports a successful save.
        Refresh the list, select the saved row, update profiles.json and notify parent app.
        """
        try:
            # refresh list
            self.notebook.select(self.tab_list)
            self.list_page.load_students()

            # select new/updated row
            for iid in self.list_page.tree.get_children():
                vals = self.list_page.tree.item(iid, "values")
                if (sid and str(vals[0]) == str(sid)) or (uname and str(vals[1]) == str(uname)):
                    self.list_page.tree.selection_set(iid)
                    self.list_page.tree.focus(iid)
                    self.list_page.tree.see(iid)
                    break

            # also sync profiles.json from the saved student
            try:
                # find student record and sync
                stud = _find_student(student_id=sid, username=uname)
                if stud:
                    _sync_profile_for_student(stud)
            except Exception:
                traceback.print_exc()

            # notify main app (so topbar/dashboard can refresh)
            try:
                if callable(self.on_students_changed):
                    self.on_students_changed()
            except Exception:
                traceback.print_exc()

        except Exception:
            traceback.print_exc()

    def _delete_confirmed(self, student_item):
        """
        Called after DeleteStudentFrame performed deletion to refresh list and notify parent.
        """
        try:
            # refresh list
            self.notebook.select(self.tab_list)
            self.list_page.load_students()
            # notify parent
            try:
                if callable(self.on_students_changed):
                    self.on_students_changed()
            except Exception:
                traceback.print_exc()
        except Exception:
            traceback.print_exc()


# allow importing specific classes
__all__ = ["ManageStudentsTabs", "AddStudentPage", "StudentListFrame", "DeleteStudentFrame"]


# ----------------- Standalone launcher for testing Add Student UI -----------------
if __name__ == "__main__":
    root = Tk()
    root.title("Add Student")
    root.geometry("1000x700+80+40")
    # Show only the Add Student form for quick testing
    add_page = AddStudentPage(root, on_saved=lambda sid, uname: print(f"Saved: {sid} / {uname}"))
    root.mainloop()
