Project Overview

The Facial Recognition Attendance System is an AI-powered desktop application that replaces manual attendance-taking with automated face recognition.
It identifies individuals from webcam input and marks attendance automatically in a database with date and time.

This solution is suitable for schools, colleges, offices, and research projects.

🔧 Technology Stack
Component	Technology
Programming Language	Python
Face Detection & Recognition	OpenCV + face_recognition (dlib)
GUI	CustomTkinter
Database	MySQL
Data Handling	JSON (student records / settings)
⭐ Key Features

✔ Face detection & recognition
✔ Live camera-based attendance
✔ Student enrollment interface
✔ Teacher dashboard & analytics
✔ Automatic timestamp logging
✔ Database-backed authentication
✔ Modern dark-themed UI

🧑‍🏫 Teacher-Side Functionality

Teachers can:

🔹 1. Login to teacher panel

Secure credential validation using MySQL.

🔹 2. Register Students

Add new student name / ID

Capture face images

Store encodings for future recognition

🔹 3. Take Attendance

Launch camera window

System automatically matches faces

Attendance is marked without manual intervention

🔹 4. View Attendance Records

See daily/monthly logs

Analyze student performance

🔹 5. Manage Students

Edit details

Delete or re-register student

🎓 Student-Side Functionality

Students can:

🔹 1. Check Attendance Status

Open student panel

View personal attendance history

🔹 2. Live Attendance Confirmation

When camera recognizes their face

Pop-up notification confirms attendance

🔹 3. Profile Visibility

Student information (ID, name, face stored)

Students cannot edit or modify attendance — only view it.
All control remains with teachers/admin.

🧠 System Flow
Student Registration → Face Encoding → Recognition via Camera → Attendance Stored in MySQL → Dashboard View

📂 Project Folder Structure
📦 Facial Recognition Attendance System
 ┣ 📂 images/                # Face image datasets
 ┣ 📂 encodings/             # Face encoding files
 ┣ 📂 gui/                   # Teacher & Student UI screens
 ┣ 📂 database/              # MySQL interaction + JSON records
 ┣ 📜 main.py                # Application entry file
 ┣ 📜 README.md              # Documentation


(Folder names may vary slightly based on your version)

📥 Installation & Setup Guide
1️⃣ Extract the project folder
2️⃣ Install required Python libraries manually
pip install opencv-python
pip install face_recognition
pip install customtkinter
pip install mysql-connector-python


dlib backend may need prebuilt installer depending on your OS.

3️⃣ Create MySQL database
CREATE DATABASE attendance_system;


Update credentials in the project wherever database connection occurs.

4️⃣ Run the application
python main.py

📊 Output Format

Attendance is recorded as:

Student ID | Full Name | Date | Time


And can be viewed through teacher dashboard or student view panel.

💡 Benefits

✨ Secure and fast attendance
✨ Reduces proxy attendance
✨ Instructor-friendly dashboard
✨ Accurate recognition through encoding

🔮 Future Enhancements

🔸 Mobile App / Cloud Sync
🔸 Mask-supported recognition
🔸 Automatic messaging system
🔸 Liveness detection
