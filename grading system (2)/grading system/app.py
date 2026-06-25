"""
Online Exam Grading System - Main Flask Application
Author: Auto-generated
Description: Full-stack exam system with student/admin roles, MCQ exams,
             auto-grading, malpractice detection, and result analytics.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import hashlib
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'exam_system_secret_key_2024'  # Change this in production

DATABASE = 'exam_system.db'

# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables and seed data."""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            attendance INTEGER NOT NULL DEFAULT 80
        )
    ''')

    # Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option1 TEXT NOT NULL,
            option2 TEXT NOT NULL,
            option3 TEXT NOT NULL,
            option4 TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            marks INTEGER NOT NULL DEFAULT 1,
            exam_id INTEGER DEFAULT 1
        )
    ''')

    # Exams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            time_limit INTEGER NOT NULL DEFAULT 30,
            total_marks INTEGER NOT NULL DEFAULT 100,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL DEFAULT 1,
            score INTEGER NOT NULL DEFAULT 0,
            total_marks INTEGER NOT NULL DEFAULT 100,
            percentage REAL NOT NULL DEFAULT 0,
            grade TEXT NOT NULL DEFAULT 'Fail',
            malpractice_flag INTEGER NOT NULL DEFAULT 0,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Malpractice logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS malpractice_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Seed admin account (admin@exam.com / admin123)
    admin_pass = hash_password('admin123')
    cursor.execute('''
        INSERT OR IGNORE INTO users (name, email, password, role, attendance)
        VALUES (?, ?, ?, ?, ?)
    ''', ('Administrator', 'admin@exam.com', admin_pass, 'admin', 100))

    # Seed default exam
    cursor.execute('''
        INSERT OR IGNORE INTO exams (id, title, description, time_limit, total_marks)
        VALUES (1, 'General Knowledge Test', 'A comprehensive MCQ-based test', 30, 100)
    ''')

    # Seed sample questions
    sample_questions = [
        ("What does CPU stand for?",
         "Central Processing Unit", "Central Program Unit",
         "Computer Personal Unit", "Central Processor Utility", 1, 10, 1),

        ("Which language is used for web front-end development?",
         "Python", "Java", "JavaScript", "C++", 3, 10, 1),

        ("What is the full form of HTML?",
         "Hyper Text Markup Language", "High Text Machine Language",
         "Hyperlink and Text Markup Language", "Home Tool Markup Language", 1, 10, 1),

        ("Which of the following is a Python web framework?",
         "Django", "Laravel", "Spring", "Express", 1, 10, 1),

        ("What does SQL stand for?",
         "Structured Query Language", "Simple Query Language",
         "Standard Query Logic", "Sequential Query Language", 1, 10, 1),

        ("What is the default port for HTTP?",
         "443", "8080", "80", "21", 3, 10, 1),

        ("Which data structure uses LIFO?",
         "Queue", "Stack", "Array", "Linked List", 2, 10, 1),

        ("What does RAM stand for?",
         "Read Access Memory", "Random Access Memory",
         "Run Access Memory", "Rapid Access Memory", 2, 10, 1),

        ("Which company created Python?",
         "Microsoft", "Google", "Guido van Rossum / CWI", "Apple", 3, 10, 1),

        ("What is 2^10?",
         "512", "1024", "2048", "256", 2, 10, 1),
    ]

    # Only insert if no questions exist for exam 1
    cursor.execute('SELECT COUNT(*) FROM questions WHERE exam_id = 1')
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO questions (question, option1, option2, option3, option4, correct_answer, marks, exam_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_questions)

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully!")

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def get_grade(percentage):
    """Return grade based on percentage."""
    if percentage >= 90:
        return 'A'
    elif percentage >= 75:
        return 'B'
    elif percentage >= 50:
        return 'C'
    else:
        return 'Fail'

def login_required(f):
    """Decorator: require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    """Decorator: require student role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator: require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# ROUTES: GENERAL
# ─────────────────────────────────────────────

@app.route('/')
def index():
    """Landing page."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for both students and admins."""
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND password = ?',
            (email, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration route."""
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        if not all([name, email, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        try:
            conn = get_db()
            # Assign random attendance between 60-100 for demo
            import random
            attendance = random.randint(60, 100)
            conn.execute(
                'INSERT INTO users (name, email, password, role, attendance) VALUES (?, ?, ?, ?, ?)',
                (name, email, hash_password(password), 'student', attendance)
            )
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered. Please login.', 'danger')

    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout and clear session."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
# ROUTES: STUDENT
# ─────────────────────────────────────────────

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    """Student dashboard with attendance and past results."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    results = conn.execute(
        '''SELECT r.*, e.title as exam_title
           FROM results r
           JOIN exams e ON r.exam_id = e.id
           WHERE r.user_id = ?
           ORDER BY r.submitted_at DESC''',
        (session['user_id'],)
    ).fetchall()
    exam = conn.execute('SELECT * FROM exams WHERE is_active = 1 LIMIT 1').fetchone()
    conn.close()

    can_take_exam = user['attendance'] >= 75
    return render_template('student_dashboard.html',
                           user=user,
                           results=results,
                           exam=exam,
                           can_take_exam=can_take_exam)

@app.route('/student/exam/<int:exam_id>')
@student_required
def exam(exam_id):
    """Start exam page."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if user['attendance'] < 75:
        flash('Your attendance is below 75%. You are not eligible to take the exam.', 'danger')
        return redirect(url_for('student_dashboard'))

    exam = conn.execute('SELECT * FROM exams WHERE id = ? AND is_active = 1', (exam_id,)).fetchone()
    if not exam:
        flash('Exam not found or not active.', 'danger')
        return redirect(url_for('student_dashboard'))

    questions = conn.execute(
        'SELECT * FROM questions WHERE exam_id = ? ORDER BY RANDOM()',
        (exam_id,)
    ).fetchall()
    conn.close()

    if not questions:
        flash('No questions available for this exam.', 'warning')
        return redirect(url_for('student_dashboard'))

    # Store exam start in session
    session['exam_id'] = exam_id
    session['exam_started'] = True
    session['violations'] = 0

    return render_template('exam.html', exam=exam, questions=questions)

@app.route('/student/submit', methods=['POST'])
@student_required
def submit_exam():
    """Handle exam submission and calculate grade."""
    if not session.get('exam_started'):
        flash('No active exam session.', 'danger')
        return redirect(url_for('student_dashboard'))

    exam_id = session.get('exam_id', 1)
    user_id = session['user_id']
    malpractice_flag = int(request.form.get('malpractice_flag', 0))
    violations = int(request.form.get('violations', 0))

    conn = get_db()
    questions = conn.execute(
        'SELECT * FROM questions WHERE exam_id = ?', (exam_id,)
    ).fetchall()

    score = 0
    total_marks = 0

    for q in questions:
        total_marks += q['marks']
        user_answer = request.form.get(f'q_{q["id"]}')
        if user_answer and int(user_answer) == q['correct_answer']:
            score += q['marks']

    percentage = (score / total_marks * 100) if total_marks > 0 else 0
    grade = get_grade(percentage)

    # Save result
    conn.execute(
        '''INSERT INTO results (user_id, exam_id, score, total_marks, percentage, grade, malpractice_flag)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, exam_id, score, total_marks, round(percentage, 2), grade, malpractice_flag)
    )

    # Log violations if any
    if violations > 0:
        conn.execute(
            'INSERT INTO malpractice_logs (user_id, activity) VALUES (?, ?)',
            (user_id, f'Exam submitted with {violations} tab-switch violation(s)')
        )

    conn.commit()

    # Clear exam session flags
    session.pop('exam_started', None)
    session.pop('exam_id', None)
    session.pop('violations', None)

    result = {
        'score': score,
        'total_marks': total_marks,
        'percentage': round(percentage, 2),
        'grade': grade,
        'malpractice_flag': malpractice_flag,
        'violations': violations
    }

    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    conn.close()

    return render_template('result.html', result=result, exam=exam)

# ─────────────────────────────────────────────
# ROUTES: MALPRACTICE
# ─────────────────────────────────────────────

@app.route('/api/log_malpractice', methods=['POST'])
@student_required
def log_malpractice():
    """API endpoint to log malpractice activities."""
    data = request.get_json()
    activity = data.get('activity', 'Unknown activity')
    user_id = session['user_id']

    conn = get_db()
    conn.execute(
        'INSERT INTO malpractice_logs (user_id, activity) VALUES (?, ?)',
        (user_id, activity)
    )
    conn.commit()
    conn.close()

    return jsonify({'status': 'logged', 'activity': activity})

# ─────────────────────────────────────────────
# ROUTES: ADMIN
# ─────────────────────────────────────────────

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with analytics."""
    conn = get_db()

    # Analytics
    total_students = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role='student'"
    ).fetchone()[0]

    total_exams = conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    total_results = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    malpractice_count = conn.execute(
        "SELECT COUNT(*) FROM results WHERE malpractice_flag = 1"
    ).fetchone()[0]

    # Grade distribution
    grade_dist = conn.execute(
        "SELECT grade, COUNT(*) as count FROM results GROUP BY grade"
    ).fetchall()

    # Recent results
    recent_results = conn.execute(
        '''SELECT r.*, u.name as student_name, u.email, e.title as exam_title
           FROM results r
           JOIN users u ON r.user_id = u.id
           JOIN exams e ON r.exam_id = e.id
           ORDER BY r.submitted_at DESC LIMIT 20'''
    ).fetchall()

    # All students
    students = conn.execute(
        "SELECT * FROM users WHERE role='student' ORDER BY name"
    ).fetchall()

    # Malpractice logs
    mal_logs = conn.execute(
        '''SELECT ml.*, u.name as student_name
           FROM malpractice_logs ml
           JOIN users u ON ml.user_id = u.id
           ORDER BY ml.timestamp DESC LIMIT 20'''
    ).fetchall()

    exams = conn.execute('SELECT * FROM exams ORDER BY id').fetchall()
    conn.close()

    avg_score = 0
    if total_results > 0:
        avg_score_row = conn.execute if False else None
        import sqlite3 as sq
        c2 = get_db()
        avg_score = c2.execute(
            "SELECT AVG(percentage) FROM results"
        ).fetchone()[0] or 0
        c2.close()

    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_exams=total_exams,
                           total_results=total_results,
                           malpractice_count=malpractice_count,
                           grade_dist=grade_dist,
                           recent_results=recent_results,
                           students=students,
                           mal_logs=mal_logs,
                           exams=exams,
                           avg_score=round(avg_score, 2))

@app.route('/admin/questions')
@admin_required
def manage_questions():
    """View and manage questions."""
    exam_id = request.args.get('exam_id', 1, type=int)
    conn = get_db()
    questions = conn.execute(
        'SELECT * FROM questions WHERE exam_id = ? ORDER BY id', (exam_id,)
    ).fetchall()
    exams = conn.execute('SELECT * FROM exams ORDER BY id').fetchall()
    current_exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    conn.close()
    return render_template('manage_questions.html',
                           questions=questions,
                           exams=exams,
                           current_exam=current_exam,
                           exam_id=exam_id)

@app.route('/admin/questions/add', methods=['POST'])
@admin_required
def add_question():
    """Add a new question."""
    question = request.form.get('question', '').strip()
    option1 = request.form.get('option1', '').strip()
    option2 = request.form.get('option2', '').strip()
    option3 = request.form.get('option3', '').strip()
    option4 = request.form.get('option4', '').strip()
    correct_answer = request.form.get('correct_answer', 1, type=int)
    marks = request.form.get('marks', 10, type=int)
    exam_id = request.form.get('exam_id', 1, type=int)

    if not all([question, option1, option2, option3, option4]):
        flash('All question fields are required.', 'danger')
        return redirect(url_for('manage_questions', exam_id=exam_id))

    conn = get_db()
    conn.execute(
        '''INSERT INTO questions (question, option1, option2, option3, option4, correct_answer, marks, exam_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (question, option1, option2, option3, option4, correct_answer, marks, exam_id)
    )
    conn.commit()
    conn.close()
    flash('Question added successfully!', 'success')
    return redirect(url_for('manage_questions', exam_id=exam_id))

@app.route('/admin/questions/edit/<int:qid>', methods=['POST'])
@admin_required
def edit_question(qid):
    """Edit an existing question."""
    question = request.form.get('question', '').strip()
    option1 = request.form.get('option1', '').strip()
    option2 = request.form.get('option2', '').strip()
    option3 = request.form.get('option3', '').strip()
    option4 = request.form.get('option4', '').strip()
    correct_answer = request.form.get('correct_answer', 1, type=int)
    marks = request.form.get('marks', 10, type=int)
    exam_id = request.form.get('exam_id', 1, type=int)

    conn = get_db()
    conn.execute(
        '''UPDATE questions SET question=?, option1=?, option2=?, option3=?,
           option4=?, correct_answer=?, marks=? WHERE id=?''',
        (question, option1, option2, option3, option4, correct_answer, marks, qid)
    )
    conn.commit()
    conn.close()
    flash('Question updated successfully!', 'success')
    return redirect(url_for('manage_questions', exam_id=exam_id))

@app.route('/admin/questions/delete/<int:qid>', methods=['POST'])
@admin_required
def delete_question(qid):
    """Delete a question."""
    exam_id = request.form.get('exam_id', 1, type=int)
    conn = get_db()
    conn.execute('DELETE FROM questions WHERE id=?', (qid,))
    conn.commit()
    conn.close()
    flash('Question deleted.', 'info')
    return redirect(url_for('manage_questions', exam_id=exam_id))

@app.route('/admin/exams/add', methods=['POST'])
@admin_required
def add_exam():
    """Create a new exam."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    time_limit = request.form.get('time_limit', 30, type=int)
    total_marks = request.form.get('total_marks', 100, type=int)

    if not title:
        flash('Exam title is required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn = get_db()
    conn.execute(
        'INSERT INTO exams (title, description, time_limit, total_marks) VALUES (?, ?, ?, ?)',
        (title, description, time_limit, total_marks)
    )
    conn.commit()
    conn.close()
    flash(f'Exam "{title}" created successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/students/attendance/<int:uid>', methods=['POST'])
@admin_required
def update_attendance(uid):
    """Update student attendance."""
    attendance = request.form.get('attendance', 80, type=int)
    attendance = max(0, min(100, attendance))
    conn = get_db()
    conn.execute('UPDATE users SET attendance=? WHERE id=?', (attendance, uid))
    conn.commit()
    conn.close()
    flash('Attendance updated.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/results/delete/<int:rid>', methods=['POST'])
@admin_required
def delete_result(rid):
    """Delete a result record."""
    conn = get_db()
    conn.execute('DELETE FROM results WHERE id=?', (rid,))
    conn.commit()
    conn.close()
    flash('Result deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    print("[*] Starting Online Exam Grading System...")
    print("[*] Admin Login: admin@exam.com / admin123")
    print("[*] Visit: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
