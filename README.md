The Facial Recognition Attendance System is an AI–driven platform that automates attendance using live face detection and recognition.
It eliminates manual attendance, reduces proxy marking, and provides real-time tracking through a dedicated teacher dashboard and student attendance panel.
This system uses computer vision, machine learning, and database persistence to securely recognize faces and store attendance records.

✨ Features

Face Registration – Capture student faces and generate encoded data.

Real-Time Face Recognition – Detect and match faces via webcam.

Automatic Attendance Marking – Record date, time, and identity instantly.

Teacher Panel – Login access, attendance view, student management.

Student Panel – Secure login to check personal attendance history.

GUI-Based Interface – Simple buttons and visually clean layouts.

MySQL Storage – Attendance saved persistently for reporting.

Encoding Accuracy – Uses machine-learning embeddings for matching.

🧑‍🏫 Teacher Functions

✔ Login securely
✔ Register student records and capture images
✔ Start recognition mode to record attendance
✔ View daily/monthly attendance logs
✔ Manage/edit student entries

🎓 Student Functions

✔ Login to student dashboard
✔ View personal attendance history
✔ Receive real-time recognition confirmation

Students cannot change or delete attendance — they only view their records.

🛠 Tech Stack
📌 Backend & AI

Python

OpenCV

face_recognition (dlib encoding)

MySQL database

JSON for data storage

📌 GUI

CustomTkinter (dark-themed UI)

📂 Project Structure
Facial-Recognition-Attendance-System/
│
├── main.py                     # Application entry point
│
├── gui/                        # GUI screens (Login, Teacher, Student)
│   ├── login_ui.py
│   ├── teacher_dashboard.py
│   ├── student_panel.py
│
├── database/                   # Data logic & JSON files
│   ├── student.json
│   ├── db_connect.py
│
├── encodings/                  # Encoded face data
│   ├── student_encodings.dat
│
├── images/                     # Captured student face photos
│
└── README.md                   # Project documentation

🔧 How to Run Locally
🔹 Step 1 — Extract Project Folder

Open your project folder.

🔹 Step 2 — Install Dependencies
pip install opencv-python
pip install face_recognition
pip install customtkinter
pip install mysql-connector-python

🔹 Step 3 — Setup MySQL Database

Create a database:

CREATE DATABASE attendance_system;


Update database credentials inside project files.

🔹 Step 4 — Run the Project
python main.py

📌 Recognition Workflow

Teacher registers a student and captures face samples.

System generates face encodings.

Webcam scans faces in attendance mode.

System compares features → identifies match.

Attendance logs saved into database.

📊 Outputs

✔ Attendance stored as:

Student_Name | Student_ID | Date | Time


✔ Dashboard view
✔ Student attendance screen
✔ Recognition confirmation UI

🌟 Advantages

Fully contactless

Eliminates proxy attendance

Fast and accurate

Saves teacher time

Easy reporting

🔮 Future Enhancements

✨ Mobile app
✨ Mask recognition support
✨ Anti-spoof liveness detection
✨ Cloud data sync
✨ Notification alerts
