-- =====================================
-- Create Database
-- =====================================
CREATE DATABASE IF NOT EXISTS face_attendance;
USE face_attendance;

-- =====================================
-- Drop Existing Tables (optional, clean start)
-- =====================================
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS teachers;
DROP TABLE IF EXISTS students;

-- =====================================
-- Table: Teachers
-- =====================================
CREATE TABLE teachers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL
);

-- =====================================
-- Table: Students
-- =====================================
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL
);

-- =====================================
-- Table: Attendance
-- =====================================
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'Present',
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- =====================================
-- Insert Teacher Credential (Corrected)
-- =====================================
INSERT INTO teachers (username, password, full_name) VALUES
('teacher1', '1234', 'Arnav Mehta')
ON DUPLICATE KEY UPDATE username = username;

-- =====================================
-- Insert Student Credentials
-- =====================================
INSERT INTO students (student_id, username, password, full_name) VALUES
('S101', 'student1', '1234', 'Samir Prasad'),
('S102', 'student2', 'abcd', 'Sachin Prasad'),
('S103', 'student3', 'pass123', 'Anindita Bairagi'),
('S104', 'student4', '4321', 'Ahana Roy')
ON DUPLICATE KEY UPDATE student_id = student_id;

-- =====================================
-- View Data
-- =====================================
SELECT * FROM teachers;
SELECT * FROM students;
SELECT * FROM attendance;