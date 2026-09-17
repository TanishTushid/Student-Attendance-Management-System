import os
import sys
import random
from datetime import datetime, date, timedelta

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_login import LoginManager
from models import db, login_manager
from models.student import User, Student
from models.subject import Subject
from models.attendance import Attendance
from config import Config

from routes.auth import auth_bp
from routes.main import main_bp
from routes.students import students_bp
from routes.attendance import attendance_bp
from routes.reports import reports_bp
from routes.ai import ai_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure instance folder exists
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ai_bp)

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    with app.app_context():
        db.create_all()
        seed_data()

    return app


def seed_data():
    """Seed realistic demo data for hackathon demonstration."""
    # Skip if already seeded
    if User.query.filter_by(username='admin').first():
        return

    print("[*] Seeding demo data...")

    # ─── Users ───────────────────────────────────────────────
    admin = User(username='admin', email='admin@eduflow.com',
                 full_name='Dr. Admin Kumar', role='admin')
    admin.set_password('admin123')

    teacher = User(username='teacher', email='teacher@eduflow.com',
                   full_name='Prof. Meera Sharma', role='teacher')
    teacher.set_password('teacher123')

    db.session.add_all([admin, teacher])
    db.session.flush()

    # ─── Subjects ────────────────────────────────────────────
    subjects_data = [
        ('Data Structures & Algorithms', 'DSA301', 3, 'A'),
        ('Database Management Systems', 'DBMS302', 3, 'A'),
        ('Python Programming', 'PY303', 3, 'A'),
        ('Computer Networks', 'CN304', 3, 'A'),
        ('Operating Systems', 'OS305', 3, 'A'),
        ('Data Structures & Algorithms', 'DSA301B', 3, 'B'),
        ('Database Management Systems', 'DBMS302B', 3, 'B'),
        ('Python Programming', 'PY303B', 3, 'B'),
    ]

    subjects = []
    for name, code, sem, sec in subjects_data:
        s = Subject(name=name, code=code, semester=sem, section=sec, credits=4)
        db.session.add(s)
        subjects.append(s)
    db.session.flush()

    # ─── Students (Section A - 12 students, Section B - 8 students) ──────
    students_raw = [
        # (roll_no, name, email, section, attendance_profile)
        # Profiles: high(85-95), good(75-85), medium(65-75), low(<65)
        ('CS301001', 'Rahul Sharma', 'rahul@example.com', 'A', 'high'),
        ('CS301002', 'Priya Patel', 'priya@example.com', 'A', 'good'),
        ('CS301003', 'Amit Singh', 'amit@example.com', 'A', 'medium'),
        ('CS301004', 'Sneha Gupta', 'sneha@example.com', 'A', 'low'),
        ('CS301005', 'Vikram Rao', 'vikram@example.com', 'A', 'high'),
        ('CS301006', 'Ananya Krishnan', 'ananya@example.com', 'A', 'good'),
        ('CS301007', 'Rohan Mehta', 'rohan@example.com', 'A', 'low'),
        ('CS301008', 'Divya Nair', 'divya@example.com', 'A', 'medium'),
        ('CS301009', 'Arjun Verma', 'arjun@example.com', 'A', 'high'),
        ('CS301010', 'Kavya Reddy', 'kavya@example.com', 'A', 'good'),
        ('CS301011', 'Nikhil Joshi', 'nikhil@example.com', 'A', 'medium'),
        ('CS301012', 'Pooja Agarwal', 'pooja@example.com', 'A', 'low'),
        ('CS301013', 'Siddharth Das', 'siddharth@example.com', 'B', 'high'),
        ('CS301014', 'Megha Iyer', 'megha@example.com', 'B', 'good'),
        ('CS301015', 'Aarav Malhotra', 'aarav@example.com', 'B', 'medium'),
        ('CS301016', 'Tanvi Bhatt', 'tanvi@example.com', 'B', 'low'),
        ('CS301017', 'Karan Bajaj', 'karan@example.com', 'B', 'high'),
        ('CS301018', 'Ishaan Kapoor', 'ishaan@example.com', 'B', 'good'),
        ('CS301019', 'Riya Saxena', 'riya@example.com', 'B', 'medium'),
        ('CS301020', 'Aryan Pandey', 'aryan@example.com', 'B', 'low'),
    ]

    attendance_profiles = {
        'high': (0.85, 0.95),
        'good': (0.75, 0.85),
        'medium': (0.65, 0.75),
        'low': (0.45, 0.65),
    }

    student_objects = []
    for roll, name, email, section, profile in students_raw:
        s = Student(roll_no=roll, name=name, email=email,
                    course='B.Tech CSE', semester=3, section=section,
                    gender=random.choice(['Male', 'Female']),
                    is_active=True)
        db.session.add(s)
        student_objects.append((s, profile))
    db.session.flush()

    # ─── Seed student user account (for demo login) ──────────
    # Link CS301004 (Sneha Gupta - low attendance) as the demo student user
    demo_student_obj = None
    for s_obj, p in student_objects:
        if s_obj.roll_no == 'CS301004':
            demo_student_obj = s_obj
            break

    if demo_student_obj:
        student_user = User(
            username='student',
            email='student@eduflow.com',
            full_name=demo_student_obj.name,
            role='student',
            student_id=demo_student_obj.id
        )
        student_user.set_password('student123')
        db.session.add(student_user)
        db.session.flush()

    # ─── Generate attendance records (last 8 weeks, Mon-Fri) ──
    today = date.today()
    start_date = today - timedelta(weeks=8)

    # Build class days (Mon-Fri, skip weekends)
    class_days = []
    current = start_date
    while current <= today:
        if current.weekday() < 5:  # Mon-Fri
            class_days.append(current)
        current += timedelta(days=1)

    # Each subject has classes ~3 days/week
    # Pick specific days for each subject
    def get_subject_days(days, frequency=3):
        """Pick every Nth day roughly."""
        result = []
        for i, d in enumerate(days):
            if i % (5 // frequency) == 0:
                result.append(d)
        return result

    sec_a_subjects = [s for s in subjects if s.section == 'A']
    sec_b_subjects = [s for s in subjects if s.section == 'B']

    # Assign each subject different weekdays
    subj_day_map = {}
    for i, subj in enumerate(sec_a_subjects):
        # Pick days where weekday matches (e.g., subj 0 → Mon/Wed/Fri, subj 1 → Tue/Thu...)
        target_days = [d for d in class_days if d.weekday() in [(i * 1) % 5, (i * 2 + 1) % 5, (i * 3 + 2) % 5]]
        subj_day_map[subj.id] = sorted(set(target_days))[:40]  # cap at 40 classes

    for i, subj in enumerate(sec_b_subjects):
        target_days = [d for d in class_days if d.weekday() in [(i * 2) % 5, (i * 3 + 1) % 5]]
        subj_day_map[subj.id] = sorted(set(target_days))[:30]

    # Generate attendance per student per subject
    random.seed(42)  # Reproducible
    attendance_records = []

    for student_obj, profile in student_objects:
        pct_min, pct_max = attendance_profiles[profile]

        # Add per-student variation
        target_pct = random.uniform(pct_min, pct_max)

        # Get their section's subjects
        their_subjects = sec_a_subjects if student_obj.section == 'A' else sec_b_subjects

        for subject in their_subjects:
            days = subj_day_map.get(subject.id, [])

            # Per-subject slight variation in attendance
            subj_pct = max(0.3, min(0.98, target_pct + random.uniform(-0.08, 0.08)))

            for class_day in days:
                status = 'Present' if random.random() < subj_pct else 'Absent'
                rec = Attendance(
                    student_id=student_obj.id,
                    subject_id=subject.id,
                    date=class_day,
                    status=status,
                    marked_by=teacher.id,
                )
                attendance_records.append(rec)

    db.session.add_all(attendance_records)
    db.session.commit()
    print(f"[+] Seeded: {len(student_objects)} students, {len(subjects)} subjects, {len(attendance_records)} attendance records")
    print("[+] Demo credentials:")
    print("   Admin   -> admin / admin123")
    print("   Teacher -> teacher / teacher123")
    print("   Student -> student / student123")


if __name__ == '__main__':
    app = create_app()
    print("\n[+] EduFlow is running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
