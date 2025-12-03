Project Overview

The Facial Recognition Attendance System is an AI-powered desktop application that replaces manual attendance-taking with automated face recognition.
It identifies individuals using a webcam and logs attendance automatically in a secure database with date and time.

Ideal for schools, colleges, workplaces, and biometric research.

🔧 Technology Stack
Component	Technology
Programming Language	Python
Face Detection & Recognition	OpenCV + face_recognition (dlib)
GUI	CustomTkinter
Database	MySQL
Data Handling	JSON
⭐ Key Features

✔ Face detection & recognition
✔ Live camera-based attendance marking
✔ Student enrollment interface
✔ Teacher dashboards and analytics
✔ Secure database-backed authentication
✔ Modern dark-themed GUI

🧑‍🏫 Teacher-Side Functionality

Teachers can:

🔹 1. Login to Teacher Panel

Secure login using MySQL authentication.

🔹 2. Register Students

Add student ID and name

Capture face images

Generate and store face encodings

🔹 3. Take Attendance

Start recognition mode

System identifies students automatically

Attendance recorded without manual marking

🔹 4. View Attendance Reports

Daily, monthly, or filtered logs

Performance views

🔹 5. Manage Students

Edit information

Delete or re-register faces

🎓 Student-Side Functionality

Students can:

🔹 1. View Attendance Records

Check personal attendance history.

🔹 2. Receive Real-Time Attendance Confirmation

When recognized, system acknowledges attendance.

🔹 3. View Profile Details

Student information and recognition status.

Students cannot modify attendance — only view it.
Teachers/admin maintain full control.

🧠 System Flow
Student Registration → Face Encoding → Live Recognition → Attendance Stored in MySQL → Report Display

📂 Project Folder Structure
📦 Facial Recognition Attendance System
 ┣ 📂 images/                # Face datasets
 ┣ 📂 encodings/             # Encoded facial data
 ┣ 📂 gui/                   # UI screens (teacher & student)
 ┣ 📂 database/              # Logic + JSON records
 ┣ 📜 main.py                # Entry point
 ┣ 📜 README.md              # Documentation


(Folder names may vary slightly based on your project version)

📥 Installation & Setup Guide
1️⃣ Extract the project folder
2️⃣ Install required Python libraries manually
pip install opencv-python
pip install face_recognition
pip install customtkinter
pip install mysql-connector-python


dlib may require precompiled binaries based on OS.

3️⃣ Configure MySQL Database
CREATE DATABASE attendance_system;


Update credentials inside the project wherever database connection exists.

4️⃣ Run the application
python main.py

📊 Output Format

Attendance is stored in the format:

Student ID | Student Name | Date | Time


Teachers can view summary dashboards, and students can view personal logs.

💡 Benefits

✨ Fast and contactless attendance
✨ Eliminates proxy attendance
✨ User-friendly graphical interface
✨ Accurate recognition with encoding models

🔮 Future Enhancements

🔹 Anti-spoofing / liveness detection
🔹 Mobile app or cloud support
🔹 Mask-enabled face recognition
🔹 SMS/email notification system
