# view_attendance.py
# Robust, tolerant reader for Attendance.csv that reliably shows a specific student's records
# Also includes a TeacherAttendancePage that allows teachers to view all students' records,
# filter/search/export and auto-refresh when Attendance.csv changes.

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import calendar
from datetime import datetime, date
import pandas as pd
import os
import threading
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import json
import time

ATTENDANCE_CSV = "Attendance.csv"
_BATCH_SIZE = 100
PROFILES_JSON = "profiles.json"


class ViewAttendancePage:
    def __init__(self, parent_frame, username):
        self.username = (username or "").strip()
        self.frame = ctk.CTkFrame(parent_frame, fg_color="white")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.status_label = ctk.CTkLabel(self.frame, text="", font=("Helvetica", 12), text_color="#666")
        self.status_label.pack(pady=6)

        self.table_frame = ctk.CTkFrame(self.frame, fg_color="white")
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.columns = ["Name", "Registration", "Department", "Date", "Time", "Status"]
        self.tree = ttk.Treeview(
            self.table_frame,
            columns=self.columns,
            show="headings",
            height=15
        )

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=150)
        self.tree.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        button_frame = ctk.CTkFrame(self.frame, fg_color="white")
        button_frame.pack(pady=15)

        refresh_btn = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            width=150,
            height=35,
            command=self.refresh_view
        )
        refresh_btn.grid(row=0, column=0, padx=10)

        delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete my Records ",
            fg_color="#d9534f",
            hover_color="#c9302c",
            width=180,
            height=35,
            command=self.delete_all_records
        )
        delete_btn.grid(row=0, column=1, padx=10)

        export_excel_btn = ctk.CTkButton(
            button_frame,
            text="📊 Download Excel",
            fg_color="#28a745",
            hover_color="#218838",
            width=180,
            height=35,
            command=self.download_excel
        )
        export_excel_btn.grid(row=0, column=2, padx=2)

        export_pdf_btn = ctk.CTkButton(
            button_frame,
            text="📄 Download PDF",
            fg_color="#007bff",
            hover_color="#0056b3",
            width=180,
            height=35,
            command=self.download_pdf
        )
        export_pdf_btn.grid(row=0, column=3, padx=10)

        calender_btn = ctk.CTkButton(
            button_frame,
            text="📅 Calendar",
            width=160,
            height=35,
            command=self.show_calendar
        )
        calender_btn.grid(row=0, column=4, padx=10)

        self._loading = False
        self._rows = []
        self._insert_index = 0

        self.calendar_container = ctk.CTkFrame(self.frame, fg_color="white")

        self.calendar_header = ctk.CTkFrame(self.calendar_container, fg_color="white")
        self.calendar_header.pack(fill="x", pady=(4, 8))

        self.prev_btn = ctk.CTkButton(self.calendar_header, text="◀ Prev", width=80,
                                      command=lambda: self._prev_month())
        self.prev_btn.pack(side="left", padx=(0, 6))

        self.today_btn = ctk.CTkButton(self.calendar_header, text="• Today", width=80,
                                       command=lambda: self._goto_today())
        self.today_btn.pack(side="left", padx=6)

        self.next_btn = ctk.CTkButton(self.calendar_header, text="Next ▶", width=80,
                                      command=lambda: self._next_month())
        self.next_btn.pack(side="left", padx=6)

        self.month_label = ctk.CTkLabel(self.calendar_header, text="", font=("Helvetica", 18, "bold"))
        self.month_label.pack(side="left", padx=12)

        self.close_cal_btn = ctk.CTkButton(
            self.calendar_header, text="✖ ", width=150,
            fg_color="#e11d48", hover_color="#000", command=self.close_calendar
        )
        self.close_cal_btn.pack(side="right")

        self.calendar_grid = ctk.CTkFrame(self.calendar_container, fg_color="white")
        self.calendar_grid.pack(fill="both", expand=True, padx=10, pady=10)

        today = date.today()
        self._cal_year = today.year
        self._cal_month = today.month
        self.threaded_load_data()

    # ---------------- helper to load profiles ----------------
    @staticmethod
    def _load_profiles():
        try:
            if not os.path.exists(PROFILES_JSON):
                return {}
            with open(PROFILES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    out = {}
                    for s in data:
                        u = s.get("username") or s.get("Username")
                        if u:
                            out[str(u).strip()] = s
                    return out
        except Exception:
            pass
        return {}

    def threaded_load_data(self):
        """Start a background thread to read CSV and prepare rows."""
        if self._loading:
            return
        self._loading = True
        self.status_label.configure(text="Loading records, please wait...")
        self.tree.delete(*self.tree.get_children())
        self._rows = []
        self._insert_index = 0

        self.thread = threading.Thread(target=self._read_csv_prepare_rows, daemon=True)
        self.thread.start()
        self.frame.after(50, self._insert_batch_ui)

    def _read_csv_prepare_rows(self):
        # Robust CSV -> normalize headers -> enrich from profiles.json
        if not os.path.exists(ATTENDANCE_CSV):
            self.frame.after(0, lambda: self.status_label.configure(text="⚠️ No attendance records found."))
            self._loading = False
            return

        try:
            df = pd.read_csv(ATTENDANCE_CSV, on_bad_lines='skip', dtype=str)
        except Exception as e:
            self.frame.after(0, lambda: messagebox.showerror("Error", f"Failed to read attendance file:\n{e}"))
            self.frame.after(0, lambda: self.status_label.configure(text=""))
            self._loading = False
            return

        if df.empty:
            self.frame.after(0, lambda: self.status_label.configure(text="ℹ️ No valid attendance data found."))
            self._loading = False
            return

        # Normalize column names (map lower->original) and strip header whitespace
        orig_cols = list(df.columns)
        col_map_lower = {c.lower().strip(): c for c in orig_cols}

        # identify username/date/time/status columns in a robust way
        username_candidates = ["username", "user", "user name", "user_name", "fullname", "full name", "full_name"]
        date_candidates = ["date", "day", "datetime", "timestamp"]
        time_candidates = ["time", "timestamp"]
        status_candidates = ["status", "presence", "state"]

        username_col = None
        date_col = None
        time_col = None
        status_col = None

        for cand in username_candidates:
            if cand in col_map_lower:
                username_col = col_map_lower[cand]
                break
        for cand in date_candidates:
            if cand in col_map_lower:
                date_col = col_map_lower[cand]
                break
        for cand in time_candidates:
            if cand in col_map_lower:
                time_col = col_map_lower[cand]
                break
        for cand in status_candidates:
            if cand in col_map_lower:
                status_col = col_map_lower[cand]
                break

        working = df.copy()

        # Trim whitespace in relevant string columns to avoid mismatch
        for c in working.columns:
            try:
                working[c] = working[c].astype(str).str.strip()
            except Exception:
                pass

        # If username column exists and we have a logged-in username, filter to that user
        if username_col:
            try:
                # case-insensitive match: compare lowered versions
                if self.username:
                    uname_l = str(self.username).strip().lower()
                    # create temporary lowered column to compare robustly
                    working["__cmp_uname__"] = working[username_col].astype(str).str.lower().fillna("")
                    working = working[working["__cmp_uname__"] == uname_l]
            except Exception:
                pass

        # load profiles so we can enrich missing FullName / StudentID / Department
        profiles = self._load_profiles()

        # Prepare target columns: FullName, StudentID, Department, Date, Time, Status
        final = pd.DataFrame()

        # Try to pick columns from CSV if present, else create empties
        # FullName heuristics
        full_name_col = None
        for cand in ("fullname", "full_name", "full name", "fullName", "name"):
            if cand in col_map_lower:
                full_name_col = col_map_lower[cand]
                break
        studentid_col = None
        for cand in ("studentid", "student_id", "registration", "registration no", "registration_no", "regno", "reg_no"):
            if cand in col_map_lower:
                studentid_col = col_map_lower[cand]
                break
        dept_col = None
        for cand in ("department", "dept", "course"):
            if cand in col_map_lower:
                dept_col = col_map_lower[cand]
                break

        # Build columns
        if full_name_col and full_name_col in working.columns:
            final["FullName"] = working[full_name_col].astype(str).fillna("")
        else:
            final["FullName"] = ""

        if studentid_col and studentid_col in working.columns:
            final["StudentID"] = working[studentid_col].astype(str).fillna("")
        else:
            # also try "Registration No" or similar exact header variants
            found = None
            for k in working.columns:
                if k.lower().strip().startswith("registration") or k.lower().strip().startswith("reg"):
                    found = k; break
            final["StudentID"] = working[found].astype(str).fillna("") if found else ""

        if dept_col and dept_col in working.columns:
            final["Department"] = working[dept_col].astype(str).fillna("")
        else:
            final["Department"] = ""

        # Date and Time
        if date_col and date_col in working.columns:
            final["Date"] = working[date_col].astype(str).fillna("")
        else:
            # fallback: try first column that looks like a date
            guess = None
            for c in working.columns:
                sample = working[c].dropna().astype(str).head(6).tolist()
                if any(("-" in s and len(s.split("-")[0]) == 4) or ("/" in s and len(s.split("/")[0]) in (1,2)) for s in sample):
                    guess = c; break
            final["Date"] = working[guess].astype(str).fillna("") if guess else ""

        # Time extraction helper (local function)
        def extract_time(s):
            try:
                s = str(s)
                # if datetime-like "2025-11-28 09:12:00" return the time portion
                if " " in s:
                    return s.split(" ", 1)[1].strip()
            except Exception:
                pass
            return ""

        # Time (explicit time column preferred; else try to split datetime)
        if time_col and time_col in working.columns:
            final["Time"] = working[time_col].astype(str).fillna("")
        elif date_col and date_col in working.columns:
            final["Time"] = working[date_col].astype(str).apply(extract_time).fillna("")
        else:
            final["Time"] = ""

        # Status
        if status_col and status_col in working.columns:
            final["Status"] = working[status_col].astype(str).fillna("")
        else:
            final["Status"] = ""

        # If username column exists and we filtered earlier but helper col left, drop it
        if "__cmp_uname__" in working.columns:
            try:
                working = working.drop(columns=["__cmp_uname__"])
            except Exception:
                pass

        # If the CSV did NOT contain a username column but we have a username, try to filter final rows using profile info
        if (username_col is None) and self.username:
            try:
                prof = profiles.get(self.username, {}) if isinstance(profiles, dict) else {}
                pid = str(prof.get("student_id") or prof.get("studentId") or prof.get("studentID") or "").strip()
                pname = str(prof.get("full_name") or prof.get("fullName") or prof.get("name") or "").strip().lower()
                if pid and final.get("StudentID") is not None:
                    final = final[final["StudentID"].astype(str).str.strip() == pid]
                elif pname and final.get("FullName") is not None:
                    final = final[final["FullName"].astype(str).str.strip().str.lower() == pname]
            except Exception:
                pass

        # Drop rows that don't have a Date or have empty FullName and StudentID (likely garbage rows)
        try:
            cond_date = final["Date"].astype(str).str.strip() != ""
            cond_ident = (final["FullName"].astype(str).str.strip() != "") | (final["StudentID"].astype(str).str.strip() != "")
            final = final[cond_date & cond_ident]
        except Exception:
            pass

        # Convert to list of rows expected by Treeview (Name, Registration, Department, Date, Time, Status)
        rows = []
        try:
            for _, r in final.iterrows():
                name = str(r.get("FullName") or "")
                sid = str(r.get("StudentID") or "")
                dept = str(r.get("Department") or "")
                dt = str(r.get("Date") or "")
                tm = str(r.get("Time") or "")
                st = str(r.get("Status") or "")
                rows.append([name, sid, dept, dt, tm, st])
        except Exception:
            rows = final.fillna("").values.tolist()

        # If the resulting rows are empty but username column exists, attempt a relaxed match (case-insensitive contains) on username column
        if not rows and username_col and self.username:
            try:
                df2 = pd.read_csv(ATTENDANCE_CSV, dtype=str, on_bad_lines='skip')
                df2 = df2.fillna("")
                uname_l = str(self.username).strip().lower()
                # attempt to find matching rows where the username column contains the username
                candidate_cols = [c for c in df2.columns if c.lower().strip() == username_col.lower().strip()]
                if candidate_cols:
                    mask_series = df2[candidate_cols[0]].astype(str).str.lower().str.contains(uname_l)
                    df2 = df2[mask_series]
                    # remap to expected output
                    for _, r in df2.iterrows():
                        name = r.get('FullName', '') if 'FullName' in r else r.get(candidate_cols[0], '')
                        sid = r.get('StudentID', '') if 'StudentID' in r else ''
                        dept = r.get('Department', '') if 'Department' in r else ''
                        dt = r.get('Date', '') if 'Date' in r else ''
                        tm = r.get('Time', '') if 'Time' in r else ''
                        st = r.get('Status', '') if 'Status' in r else ''
                        rows.append([name, sid, dept, dt, tm, st])
            except Exception:
                pass

        self._rows = rows
        self._loading = False

    def _insert_batch_ui(self):
        if self._insert_index < len(self._rows):
            end = min(self._insert_index + _BATCH_SIZE, len(self._rows))
            for r in self._rows[self._insert_index:end]:
                vals = ["" if v is None else str(v) for v in r]
                self.tree.insert("", "end", values=vals)
            self._insert_index = end
            self.frame.after(10, self._insert_batch_ui)
            self.status_label.configure(text=f"Loaded {self._insert_index}/{len(self._rows)} records...")
            return
        if self._loading:
            self.frame.after(50, self._insert_batch_ui)
            return
        if not self._rows:
            self.status_label.configure(text="No attendance records found for this user.")
        else:
            self.status_label.configure(
                text="Attendance Records",
                font=("Helvetica", 19, "bold"),
                text_color="black"
            )
        return

    def refresh_view(self):
        self._rows = []
        self._insert_index = 0
        self._loading = False
        self.tree.delete(*self.tree.get_children())
        self.threaded_load_data()

    def load_attendance(self):
        """Reload attendance data from the CSV file (called after marking attendance)."""
        self.refresh_view()

    def delete_all_records(self):
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL attendance records?")
        if not confirm:
            return
        try:
            if os.path.exists(ATTENDANCE_CSV):
                df = pd.read_csv(ATTENDANCE_CSV)
                if "Username" in df.columns:
                    df = df[~df["Username"].astype(str).str.strip().str.lower().eq(str(self.username).strip().lower())]
                else:
                    profiles = self._load_profiles()
                    prof = profiles.get(self.username, {}) if isinstance(profiles, dict) else {}
                    pid = str(prof.get("student_id") or prof.get("studentId") or prof.get("studentID") or "").strip()
                    pname = str(prof.get("full_name") or prof.get("fullName") or prof.get("name") or "").strip().lower()
                    if pid:
                        df = df[~df.apply(lambda r: str(r.astype(str).get("StudentID", "")).strip() == pid, axis=1)]
                    elif pname:
                        df = df[~df.apply(lambda r: str(r.astype(str).get("FullName", "")).strip().lower() == pname, axis=1)]
                df.to_csv(ATTENDANCE_CSV, index=False)
            self._rows = []
            self._insert_index = 0
            self.tree.delete(*self.tree.get_children())
            self.status_label.configure(text="🗑️ All attendance records deleted for this user.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete records:\n{e}")

    def download_excel(self):
        if not os.path.exists(ATTENDANCE_CSV):
            messagebox.showinfo("Info", "No attendance file found to export.")
            return
        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                title="Save Report as Excel"
            )
            if not save_path:
                return
            df = pd.read_csv(ATTENDANCE_CSV)
            if "Username" in df.columns:
                df = df[df["Username"].astype(str).str.strip().str.lower() == str(self.username).strip().lower()]
            else:
                profiles = self._load_profiles()
                prof = profiles.get(self.username, {}) if isinstance(profiles, dict) else {}
                pid = str(prof.get("student_id") or prof.get("studentId") or prof.get("studentID") or "").strip()
                pname = str(prof.get("full_name") or prof.get("fullName") or prof.get("name") or "").strip().lower()
                if pid and "StudentID" in df.columns:
                    df = df[df["StudentID"].astype(str).str.strip() == pid]
                elif pname and "FullName" in df.columns:
                    df = df[df["FullName"].astype(str).str.strip().str.lower() == pname]
            df.to_excel(save_path, index=False)
            messagebox.showinfo("Success", f"Excel report saved successfully:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Excel file:\n{e}")

    def download_pdf(self):
        if not os.path.exists(ATTENDANCE_CSV):
            messagebox.showinfo("Info", "No attendance file found to export.")
            return
        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Save PDF Report As"
            )
            if not save_path:
                return

            df = pd.read_csv(ATTENDANCE_CSV)
            if "Username" in df.columns:
                df = df[df["Username"].astype(str).str.strip().str.lower() == str(self.username).strip().lower()]

            if df.empty:
                messagebox.showinfo("Info", "No records found to export.")
                return

            cols = df.columns.tolist()
            colmap = {c.lower(): c for c in cols}
            use_full = colmap.get("fullname") or colmap.get("full_name") or colmap.get("name") or None
            use_sid = colmap.get("studentid") or colmap.get("student_id") or colmap.get("registration") or None
            use_dept = colmap.get("department") or colmap.get("dept") or None
            use_date = colmap.get("date") or colmap.get("datetime") or None
            use_time = colmap.get("time") or None

            table_rows = []
            for _, row in df.iterrows():
                fullname = row.get(use_full, "") if use_full else ""
                sid = row.get(use_sid, "") if use_sid else ""
                dept = row.get(use_dept, "") if use_dept else ""
                datev = row.get(use_date, "") if use_date else ""
                timev = row.get(use_time, "") if use_time else ""
                table_rows.append([str(sid), str(fullname), str(self.username or ""), str(dept), str(datev), str(timev), str(row.get("Status", ""))])
            data = [["Registration No", "FullName", "Username", "Department", "Date", "Time", "Status"]] + table_rows

            pdf = SimpleDocTemplate(save_path, pagesize=A4)
            styles = getSampleStyleSheet()
            title = Paragraph("Attendance Report", styles["Title"])

            table = Table(data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]))

            pdf.build([title, table])
            messagebox.showinfo("Success", f"PDF report saved successfully:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create PDF file:\n{e}")

    def show_calendar(self):
        self.table_frame.pack_forget()
        self.calendar_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._render_month()
        self.status_label.configure(text="Calendar opened.")

    def close_calendar(self):
        self.calendar_container.pack_forget()
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.status_label.configure(text="📋 Table View")

    def _render_month(self):
        for w in self.calendar_grid.winfo_children():
            w.destroy()

        month_name = calendar.month_name[self._cal_month]
        self.month_label.configure(text=f"{month_name} {self._cal_year}")

        head = ctk.CTkFrame(self.calendar_grid, fg_color="white")
        head.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 6))
        for i, wd in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            lbl = ctk.CTkLabel(head, text=wd, font=("Helvetica", 13, "bold"))
            lbl.grid(row=0, column=i, padx=5, sticky="nsew")
            head.grid_columnconfigure(i, weight=1)

        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(self._cal_year, self._cal_month)
        present_days = self._get_present_days()
        today_d = date.today()

        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                in_month = (day.month == self._cal_month)
                if not in_month:
                    bg, fg = "#e5e7eb", "#64748b"
                elif day == today_d:
                    bg, fg = "#2563eb", "white"
                elif day < today_d and (day.day not in present_days):
                    bg, fg = "#ef4444", "white"
                elif day.day in present_days:
                    bg, fg = "#22c55e", "white"
                else:
                    bg, fg = "#e2e8f0", "black"

                cell = ctk.CTkFrame(self.calendar_grid, fg_color=bg, corner_radius=8)
                cell.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
                ctk.CTkLabel(cell, text=str(day.day), font=("Helvetica", 14, "bold"), text_color=fg).pack(pady=8)

        for i in range(7):
            self.calendar_grid.grid_columnconfigure(i, weight=1)
        for i in range(len(weeks) + 1):
            self.calendar_grid.grid_rowconfigure(i, weight=1)

    def _get_present_days(self):
        days = set()
        if not os.path.exists(ATTENDANCE_CSV):
            return days

        try:
            df = pd.read_csv(ATTENDANCE_CSV, on_bad_lines="skip", dtype=str)
            df = df.fillna("")
            # Try username match if present
            if "Username" in df.columns:
                uname_l = str(self.username).strip().lower()
                df = df[df["Username"].astype(str).str.strip().str.lower() == uname_l]

            # find a date column
            if "Date" not in df.columns:
                for c in df.columns:
                    sample = df[c].astype(str).head(4).tolist()
                    if any(("-" in s and len(s.split("-")[0]) == 4) or ("/" in s and len(s.split("/")[-1]) == 4) for s in sample):
                        df["Date"] = df[c]
                        break
            if "Date" not in df.columns:
                return days

            for d in df["Date"].astype(str).fillna(""):
                dt = self._parse_date_safe(d)
                if dt and dt.year == self._cal_year and dt.month == self._cal_month:
                    days.add(dt.day)
        except Exception:
            pass
        return days

    @staticmethod
    def _parse_date_safe(val):
        s = str(val)
        fmts = (
            "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S",
            "%Y/%m/%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"
        )

        for f in fmts:
            try:
                return datetime.strptime(s, f)
            except Exception:
                continue

        try:
            return pd.to_datetime(s).to_pydatetime()
        except Exception:
            return None

    def _prev_month(self):
        if self._cal_month == 1:
            self._cal_month = 12
            self._cal_year -= 1
        else:
            self._cal_month -= 1
        self._render_month()

    def _next_month(self):
        if self._cal_month == 12:
            self._cal_month = 1
            self._cal_year += 1
        else:
            self._cal_month += 1
        self._render_month()

    def _goto_today(self):
        t = date.today()
        self._cal_year, self._cal_month = t.year, t.month
        self._render_month()


# -------------------- Teacher view --------------------
class TeacherAttendancePage:
    """
    Teacher view: shows all attendance records with filtering, search, export and auto-refresh on CSV change.
    Instantiate only when current user is a teacher.
    """

    def __init__(self, parent_frame, autoscan_interval_ms=3000):
        self.frame = ctk.CTkFrame(parent_frame, fg_color="white")
        self.frame.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(self.frame, fg_color="white")
        header.pack(fill="x", pady=(6, 8))
        ctk.CTkLabel(header, text="Teacher — Attendance Records", font=("Segoe UI", 16, "bold")).pack(side="left")

        ctl = ctk.CTkFrame(header, fg_color="white")
        ctl.pack(side="right")

        self.filter_var = ctk.CTkEntry(ctl, placeholder_text="Search (reg/name/username)")
        self.filter_var.pack(side="left", padx=(0, 8))
        self.filter_btn = ctk.CTkButton(ctl, text="Search", command=self._apply_filter)
        self.filter_btn.pack(side="left", padx=(0, 8))
        self.clear_btn = ctk.CTkButton(ctl, text="Clear", command=self._clear_filter)
        self.clear_btn.pack(side="left", padx=(0, 8))

        self.refresh_btn = ctk.CTkButton(ctl, text="Refresh All", command=self.refresh_view)
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.export_btn = ctk.CTkButton(ctl, text="Export (Filtered)", command=self.export_filtered_excel)
        self.export_btn.pack(side="left", padx=(0, 8))

        # table
        cols = ["Registration", "FullName", "Username", "Department", "Date", "Time", "Status"]
        self.tree = ttk.Treeview(self.frame, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=8)

        vsb = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        self.status_label = ctk.CTkLabel(self.frame, text="Loading...", text_color="#444")
        self.status_label.pack(anchor="w", padx=6)

        self._rows = []
        self._csv_mtime = None
        self._autoscan_interval_ms = autoscan_interval_ms
        self._stop_scan = False

        # initial load
        self.refresh_view()
        # start autoscan thread
        self._scan_thread = threading.Thread(target=self._watch_csv_loop, daemon=True)
        self._scan_thread.start()

    def _normalize_cols(self, df):
        # ensure the dataframe has the standard columns (best-effort)
        df = df.fillna("")
        cols = df.columns.tolist()
        lower = {c.lower().strip(): c for c in cols}
        mapping = {}
        mapping['Registration'] = lower.get('registration') or lower.get('registration no') or lower.get('regno') or lower.get('studentid') or lower.get('student_id') or None
        mapping['FullName'] = lower.get('fullname') or lower.get('full_name') or lower.get('name') or None
        mapping['Username'] = lower.get('username') or lower.get('user') or None
        mapping['Department'] = lower.get('department') or lower.get('dept') or None
        mapping['Date'] = lower.get('date') or lower.get('datetime') or None
        mapping['Time'] = lower.get('time') or None
        mapping['Status'] = lower.get('status') or None

        out = pd.DataFrame()
        out['Registration'] = df[mapping['Registration']] if mapping['Registration'] in df.columns else ""
        out['FullName'] = df[mapping['FullName']] if mapping['FullName'] in df.columns else ""
        out['Username'] = df[mapping['Username']] if mapping['Username'] in df.columns else ""
        out['Department'] = df[mapping['Department']] if mapping['Department'] in df.columns else ""
        out['Date'] = df[mapping['Date']] if mapping['Date'] in df.columns else ""
        out['Time'] = df[mapping['Time']] if mapping['Time'] in df.columns else ""
        out['Status'] = df[mapping['Status']] if mapping['Status'] in df.columns else ""
        return out

    def refresh_view(self):
        try:
            if not os.path.exists(ATTENDANCE_CSV):
                self._rows = []
                self._populate_tree([])
                self.status_label.configure(text="No attendance file found.")
                return
            df = pd.read_csv(ATTENDANCE_CSV, dtype=str, on_bad_lines='skip')
            if df.empty:
                self._rows = []
                self._populate_tree([])
                self.status_label.configure(text="No records found.")
                return
            df = self._normalize_cols(df)
            # save internal rows
            self._rows = df.values.tolist()
            self._populate_tree(self._rows)
            try:
                self._csv_mtime = os.path.getmtime(ATTENDANCE_CSV)
            except Exception:
                self._csv_mtime = None
            self.status_label.configure(text=f"Loaded {len(self._rows)} records.")
        except Exception as e:
            self.status_label.configure(text=f"Error loading CSV: {e}")

    def _populate_tree(self, rows):
        # clear and insert
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=[str(x) for x in r])

    def _apply_filter(self):
        txt = str(self.filter_var.get()).strip().lower()
        if not txt:
            self._populate_tree(self._rows)
            return
        try:
            df = pd.DataFrame(self._rows, columns=['Registration', 'FullName', 'Username', 'Department', 'Date', 'Time', 'Status'])
            # corrected, robust mask
            mask = df.apply(
                lambda r: (
                    txt in str(r.get('Registration', '')).lower()
                    or txt in str(r.get('FullName', '')).lower()
                    or txt in str(r.get('Username', '')).lower()
                ),
                axis=1
            )
            filtered = df[mask]
            self._populate_tree(filtered.values.tolist())
            self.status_label.configure(text=f"Showing {len(filtered)} filtered records.")
        except Exception as e:
            self.status_label.configure(text=f"Filter error: {e}")

    def _clear_filter(self):
        self.filter_var.delete(0, 'end')
        self._populate_tree(self._rows)
        self.status_label.configure(text=f"Loaded {len(self._rows)} records.")

    def export_filtered_excel(self):
        try:
            # gather current displayed rows
            displayed = [self.tree.item(i)['values'] for i in self.tree.get_children()]
            if not displayed:
                messagebox.showinfo("Info", "No records to export.")
                return
            save_path = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel files', '*.xlsx')])
            if not save_path:
                return
            df = pd.DataFrame(displayed, columns=['Registration', 'FullName', 'Username', 'Department', 'Date', 'Time', 'Status'])
            df.to_excel(save_path, index=False)
            messagebox.showinfo("Success", f"Exported {len(displayed)} rows to {save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def _watch_csv_loop(self):
        """Background loop to watch CSV mtime and refresh automatically."""
        while not self._stop_scan:
            try:
                if os.path.exists(ATTENDANCE_CSV):
                    try:
                        m = os.path.getmtime(ATTENDANCE_CSV)
                    except Exception:
                        m = None
                    if m and self._csv_mtime is None:
                        self._csv_mtime = m
                    elif m and self._csv_mtime != m:
                        self._csv_mtime = m
                        # refresh in main thread
                        try:
                            self.frame.after(100, self.refresh_view)
                        except Exception:
                            self.refresh_view()
                time.sleep(max(0.5, self._autoscan_interval_ms/1000.0))
            except Exception:
                time.sleep(1.0)

    def stop(self):
        self._stop_scan = True
