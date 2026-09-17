from flask import Blueprint, render_template
from flask_login import login_required, current_user
from services.attendance_service import get_dashboard_stats, get_student_attendance
from models.subject import Subject
from models.attendance import Attendance
from models.student import Student
from models import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    if current_user.role == 'student':
        # Student sees their own dashboard
        student_data = None
        if current_user.student_id:
            student_data = get_student_attendance(current_user.student_id)
        return render_template('dashboard.html', student_data=student_data, stats=None)

    stats = get_dashboard_stats()

    # Subject-wise average attendance for chart
    subjects = Subject.query.all()
    subject_chart_data = []
    for subj in subjects:
        records = Attendance.query.filter_by(subject_id=subj.id).all()
        present = sum(1 for r in records if r.status == 'Present')
        total = len(records)
        pct = round((present / total * 100), 1) if total > 0 else 0
        subject_chart_data.append({
            'name': subj.name,
            'code': subj.code,
            'percentage': pct,
        })

    return render_template('dashboard.html',
                           stats=stats,
                           subject_chart_data=subject_chart_data,
                           student_data=None)
