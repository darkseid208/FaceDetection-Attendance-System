👨‍🏫 Facial Recognition Attendance System

The Facial Recognition Attendance System is an AI-powered automated attendance platform that replaces manual roll-calling with live facial recognition.
It identifies individuals via webcam, matches their stored facial encodings, and records attendance automatically with timestamp logging.

✨ Features

Face Registration – Capture student faces and generate encoded data

Real-Time Recognition – Detect and match faces through webcam

Automatic Attendance Marking – Logs name, date, time instantly

Teacher Dashboard – Reports, student management, attendance viewing

Student Login Panel – Personal attendance tracking

Clean GUI (CustomTkinter)

Secure MySQL Database Storage

🧑‍🏫 Teacher Functions

✔ Login authentication
✔ Register students with face data
✔ Start attendance detection
✔ View attendance logs
✔ Manage student data

🎓 Student Functions

✔ Login to student dashboard
✔ View personal attendance history
✔ Get real-time recognition status

Students cannot edit or remove attendance — only teachers can manage data.

🛠 Tech Stack
Backend & Core AI

Python

OpenCV

face_recognition / dlib

GUI

CustomTkinter

Database

MySQL

JSON files for local storage

📂 Project Structure (Markdown formatted)
Facial-Recognition-Attendance-System/
│
├── main.py                     # Application launcher
│
├── gui/                        # User interface screens
│   ├── login_ui.py
│   ├── teacher_dashboard.py
│   ├── student_panel.py
│
├── database/                   # DB logic + JSON records
│   ├── db_connect.py
│   ├── students.json
│
├── encodings/                  # Stored recognition data
│
├── images/                     # Face capture images
│
└── README.md                   # Documentation

🔧 How to Run Locally
Step 1: Extract Folder

Open the root project directory.

Step 2: Install required libraries
pip install opencv-python
pip install face_recognition
pip install customtkinter
pip install mysql-connector-python


Note: dlib installation depends on OS compatibility.

Step 3: Configure MySQL
CREATE DATABASE attendance_system;


Edit project files to update host/user/password.

Step 4: Run UI
python main.py

📌 Processing Workflow
Register Face → Encode → Webcam Recognition → Match → Attendance Stored → Report View

📊 Output Format
Student_ID | Student_Name | Date | Time


Displayed on teacher dashboard and student history panel.

⭐ Advantages

Fast automated attendance

Eliminates proxies

Easy retrieval and reporting

User-friendly UI

🔮 Future Enhancements

Mobile application support

Mask recognition

Cloud synchronization

Alert notifications

Anti-spoofing detection
