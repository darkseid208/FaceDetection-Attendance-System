✨ Overview

The AI Facial Recognition Attendance System is a professional-grade application built with:

🧠 AI-powered face recognition (dlib + face_recognition)

🎨 Modern CustomTkinter GUI

🗄 MySQL database with secure login

📊 Beautiful dashboards and analytics

🧑‍🏫 Separate portals for Teachers and Students

📷 Real-time webcam-based attendance

This project is perfect for college submissions, portfolio projects, and real institutional use.

🚀 Features
👨‍🏫 Teacher Portal

📌 Add / Edit / Delete Students

🔍 Search attendance by date, name, or ID

📣 Send warnings to students

📈 Student-wise attendance charts

🧾 Attendance history viewer

👤 Editable profile page with image upload

🧩 Dynamic dashboards & KPIs

🧑‍🎓 Student Portal

🤳 AI Facial Attendance Marking

📄 View attendance history

📊 Attendance progress (circular graph)

⚠ Receive warnings from teachers

👁 Student profile viewer

⚙ System Highlights

⚡ Real-time face recognition

🔄 Auto-updating CSV + JSON data

🧵 Multi-threaded camera handling

🎛 Smooth animations & modern UI

🧩 Clean modular architecture

🏗 Project Architecture
📦 Facial-Recognition-Attendance-System
 ┣ 📁 profile_images/
 ┣ 📁 models/
 ┣ 📄 main.py
 ┣ 📄 student.py
 ┣ 📄 attendance.py
 ┣ 📄 view_attendance.py
 ┣ 📄 User_Authentication.py
 ┣ 📄 db_connection.py
 ┣ 📄 warnings.json
 ┣ 📄 students.json
 ┣ 📄 Attendance.csv
 ┣ 📄 requirements.txt
 ┗ 📄 README.md

📸 Screenshots (Add yours here)
🔐 Login Page

🏠 Dashboard

🤳 Face Recognition

(You can upload real screenshots later and I will embed them beautifully.)

🛠 Installation
1️⃣ Install Dependencies
pip install opencv-python
pip install face_recognition
pip install customtkinter
pip install mysql-connector-python
pip install pillow
pip install matplotlib

🗄 MySQL Setup
CREATE DATABASE face_attendance;

CREATE USER 'pythonuser'@'localhost' IDENTIFIED BY '12345';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'pythonuser'@'localhost';
FLUSH PRIVILEGES;


Import student structure:

source fix_students_complete.sql;

▶️ Run the Application
python main.py

📊 Tech Stack
Component	Technology
Frontend GUI	CustomTkinter
Backend	Python
AI Engine	face_recognition (dlib), OpenCV
Database	MySQL
Graphs	Matplotlib
Storage	CSV + JSON + MySQL
