from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

db_config = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", ""),
    'database': os.getenv("DB_NAME", "library_attendance")
}

@app.route('/api/library/exit', methods=['POST'])
def generate_library_exit_qr():
    roll_no = request.json.get('roll_no')

    if not roll_no:
        return jsonify({'error': 'roll_no is required'}), 400

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch student by roll_no
        cursor.execute("SELECT * FROM Students WHERE roll_no = %s", (roll_no,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        student_id = student['student_id']
        current_time = datetime.now()

        # Generate QR code image data
        qr_data = f"{roll_no}-library-exit-{current_time.isoformat()}"
        qr = qrcode.make(qr_data)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_image = buffer.getvalue()

        # Find latest QRLog entry for this student
        cursor.execute("""
            SELECT qr_id FROM QRLog
            WHERE student_id = %s
            ORDER BY generated_at DESC LIMIT 1
        """, (student_id,))
        latest_qr = cursor.fetchone()

        if latest_qr:
            qr_id = latest_qr['qr_id']
            # Update QRLog with the new library QR image
            cursor.execute("""
                UPDATE QRLog SET library_qr_image = %s WHERE qr_id = %s
            """, (qr_image, qr_id))
        else:
            # If no QRLog entry, create one (optional)
            cursor.execute("""
                INSERT INTO QRLog (student_id, status, qr_image)
                VALUES (%s, %s, %s)
            """, (student_id, 'library_exit', qr_image))
            qr_id = cursor.lastrowid

        # Check if an open LibraryLogs record exists (out_time IS NULL)
        cursor.execute("""
            SELECT log_id FROM LibraryLogs
            WHERE student_id = %s AND out_time IS NULL
            ORDER BY in_time DESC LIMIT 1
        """, (student_id,))
        open_log = cursor.fetchone()

        if open_log:
            # Update existing log with out_time and qr_id
            cursor.execute("""
                UPDATE LibraryLogs
                SET out_time = %s, qr_id = %s
                WHERE log_id = %s
            """, (current_time, qr_id, open_log['log_id']))
        else:
            # Insert new LibraryLogs record with out_time and qr_id
            cursor.execute("""
                INSERT INTO LibraryLogs (student_id, qr_id, out_time)
                VALUES (%s, %s, %s)
            """, (student_id, qr_id, current_time))

        # Commit changes
        conn.commit()

        # Return success response with base64 QR code image and exit time
        return jsonify({
            'message': 'Library exit QR generated and LibraryLogs updated successfully',
            'name': student['name'],
            'roll_no': student['roll_no'],
            'phone_number': student['phone_number'],
            'out_time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
            'qr_image': "data:image/png;base64," + base64.b64encode(qr_image).decode()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5006)
