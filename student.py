from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import qrcode
import io
import random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import base64

load_dotenv()

app = Flask(__name__)
CORS(app)

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'library_attendance')
}

def send_otp_email(to_email, otp):
    smtp_host = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('EMAIL_SENDER')
    smtp_pass = os.getenv('EMAIL_PASSWORD')

    subject = "Your OTP for Library Login"
    body = f"Your OTP is: {otp}. It expires in 5 minutes."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

@app.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Students WHERE email = %s", (email,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Student not found with this email'}), 404

        otp = f"{random.randint(100000, 999999)}"
        expiry = datetime.now() + timedelta(minutes=5)

        cursor.execute("""
            INSERT INTO StudentOTP (student_id, otp, expiry)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE otp=%s, expiry=%s
        """, (student['student_id'], otp, expiry, otp, expiry))
        conn.commit()

        cursor.close()
        conn.close()

        if send_otp_email(student['email'], otp):
            return jsonify({'message': 'OTP sent to your email'}), 200
        else:
            return jsonify({'error': 'Failed to send OTP email'}), 500

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return jsonify({'error': 'Email and OTP required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Students WHERE email = %s", (email,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Student not found with this email'}), 404

        cursor.execute("""
            SELECT * FROM StudentOTP 
            WHERE student_id = %s AND otp = %s AND expiry > NOW()
        """, (student['student_id'], otp))
        otp_entry = cursor.fetchone()

        if not otp_entry:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid or expired OTP'}), 401

        # Get latest out_time for hostel
        cursor.execute("SELECT out_time FROM QRLog WHERE student_id = %s ORDER BY qr_id DESC LIMIT 1", (student['student_id'],))
        hostel_log = cursor.fetchone()
        hostel_out_time = hostel_log['out_time'].strftime('%Y-%m-%d %H:%M:%S') if hostel_log and hostel_log['out_time'] else 'N/A'

        # Generate hostel QR with name, roll, hostel out time
        qr_data_hostel = f"Name: {student['name']}\nRoll No: {student['roll_no']}\nHostel Out Time: {hostel_out_time}"
        qr_hostel_img = qrcode.make(qr_data_hostel)
        hostel_byte_arr = io.BytesIO()
        qr_hostel_img.save(hostel_byte_arr, format='PNG')
        hostel_qr_bytes = hostel_byte_arr.getvalue()

        cursor.execute(
            "INSERT INTO QRLog (student_id, status, qr_image, out_time) VALUES (%s, %s, %s, %s)",
            (student['student_id'], 'generated', hostel_qr_bytes, hostel_log['out_time'] if hostel_log else None)
        )
        conn.commit()

        # Get latest out_time for library
        cursor.execute("SELECT out_time FROM LibraryLogs WHERE student_id = %s ORDER BY log_id DESC LIMIT 1", (student['student_id'],))
        lib_log = cursor.fetchone()
        lib_out_time = lib_log['out_time'].strftime('%Y-%m-%d %H:%M:%S') if lib_log and lib_log['out_time'] else 'N/A'

        # Generate library QR with name, roll, library out time
        qr_data_lib = f"Name: {student['name']}\nRoll No: {student['roll_no']}\nLibrary Out Time: {lib_out_time}"
        qr_lib_img = qrcode.make(qr_data_lib)
        lib_byte_arr = io.BytesIO()
        qr_lib_img.save(lib_byte_arr, format='PNG')
        lib_qr_bytes = lib_byte_arr.getvalue()

        # Encode for frontend
        qr_hostel_img_src = f"data:image/png;base64,{base64.b64encode(hostel_qr_bytes).decode('utf-8')}"
        qr_library_img_src = f"data:image/png;base64,{base64.b64encode(lib_qr_bytes).decode('utf-8')}"

        cursor.close()
        conn.close()

        student_info = {
            "name": student['name'],
            "roll_no": student['roll_no'],
            "email": student['email'],
            "hostel_name": student['hostel_name'],
            "room_number": student['room_number'],
            "phone_number": student['phone_number']
        }

        return jsonify({
            'student_info': student_info,
            'hostel_qr_code': qr_hostel_img_src,
            'library_qr_code': qr_library_img_src
        })

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

if __name__ == '__main__':
    app.run(port=5007, debug=True)
