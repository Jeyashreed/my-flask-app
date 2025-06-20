from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
print("DB_USER:", os.getenv("DB_USER"))
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))


app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Global DB connection
db = None
cursor = None

def connect_db():
    global db, cursor
    try:
        db = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=3306,
            use_pure=True
        )
        cursor = db.cursor()
        print("✅ Connected to database.")
    except mysql.connector.Error as err:
        print("❌ Database connection error:", err)

        cursor = db.cursor()
        print("✅ Connected to database.")
    except mysql.connector.Error as err:
        print("❌ Database connection error:", err)

# Initial DB connection
connect_db()

# Send email
def send_confirmation_email(to_email, user_name):
    sender_email = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    msg = EmailMessage()
    msg['Subject'] = "Welcome!"
    msg['From'] = sender_email
    msg['To'] = to_email
    msg.set_content(f"Hi {user_name},\n\nThank you for signing up!")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.send_message(msg)
    except Exception as e:
        print("❌ Email sending failed:", e)

@app.route('/')
def home():
    return redirect('/signup')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if db is None or not db.is_connected():
            connect_db()
            if db is None or not db.is_connected():
                flash("Database not connected.")
                return redirect('/signup')

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cpassword = request.form['cpassword']

        if password != cpassword:
            flash("Passwords do not match.")
            return redirect('/signup')

        hashed = generate_password_hash(password)

        try:
            cursor.execute("""
                INSERT INTO USERS (USERNAME, EMAIL, PASSWORD)
                VALUES (%s, %s, %s)
            """, (username, email, hashed))
            db.commit()
            send_confirmation_email(email, username)
            flash("Signup successful. Please log in.")
            return redirect('/login')
        except mysql.connector.IntegrityError:
            flash("Email already exists.")
            return redirect('/signup')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if db is None or not db.is_connected():
            connect_db()
            if db is None or not db.is_connected():
                flash("Database not connected.")
                return redirect('/login')

        cursor.execute("SELECT USERNAME, PASSWORD FROM USERS WHERE EMAIL = %s", (email,))
        user = cursor.fetchone()

        if user:
            username, hashed = user
            if check_password_hash(hashed, password):
                session['user_name'] = username
                session['email'] = email
                return redirect('/welcome')

        flash("Invalid email or password.")
        return redirect('/login')

    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'email' not in session:
        return redirect('/login')
    return render_template('welcome.html', username=session['user_name'])

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/login')

    if db is None or not db.is_connected():
        connect_db()

    cursor.execute("""
        SELECT ROLL_NO, NAME, CLASS 
        FROM STUDENTS 
        WHERE IS_ACTIVE = 1
    """)
    students = cursor.fetchall()
    return render_template('dashboard.html', username=session['user_name'], students=students)

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'email' not in session:
        return redirect('/login')

    roll_no = request.form['roll_no']
    name = request.form['name']
    student_class = request.form['student_class']
    created_by = session['email']
    created_on = datetime.now()

    try:
        cursor.execute("""
            INSERT INTO STUDENTS (ROLL_NO, NAME, CLASS, CREATED_BY, CREATED_ON)
            VALUES (%s, %s, %s, %s, %s)
        """, (roll_no, name, student_class, created_by, created_on))
        db.commit()
        flash("Student added successfully.")
    except mysql.connector.Error as e:
        flash(f"DB Error: {e}")
    return redirect('/dashboard')

@app.route('/edit_student/<roll_no>', methods=['POST'])
def edit_student(roll_no):
    if 'email' not in session:
        return redirect('/login')

    new_name = request.form['name']
    new_class = request.form['student_class']

    cursor.execute("""
        SELECT NAME, CLASS FROM STUDENTS 
        WHERE ROLL_NO = %s AND CREATED_BY = %s AND IS_ACTIVE = 1
    """, (roll_no, session['email']))
    result = cursor.fetchone()

    if not result:
        flash("Student not found.")
        return redirect('/dashboard')

    current_name, current_class = result
    updated_by = session['email']
    updated_on = datetime.now() if new_name != current_name or new_class != current_class else None

    cursor.execute("""
        UPDATE STUDENTS 
        SET NAME = %s, CLASS = %s, UPDATED_BY = %s, UPDATED_ON = %s
        WHERE ROLL_NO = %s
    """, (new_name, new_class, updated_by, updated_on, roll_no))
    db.commit()

    flash("Student record updated." if updated_on else "No changes detected.")
    return redirect('/dashboard')

@app.route('/delete_student/<roll_no>')
def delete_student(roll_no):
    if 'email' not in session:
        return redirect('/login')

    cursor.execute("""
        UPDATE STUDENTS 
        SET IS_ACTIVE = 0, UPDATED_BY = %s, UPDATED_ON = %s
        WHERE ROLL_NO = %s AND CREATED_BY = %s
    """, (session['email'], datetime.now(), roll_no, session['email']))
    db.commit()
    flash("Student deleted successfully.")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
