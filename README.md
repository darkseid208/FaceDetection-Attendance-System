# 🎓Facial Recognition Attendance System

This project is an AI-powered automated attendance system that replaces traditional manual roll-calling with live facial recognition. It uses webcam-based face detection, generates face encodings, identifies individuals, and records attendance with timestamps.

## Project Overview
The system provides two separate dashboards: one for teachers and one for students.  
Teachers can manage all students, capture faces, train recognition data, and view attendance logs.  
Students can log in to track their attendance progress via graphs and detailed statistics.

The system automatically detects faces using the webcam, compares them with the trained encodings, and marks attendance instantly.

## Features

- Face Registration: Capture student faces and create encoded training data
- Real-Time Face Recognition: Detect and match faces through webcam
- Automatic Attendance Marking: Log student name, date, and time
- Teacher Dashboard: Manage students, view reports, track attendance
- Student Dashboard: Personal attendance tracking with graphs
- Manual Attendance Control for Teachers
- Attendance Export to CSV
- Login Authentication System for Students and Teachers
- Clean and responsive GUI built with CustomTkinter
- SQLite, JSON, and CSV data storage support

## Technologies Used

- Python 3
- Tkinter and CustomTkinter (GUI)
- OpenCV for webcam video capture
- face_recognition (dlib-based face detection and encoding)
- SQLite databases (students.db, users.db)
- CSV files (attendance.csv)
- JSON files (profiles.json, students.json)
- PIL for image processing
- Matplotlib for attendance graphs

## Facial Recognition Attendance System/
│
├── main.py (Main application with dashboards)
├── User_Authentication.py (Login system)
├── capture_all_students.py (Capture images for training)
├── train_data.py (Generates facial encodings and creates train.pkl)
├── attendance.py (Attendance marking logic)
├── student.py (Student data model)
├── view_attendance.py (Graph rendering)
│
├── profiles.json (All user profiles)
├── students.json (Student details)
├── warnings.json (Warning information)
├── attendance.csv (Attendance log)
├── students_local.csv (Local backup of students)
├── train.pkl (Trained facial encodings)
│
├── students.db (Student database)
├── users.db (User login database)
│
├── dataset/ (Captured images for training)
├── known_faces/ (Encoded face data)
├── certified_faces/ (Verified face images)
├── profile_images/ (Profile photos)
├── media/ (UI images and icons)
├── images/ (Misc images)
├── exports/ (Exported reports)
│
└── venv/ (Virtual environment)

## How the System Works

### 1. Face Capture
The teacher captures multiple images of each student using the webcam.  
These images are saved inside the dataset folder sorted by student ID.

### 2. Training Encodings
The train_data.py script:
- Reads all captured images
- Detects faces
- Generates encoding vectors
- Stores them in train.pkl

### 3. Real-Time Recognition
During attendance:
- Webcam captures live video frames
- face_recognition extracts face encodings
- System compares them with known encodings
- When a match is found, attendance is recorded automatically

### 4. Attendance Logging
Attendance is stored inside:
- attendance.csv
- students.db (optional)
- JSON files for dashboard display

## D0atabase Structure

### users.db
Stores login details:
- username
- password
- role (Teacher or Student)

### students.db
Stores student information:
- student_id
- full_name
- department
- course
- email
- phone
- profile_pic

## 🧑‍🏫 Teacher Features

Teachers have full control over the system. Features include:

- 📸 Capture student faces for training
- 🧠 Train the facial recognition model (train.pkl)
- 👥 Add, edit, and manage student profiles
- 🎥 Start real-time attendance scanning
- 📊 View attendance graphs and analytics
- ✏️ Manually mark or correct attendance
- 📅 Access daily, monthly, and overall attendance reports
- 📤 Export attendance data to CSV
- 📝 View recent activity logs
- ⚠️ Manage low-attendance warnings

## 👨‍🎓 Student Features

Students can access personal attendance information. Features include:

- 📅 View daily and monthly attendance
- 📈 See attendance percentage progress
- 🧾 Access complete attendance history
- 📊 View attendance graph (line/bar chart)
- 👤 View personal profile information
- 🔐 Secure login to student dashboard
- ⚠️ Track warnings for low attendance

## Future Enhancements

- Cloud database integration
- Mobile app for students
- Improved UI with animations
- Notification system for low attendance
- Admin panel with full system controls



This project is for educational and personal use only.

