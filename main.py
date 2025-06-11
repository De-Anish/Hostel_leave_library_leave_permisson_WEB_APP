from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# MySQL connection config
db_config = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", ""),
    'database': os.getenv("DB_NAME", "library_attendance")
}

@app.route('/api/admin/add-student', methods=['POST'])
def add_student():
    conn = None
    cursor = None
    try:
        name = request.form['name']
        roll_no = request.form['roll_no']
        email = request.form['email']
        phone_number = request.form.get('phone_number')  # New field
        hostel_name = request.form['hostel_name']
        room_number = request.form['room_number']
        photo_file = request.files.get('photo')

        if not photo_file:
            return jsonify({'error': 'Photo file is required'}), 400

        photo_data = photo_file.read()

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = """
        INSERT INTO Students (name, roll_no, email, phone_number, hostel_name, room_number, photo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (name, roll_no, email, phone_number, hostel_name, room_number, photo_data))
        conn.commit()

        return jsonify({'message': 'Student added successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
