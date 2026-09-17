from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.subject import Subject
from models.student import Student
from models.attendance import Attendance
from datetime import datetime, date
from functools import wraps
from sqlalchemy.exc import IntegrityError

attendance_bp = Blueprint('attendance', __name__)


def teacher_or_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'teacher']:
            flash('Teacher or Admin access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


@attendance_bp.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
@teacher_or_admin
def mark_attendance():
    subjects = Subject.query.order_by(Subject.semester, Subject.name).all()

    selected_subject_id = request.form.get('subject_id') or request.args.get('subject_id')
    selected_date_str = request.form.get('date') or request.args.get('date', date.today().isoformat())
    selected_section = request.form.get('section') or request.args.get('section')

    students = []
    existing_map = {}
    subject = None

    if selected_subject_id:
        subject = Subject.query.get(selected_subject_id)
        if subject:
            # Get all active students for this subject's semester/section
            student_query = Student.query.filter_by(
                semester=subject.semester,
                section=subject.section,
                is_active=True
            ).order_by(Student.roll_no)
            students = student_query.all()

            # Check existing attendance for this date/subject
            try:
                att_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                att_date = date.today()

            existing = Attendance.query.filter_by(
                subject_id=subject.id,
                date=att_date
            ).all()
            existing_map = {e.student_id: e.status for e in existing}

    if request.method == 'POST' and request.form.get('action') == 'submit_attendance':
        subject_id = int(request.form.get('subject_id'))
        date_str = request.form.get('date')
        subj = Subject.query.get(subject_id)

        if not subj:
            flash('Invalid subject selected.', 'danger')
            return redirect(url_for('attendance.mark_attendance'))

        try:
            att_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('attendance.mark_attendance'))

        if att_date > date.today():
            flash('Cannot mark attendance for future dates.', 'danger')
            return redirect(url_for('attendance.mark_attendance'))

        all_students = Student.query.filter_by(
            semester=subj.semester,
            section=subj.section,
            is_active=True
        ).all()

        saved = 0
        skipped = 0
        for student in all_students:
            status_key = f'status_{student.id}'
            status = request.form.get(status_key, 'Absent')
            if status not in ('Present', 'Absent'):
                status = 'Absent'

            # Check for existing record
            existing = Attendance.query.filter_by(
                student_id=student.id,
                subject_id=subject_id,
                date=att_date
            ).first()

            if existing:
                existing.status = status
                skipped += 1
            else:
                record = Attendance(
                    student_id=student.id,
                    subject_id=subject_id,
                    date=att_date,
                    status=status,
                    marked_by=current_user.id
                )
                db.session.add(record)
                saved += 1

        try:
            db.session.commit()
            flash(f'Attendance saved! {saved} new records, {skipped} updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving attendance: {str(e)}', 'danger')

        return redirect(url_for('attendance.mark_attendance',
                                subject_id=subject_id, date=date_str))

    return render_template('mark_attendance.html',
                           subjects=subjects,
                           students=students,
                           subject=subject,
                           selected_date=selected_date_str,
                           existing_map=existing_map,
                           today=date.today().isoformat())


@attendance_bp.route('/subjects')
@login_required
def subjects_list():
    subjects = Subject.query.order_by(Subject.semester, Subject.name).all()
    return render_template('subjects.html', subjects=subjects)


@attendance_bp.route('/subjects/add', methods=['GET', 'POST'])
@login_required
def add_subject():
    if current_user.role not in ['admin']:
        flash('Admin access required.', 'danger')
        return redirect(url_for('attendance.subjects_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        semester = request.form.get('semester', '').strip()
        section = request.form.get('section', '').strip()
        credits = request.form.get('credits', '3').strip()

        if not all([name, code, semester, section]):
            flash('All fields are required.', 'danger')
            return render_template('subjects.html', subjects=Subject.query.all(), show_form=True)

        if Subject.query.filter_by(code=code).first():
            flash(f'Subject code {code} already exists.', 'danger')
            return render_template('subjects.html', subjects=Subject.query.all(), show_form=True)

        try:
            subject = Subject(name=name, code=code, semester=int(semester),
                              section=section, credits=int(credits))
            db.session.add(subject)
            db.session.commit()
            flash(f'Subject {name} added!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('attendance.subjects_list'))


@attendance_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    if current_user.role not in ['admin']:
        flash('Admin access required.', 'danger')
        return redirect(url_for('attendance.subjects_list'))

    subject = Subject.query.get_or_404(subject_id)
    try:
        db.session.delete(subject)
        db.session.commit()
        flash(f'Subject {subject.name} deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('attendance.subjects_list'))
