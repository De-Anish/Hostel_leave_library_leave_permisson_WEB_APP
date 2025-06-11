
# 📚 Library Attendance Management System

A Flask-based backend system to manage student attendance using QR codes. It includes three main portals: **Admin**, **Warden**, and **Library**, and interacts with a central MySQL database.

---

## 📁 Project Structure

```bash
.
├── main.py                        # Admin portal: Add student and store photo
├── warden_api.py                 # Warden portal: Get student info, generate QR for hostel exit
├── liberary_side_management.py   # Library portal: Generate QR for library exit, log activity
├── .env                          # Environment variables (used by all apps)
├── used_mysql_query.sql          # MySQL schema and queries
├── requirements.txt              # Required Python packages
└── README.md                     # Documentation
```

---

## 🔧 Requirements

- Python 3.7+
- MySQL Server
- Virtual environment (optional but recommended)

Install required packages:

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a file named `.env` in the project root directory and add the following content:

```env
# MySQL Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=Your_pass
DB_NAME=library_attendance

# SMTP Email Configuration (optional for email alerts)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=Sender_email
EMAIL_PASSWORD=Smtp_password
```

> ⚠️ Make sure you replace these values with your actual credentials.  
> If using Gmail with 2FA, you must generate and use an **App Password**.

---

## 🗃️ Database Setup

Run the SQL statements provided in [`used_mysql_query.sql`](./used_mysql_query.sql) to create the necessary tables in your MySQL server.

```sql
-- Example tables:
CREATE DATABASE IF NOT EXISTS library_attendance;

USE library_attendance;

CREATE TABLE Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    roll_no VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    phone_number VARCHAR(20),
    hostel_name VARCHAR(100),
    room_number VARCHAR(50),
    photo LONGBLOB
);

CREATE TABLE QRLog (
    qr_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    out_time DATETIME,
    status VARCHAR(50),
    qr_image LONGBLOB,
    library_qr_image LONGBLOB,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
);

CREATE TABLE LibraryLogs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    qr_id INT,
    in_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    out_time DATETIME,
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (qr_id) REFERENCES QRLog(qr_id)
);
```

---

## 🌐 API Endpoints

### 🔸 Admin Portal (`main.py`)
- `POST /api/admin/add-student`  
  Add a new student with form-data including a photo.

### 🔸 Warden Portal (`warden_api.py`)
- `GET /api/hostel/student-info/<roll_no>`  
  Fetch student info using roll number.

- `POST /api/hostel/generate-qr`  
  Generate a QR code when student exits the hostel.  
  **JSON Body:**
  ```json
  {
    "roll_no": "123456"
  }
  ```

### 🔸 Library Portal (`liberary_side_management.py`)
- `POST /api/library/exit`  
  Generate library exit QR, update `LibraryLogs`.  
  **JSON Body:**
  ```json
  {
    "roll_no": "123456"
  }
  ```

---

## 🧪 Sample Response

```json
{
  "message": "QR generated successfully",
  "qr_image_base64": "data:image/png;base64,...",
  "out_time": "2025-06-12 12:30:00"
}
```

---

## ▶️ Running the Apps

Start each Flask app in separate terminals (or ports):

```bash
# Admin
python main.py

# Warden (on port 5001)
python warden_api.py

# Library (on port 5006)
python liberary_side_management.py
```

---

## ✅ Notes

- All apps share the same `.env` configuration.
- SQL logic is isolated in `used_mysql_query.sql` for portability.
- Ensure CORS is enabled if connecting with a frontend (already handled via `flask-cors`).

---

## 📦 Python Requirements

**`requirements.txt`**
```
Flask
flask-cors
mysql-connector-python
python-dotenv
qrcode[pil]
Pillow
pytz
```

Install via:

```bash
pip install -r requirements.txt
```

---

## 📌 TODO (Optional Enhancements)

- ✅ Email alerts on QR generation using SMTP
- 🔒 Admin/Warden authentication
- 📊 Frontend dashboard with QR scanner
- 🎥 Face recognition for student verification

---

## 👨‍💻 Author

Made by Anish De  
CSE Student | QTel Diversity Program
