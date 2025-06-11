from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
from datetime import datetime, timedelta
import base64
import qrcode
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", ""),
    'database': os.getenv("DB_NAME", "library_attendance")
}

# Endpoint to fetch student info
@app.route('/api/hostel/student-info/<roll_no>', methods=['GET'])
def get_student_info(roll_no):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT student_id, name, roll_no, hostel_name, room_number, phone_number, photo
            FROM Students
            WHERE roll_no = %s
        """
        cursor.execute(query, (roll_no,))
        student = cursor.fetchone()

        if not student:
            return jsonify({"error": "Student not found"}), 404

        # Convert photo blob to base64
        if student.get('photo'):
            photo_base64 = base64.b64encode(student['photo']).decode('utf-8')
            student['photo'] = f"data:image/jpeg;base64,{photo_base64}"
        else:
            student['photo'] = None

        return jsonify(student)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

# Endpoint to generate QR and save to database
@app.route('/api/hostel/generate-qr', methods=['POST'])
def generate_qr():
    data = request.json
    roll_no = data.get("roll_no")

    if not roll_no:
        return jsonify({"error": "Roll number is required"}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Get student_id by roll_no
        cursor.execute("SELECT student_id FROM Students WHERE roll_no = %s", (roll_no,))
        student = cursor.fetchone()
        if not student:
            return jsonify({"error": "Student not found"}), 404

        student_id = student['student_id']

        # Use current time minus 2 hours
        out_time = datetime.now()

        # QR code content
        qr_text = f"StudentID: {student_id} | Roll: {roll_no} | Out: {out_time.strftime('%Y-%m-%d %H:%M:%S')}"
        qr_img = qrcode.make(qr_text)
        img_bytes = io.BytesIO()
        qr_img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        # Save to QRLog table
        insert_qr = """
            INSERT INTO QRLog (student_id, out_time, status, qr_image)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_qr, (student_id, out_time, 'Generated', img_bytes))
        conn.commit()

        # Return QR image and out_time to frontend
        qr_base64 = base64.b64encode(img_bytes).decode('utf-8')
        return jsonify({
            "message": "QR generated successfully",
            "qr_image_base64": qr_base64,
            "out_time": out_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
