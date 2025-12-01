import customtkinter as ctk
from PIL import Image
import os
import mysql.connector
from tkinter import messagebox, ttk
import traceback
import tkinter as tk
import time

# ------------------ MySQL Configuration ------------------
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "your_password"  # 👈 Replace with your actual password
MYSQL_DB = "face_attendance"


# ------------------ Database Helper ------------------
def connect_database():
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        if conn.is_connected():
            print("[OK] Database connection successful!")  # Windows-safe print
            return conn
    except mysql.connector.Error as err:
        print("[ERROR] Database connection failed:", err)  # Windows-safe print
        messagebox.showerror("Database Error", f"Connection failed: {err}")
    return None



# ------------------ User Authentication Class ------------------
class User_Authentication:
    def __init__(self, root):
        self.root = root
        self.root.title("Login")
        self.root.geometry("1200x700+100+50")
        self.root.resizable(False, False)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.primary = "#7b2ff7"
        self.bg_color = "#f5f6fa"

        # ------------------ Frames ------------------
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        self.left_frame = ctk.CTkFrame(self.main_frame, width=450, fg_color=self.bg_color)
        self.left_frame.pack(side="left", fill="both")

        self.right_frame = ctk.CTkFrame(self.main_frame, width=450, fg_color="transparent")
        self.right_frame.pack(side="right", fill="both", expand=True)

        # Load image
        self.img_tk = None
        self.image_label = None
        self.load_image("s.png", angle=90, size=(450, 500))

        if self.img_tk:
            self.image_label = ctk.CTkLabel(self.right_frame, image=self.img_tk, text="")
            self.image_label.pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(self.right_frame, text="Image not found", font=("Poppins", 20),
                         text_color="gray").pack(fill="both", expand=True)

        self.create_main_selection()

    # ------------------ Load Image ------------------
    def load_image(self, image_name, angle=0, size=(450, 500)):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_name)
        if not os.path.exists(path):
            return
        from customtkinter import CTkImage
        img = Image.open(path)
        img = img.rotate(angle, expand=True)
        img = img.resize(size)
        self.img_tk = CTkImage(light_image=img, dark_image=img, size=size)
    

    # ------------------ Utility ------------------
    def clear_left_frame(self):
        for widget in self.left_frame.winfo_children():
            widget.destroy()

    # ------------------ Main Selection ------------------
    def create_main_selection(self):
        self.clear_left_frame()
        ctk.CTkLabel(self.left_frame, text="Select Login Type", font=("Poppins SemiBold", 28),
                     text_color="black").place(x=80, y=100)

        ctk.CTkButton(self.left_frame, text="👨‍🏫 Teacher Login", font=("Poppins SemiBold", 20),
                      width=300, height=50, fg_color=self.primary, hover_color="#682ae9",
                      command=self.create_teacher_login).place(x=75, y=200)

        ctk.CTkButton(self.left_frame, text="🎓 Student Login", font=("Poppins SemiBold", 20),
                      width=300, height=50, fg_color=self.primary, hover_color="#682ae9",
                      command=self.create_student_login).place(x=75, y=280)

    # ------------------ Teacher Login ------------------
    def create_teacher_login(self):
        self.clear_left_frame()
        ctk.CTkLabel(self.left_frame, text="Teacher Login", font=("Poppins SemiBold", 28),
                     text_color="black").place(x=80, y=80)

        self.teacher_username = ctk.CTkEntry(self.left_frame, placeholder_text="Username",
                                             width=300, height=40, corner_radius=15)
        self.teacher_username.place(x=50, y=160)

        self.teacher_password = ctk.CTkEntry(self.left_frame, placeholder_text="Password",
                                             show="*", width=300, height=40, corner_radius=15)
        self.teacher_password.place(x=50, y=220)

        ctk.CTkButton(self.left_frame, text="Login", font=("Poppins SemiBold", 21),
                      width=300, height=40, fg_color=self.primary,
                      hover_color="#682ae9", command=self.teacher_login_action).place(x=50, y=280)
        
        ctk.CTkButton(self.left_frame, text="Forgot Password", font=("Poppins", 14),
                      fg_color="transparent", hover_color="#eee", text_color=self.primary,
                      command=self.teacher_forgot_inplace).place(x=50, y=340)

        ctk.CTkButton(self.left_frame, text="⬅ Back", font=("Poppins", 14),
                      fg_color="transparent", hover_color="#eee", text_color=self.primary,
                      command=self.create_main_selection).place(x=50, y=380)

    # ------------------ Student Login ------------------
    def create_student_login(self):
        self.clear_left_frame()
        ctk.CTkLabel(self.left_frame, text="Student Login", font=("Poppins SemiBold", 28),
                     text_color="black").place(x=80, y=60)

        self.student_id = ctk.CTkEntry(self.left_frame, placeholder_text="Student ID",
                                       width=300, height=40, corner_radius=15)
        self.student_id.place(x=50, y=140)

        self.student_username = ctk.CTkEntry(self.left_frame, placeholder_text="Username",
                                             width=300, height=40, corner_radius=15)
        self.student_username.place(x=50, y=200)

        self.student_password = ctk.CTkEntry(self.left_frame, placeholder_text="Password",
                                             show="*", width=300, height=40, corner_radius=15)
        self.student_password.place(x=50, y=260)

        ctk.CTkButton(self.left_frame, text="Login", font=("Poppins SemiBold", 21),
                      width=300, height=40, fg_color=self.primary,
                      hover_color="#682ae9", command=self.student_login_action).place(x=50, y=320)

        # ⭐ ADDED Student Forgot Password Button
        ctk.CTkButton(self.left_frame, text="Forgot Password", font=("Poppins", 14),
                      fg_color="transparent", hover_color="#eee", text_color=self.primary,
                      command=self.student_forgot_inplace).place(x=50, y=360)

        ctk.CTkButton(self.left_frame, text="⬅ Back", font=("Poppins", 14),
                      fg_color="transparent", hover_color="#eee", text_color=self.primary,
                      command=self.create_main_selection).place(x=50, y=410)
        
    def teacher_login_action(self):
        username = self.teacher_username.get().strip()
        password = self.teacher_password.get().strip()

        if not username or not password:
            messagebox.showwarning("Input error", "Please fill all input fields")
            return
        
        conn = connect_database()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT full_name FROM teachers WHERE username=%s AND password=%s",
                               (username, password))
                
                result = cursor.fetchone()
                if result:
                    full_name = result[0]
                    self.show_welcome_animation(full_name, lambda: self._open_main_after_login(
                        user_role="Teacher", username=username))
                else:
                    messagebox.showerror("Login failed", "Invalid username or password")
            except Exception:
                traceback.print_exc()
                messagebox.showerror("Error", "An error occurred during login.")
            finally:
                conn.close()

    def teacher_forgot_inplace(self):
        self.clear_left_frame()
        ctk.CTkLabel(self.left_frame, text="Forget Password (Teacher)", font=("Poppins SemiBold", 22),
                     text_color="black").place(x=40, y=30)
        
        ctk.CTkLabel(self.left_frame, text="Username").place(x=30, y=90)
        username_entry = ctk.CTkEntry(self.left_frame, width=320, height=35)
        username_entry.place(x=30, y=120)


        ctk.CTkLabel(self.left_frame, text="New Password").place(x=30, y=170)
        new_entry = ctk.CTkEntry(self.left_frame, show="*", width=320, height=35)
        new_entry.place(x=30, y=200)


        ctk.CTkLabel(self.left_frame, text="Confirm Password").place(x=30, y=250)
        confirm_entry = ctk.CTkEntry(self.left_frame, show="*", width=320, height=35)
        confirm_entry.place(x=30, y=280)


        def reset_action():
            username = username_entry.get().strip()
            new = new_entry.get().strip()
            confirm = confirm_entry.get().strip()


            if not (username and new and confirm):
                messagebox.showwarning("Input Error", "Fill all fields.")
                return
            if new != confirm:
                messagebox.showwarning("Mismatch", "Passwords do not match.")
                return
        
            conn = connect_database()

            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE teachers SET password=%s WHERE username=%s",
                               (new,username))
                    conn.commit()
                    messagebox.showinfo("Success", "Password reset successful.")
                    self.create_teacher_login()

                except Exception:
                    traceback.print_exc()
                    messagebox.showerror("Error", "Failed to reset password.")
                finally:
                    conn.close()

        ctk.CTkButton(self.left_frame, text="Reset Password", width=320, height=40,
                        fg_color=self.primary, hover_color="#682ae9",
                        command=reset_action).place(x=30, y=330)

        # BACK button (added)
        ctk.CTkButton(self.left_frame, text="⬅ Back", font=("Poppins", 14),
                        fg_color="transparent", hover_color="#eee", text_color=self.primary,
                        command=self.create_teacher_login).place(x=30, y=380)
    
    def student_login_action(self):
        student_id = self.student_id.get().strip()
        username = self.student_username.get().strip()
        password = self.student_password.get().strip()

        if not student_id or not username or not password:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        conn = connect_database()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT full_name FROM students WHERE student_id=%s AND username=%s AND password=%s",
                    (student_id, username, password)
                )
                result = cursor.fetchone()
                if result:
                    full_name = result[0]
                    self.show_welcome_animation(full_name, lambda: self._open_main_after_login(
                        user_role="Student", username=username, student_id=student_id))
                    
                else:
                    messagebox.showerror("Login Failed", "Invalid credentials.")
            except Exception:
                traceback.print_exc()
                messagebox.showerror("Error", "An error occurred during login.")
            finally:
                conn.close()

    def student_forgot_inplace(self):
        self.clear_left_frame()
        ctk.CTkLabel(self.left_frame, text="Forgot Password (Student)", font=("Poppins SemiBold", 22),
                     text_color="black").place(x=40, y=30)
        
        ctk.CTkLabel(self.left_frame, text="Student ID").place(x=30, y=90)
        sid_entry = ctk.CTkEntry(self.left_frame, width=320, height=35)
        sid_entry.place(x=30, y=120)
        
        ctk.CTkLabel(self.left_frame, text="Username").place(x=30, y=170)
        username_entry = ctk.CTkEntry(self.left_frame, width=320, height=35)
        username_entry.place(x=30, y=200)

        ctk.CTkLabel(self.left_frame, text="New Password").place(x=30, y=250)
        new_entry = ctk.CTkEntry(self.left_frame, show="*", width=320, height=35)
        new_entry.place(x=30, y=280)

        ctk.CTkLabel(self.left_frame, text="Confirm New Password").place(x=30, y=330)
        confirm_entry = ctk.CTkEntry(self.left_frame, show="*", width=320, height=35)
        confirm_entry.place(x=30, y=360)

        def reset_action():
            sid = sid_entry.get().strip()
            username = username_entry.get().strip()
            new = new_entry.get().strip()
            confirm = confirm_entry.get().strip()

            if not (sid and username and new and confirm):
                messagebox.showwarning("Input Error", "Fill all fields.")
                return
            
            conn = connect_database()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE students SET password=%s WHERE student_id=%s AND username=%s",
                                   (new, sid, username))
                    
                    conn.commit()
                    messagebox.showinfo("Success", "Password reset successful.")
                    self.create_student_login()
                except Exception:
                    traceback.print_exc()
                    messagebox.showerror("Error", "Failed to reset password.")

                finally:
                    conn.close()
                
        ctk.CTkButton(self.left_frame, text="Reset Password", width=320, height=40,
                      fg_color=self.primary, hover_color="#682ae9",
                      command=reset_action).place(x=30, y=410)
            
        ctk.CTkButton(self.left_frame, text="⬅ Back", font=("Poppins", 14),
                      fg_color="transparent", hover_color="#eee", text_color=self.primary,
                      command=self.create_student_login).place(x=30, y=455)
            
    def _open_main_after_login(self, user_role, username, student_id=None):
        try:
            from main import Face_Reconition_System

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Import error", f"Failed to open main app:\n{e}")
            return
        
        for widget in self.root.winfo_children():
            widget.destroy()

        
        if user_role == "Teacher":
            Face_Reconition_System(self.root, authenticated=True, user_role="Teacher", username=username)
        else:
            Face_Reconition_System(self.root, authenticated=True, user_role="Student",
                                   username=username, student_id=student_id)
            
    
    def show_welcome_animation(self, name, callback, width=450, height=120, hold_ms=900):
        try:
            top = tk.Toplevel(self.root)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.lift()

            ws = self.root.winfo_screenwidth()
            hs = self.root.winfo_screenheight()

# PERFECT CENTER
            x = (ws // 2) - (width // 2)
            y = (hs // 2) - (height // 2)

            top.geometry(f"{width}x{height}+{x}+{y}")


            transparent_key = "#123456"
            transparent_supported = False

            try:
                top.configure(bg=transparent_key)
                top.wm_attributes("-transparentcolor", transparent_key)
                transparent_supported = True
            except Exception:
                top.configure(bg=self.bg_color)

            label_bg = transparent_key if transparent_supported else top.cget("bg")

            welcome_lbl = tk.Label(
                top, text="Welcome", font=("Segoe UI", 20, "bold"),
                fg="red", bg=label_bg
            )
            welcome_lbl.place(relx=0.5, rely=0.28, anchor="center")

            name_lbl = tk.Label(
                top, text=str(name), font=("Segoe UI", 19, "bold"),
                fg="#000", bg=label_bg
            )
            name_lbl.place(relx=0.5, rely=0.68, anchor="center")

            try: top.attributes("-alpha", 0.0)
            except: pass

            def fade_in(step=0):
                try: top.attributes("-alpha", min(1, step / 10))
                except: pass
                if step < 10:
                    top.after(30, lambda: fade_in(step+1))
                else:
                    top.after(hold_ms, lambda: fade_out(10))

            def fade_out(step):
                try: top.attributes("-alpha", max(0, step / 10))
                except: pass
                if step > 0:
                    top.after(30, lambda: fade_out(step-1))
                else:
                    try: top.destroy()
                    except: pass
                    callback()

            fade_in()

        except Exception:
            traceback.print_exc()
            callback()


if __name__ == "__main__":
    root = ctk.CTk()
    app = User_Authentication(root)
    root.mainloop()
