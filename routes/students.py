from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.student import Student
from models.attendance import Attendance
from services.attendance_service import get_student_attendance, get_dashboard_stats
from datetime import datetime
from functools import wraps

students_bp = Blueprint('students', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin']:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


def admin_or_teacher(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'teacher']:
            flash('Access restricted.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


@students_bp.route('/students')
@login_required
def students_list():
    search = request.args.get('search', '').strip()
    section_filter = request.args.get('section', '').strip()
    semester_filter = request.args.get('semester', '').strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.name.ilike(f'%{search}%'),
                Student.roll_no.ilike(f'%{search}%'),
                Student.email.ilike(f'%{search}%'),
            )
        )
    if section_filter:
        query = query.filter_by(section=section_filter)
    if semester_filter:
        query = query.filter_by(semester=int(semester_filter))

    students = query.order_by(Student.roll_no).all()

    # Attach quick attendance stats
    students_data = []
    for s in students:
        records = Attendance.query.filter_by(student_id=s.id).all()
        present = sum(1 for r in records if r.status == 'Present')
        total = len(records)
        pct = round((present / total * 100), 1) if total > 0 else 0
        students_data.append({'student': s, 'percentage': pct, 'total': total, 'present': present})

    sections = db.session.query(Student.section).distinct().order_by(Student.section).all()
    sections = [s[0] for s in sections]

    return render_template('students.html',
                           students_data=students_data,
                           search=search,
                           section_filter=section_filter,
                           semester_filter=semester_filter,
                           sections=sections)


@students_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        course = request.form.get('course', '').strip()
        semester = request.form.get('semester', '').strip()
        section = request.form.get('section', '').strip()
        gender = request.form.get('gender', '').strip()

        if not all([roll_no, name, course, semester, section]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_student.html')

        if Student.query.filter_by(roll_no=roll_no).first():
            flash(f'Roll number {roll_no} already exists.', 'danger')
            return render_template('add_student.html')

        try:
            student = Student(
                roll_no=roll_no,
                name=name,
                email=email or None,
                phone=phone or None,
                course=course,
                semester=int(semester),
                section=section,
                gender=gender or None,
            )
            db.session.add(student)
            db.session.commit()
            flash(f'Student {name} added successfully!', 'success')
            return redirect(url_for('students.students_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')

    return render_template('add_student.html')


@students_bp.route('/students/<int:student_id>')
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)

    # Students can only view their own profile
    if current_user.role == 'student':
        if not current_user.student_id or current_user.student_id != student_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('main.dashboard'))

    attendance_data = get_student_attendance(student_id)
    return render_template('student_detail.html', student=student, data=attendance_data)


@students_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        student.name = request.form.get('name', student.name).strip()
        student.email = request.form.get('email', '').strip() or None
        student.phone = request.form.get('phone', '').strip() or None
        student.course = request.form.get('course', student.course).strip()
        student.semester = int(request.form.get('semester', student.semester))
        student.section = request.form.get('section', student.section).strip()
        student.gender = request.form.get('gender', '').strip() or None
        student.is_active = request.form.get('is_active') == 'on'

        try:
            db.session.commit()
            flash(f'Student {student.name} updated successfully!', 'success')
            return redirect(url_for('students.student_detail', student_id=student_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'danger')

    return render_template('edit_student.html', student=student)


@students_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        db.session.delete(student)
        db.session.commit()
        flash(f'Student {student.name} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    return redirect(url_for('students.students_list'))
