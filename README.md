📘 AI-Powered Facial Recognition Attendance System

A complete attendance management system using AI face recognition, CustomTkinter UI, and MySQL database, designed for schools, colleges, and institutions.

🚀 Overview

This project is an advanced end-to-end Facial Recognition Attendance System built using:

Python

OpenCV

face_recognition (dlib)

CustomTkinter (Modern UI)

MySQL Database

Matplotlib (Graphs & Analytics)

It offers separate dashboards for Students and Teachers, real-time attendance tracking, visual analytics, and a fully functional authentication system.

⭐ Features

🧑‍🎓 Student Features:
Login using username & password

Mark attendance using AI face recognition

View personal attendance history

Real-time attendance graph

Warning messages from teacher

Profile page (view-only)

👨‍🏫 Teacher Features:
Full dashboard with analytics

Add / Edit / Delete students

View attendance records (search by name or reg no.)

Send warning messages to students

Real-time CSV watcher auto-updates KPIs

Detailed daily/student-wise attendance graph

Teacher profile page (edit name, email, mobile, photo)

⚙ Technical Highlights

Smart CSV attendance parser

Supports multiple date formats

Auto username normalization

Modern UI using CustomTkinter

MySQL-based authentication & student management

Scrollable dashboards & pages

Profile photo upload/removal

🗂️ Folder Structure (Recommended)
📦 facial-recognition-attendance-system
 ┣ 📁 profile_images/
 ┣ 📁 models/                (if you store face encodings/dlib models)
 ┣ 📄 main.py
 ┣ 📄 student.py
 ┣ 📄 attendance.py
 ┣ 📄 User_Authentication.py
 ┣ 📄 view_attendance.py
 ┣ 📄 db_connection.py
 ┣ 📄 warnings.json          (auto-created)
 ┣ 📄 students.json          (student list)
 ┣ 📄 profiles.json          (teacher/student profiles)
 ┣ 📄 Attendance.csv         (attendance saved here)
 ┣ 📄 requirements.txt
 ┗ 📄 README.md



⚠ If face_recognition fails
Install CMake and Visual Studio Build Tools (Windows).

🗄️ MySQL Setup
Create Database + User

Run this in MySQL Workbench:

CREATE DATABASE IF NOT EXISTS face_attendance;

CREATE USER IF NOT EXISTS 'pythonuser'@'localhost'
IDENTIFIED BY '12345';

GRANT ALL PRIVILEGES ON face_attendance.* TO 'pythonuser'@'localhost';
FLUSH PRIVILEGES;

Import Student Table

Run:

source fix_students_complete.sql;

▶️ How to Run
python main.py

Application Flow:

Login page appears

Student → Attendance Dashboard

Teacher → Full Management Dashboard

Face recognition window opens when marking attendance

📸 Screenshots

(You can add your own screenshots here)

📚 Tech Used

Python

CustomTkinter

OpenCV

dlib / face_recognition

MySQL

Matplotlib

🤝 Contributing

Pull requests are welcome.
For major changes, open an issue first to discuss improvements.

📝 License

This project is free to use for educational purposes.
