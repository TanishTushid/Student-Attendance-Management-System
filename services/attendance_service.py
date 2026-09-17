from models import db
from models.attendance import Attendance
from models.student import Student
from models.subject import Subject
from sqlalchemy import func
import math


def calculate_percentage(present, total):
    """Calculate attendance percentage. Returns 0 if no classes."""
    if total == 0:
        return 0.0
    return round((present / total) * 100, 2)


def calculate_required_classes(present, total, threshold=75.0):
    """
    Calculate how many consecutive future classes a student must attend
    to reach the threshold percentage.
    Formula: (present + x) / (total + x) >= threshold/100
    Solve for smallest integer x >= 0.
    Returns 0 if already at or above threshold, -1 if impossible.
    """
    current_pct = calculate_percentage(present, total)
    if current_pct >= threshold:
        return 0

    # Solve: (present + x) / (total + x) >= threshold/100
    # present + x >= threshold/100 * (total + x)
    # present + x >= threshold*total/100 + threshold*x/100
    # x - threshold*x/100 >= threshold*total/100 - present
    # x * (1 - threshold/100) >= threshold*total/100 - present
    t = threshold / 100.0
    numerator = t * total - present
    denominator = 1 - t

    if denominator <= 0:
        return -1  # threshold is 100%, impossible if any absent

    x = math.ceil(numerator / denominator)
    return max(0, x)


def calculate_classes_can_miss(present, total, threshold=75.0):
    """
    Calculate how many classes a student can miss while staying above threshold.
    Formula: present / (total + x) >= threshold/100
    Returns 0 if already below threshold.
    """
    current_pct = calculate_percentage(present, total)
    if current_pct < threshold:
        return 0

    t = threshold / 100.0
    # present / (total + x) >= t
    # total + x <= present / t
    # x <= present/t - total
    max_total = math.floor(present / t)
    x = max_total - total
    return max(0, x)


def get_student_attendance(student_id):
    """
    Get comprehensive attendance data for a student.
    Returns dict with overall and per-subject stats.
    """
    from models.student import Student

    student = Student.query.get(student_id)
    if not student:
        return None

    records = Attendance.query.filter_by(student_id=student_id).all()

    total_present = sum(1 for r in records if r.status == 'Present')
    total_classes = len(records)
    overall_pct = calculate_percentage(total_present, total_classes)

    # Per-subject breakdown
    subjects = Subject.query.filter_by(
        semester=student.semester,
        section=student.section
    ).all()

    subject_stats = []
    for subject in subjects:
        subj_records = [r for r in records if r.subject_id == subject.id]
        s_present = sum(1 for r in subj_records if r.status == 'Present')
        s_total = len(subj_records)
        s_pct = calculate_percentage(s_present, s_total)
        required = calculate_required_classes(s_present, s_total)
        can_miss = calculate_classes_can_miss(s_present, s_total)
        risk = get_risk_level(s_pct)

        subject_stats.append({
            'subject_id': subject.id,
            'subject_name': subject.name,
            'subject_code': subject.code,
            'present': s_present,
            'total': s_total,
            'percentage': s_pct,
            'required_classes': required,
            'can_miss': can_miss,
            'risk': risk,
        })

    overall_required = calculate_required_classes(total_present, total_classes)
    overall_can_miss = calculate_classes_can_miss(total_present, total_classes)

    return {
        'student_id': student_id,
        'student_name': student.name,
        'roll_no': student.roll_no,
        'course': student.course,
        'semester': student.semester,
        'section': student.section,
        'total_present': total_present,
        'total_classes': total_classes,
        'overall_percentage': overall_pct,
        'required_classes': overall_required,
        'can_miss': overall_can_miss,
        'risk': get_risk_level(overall_pct),
        'subjects': subject_stats,
    }


def get_subject_attendance(subject_id):
    """
    Get attendance stats for a subject across all students.
    """
    subject = Subject.query.get(subject_id)
    if not subject:
        return None

    students = Student.query.filter_by(
        semester=subject.semester,
        section=subject.section,
        is_active=True
    ).all()

    student_stats = []
    for student in students:
        records = Attendance.query.filter_by(
            student_id=student.id,
            subject_id=subject_id
        ).all()
        present = sum(1 for r in records if r.status == 'Present')
        total = len(records)
        pct = calculate_percentage(present, total)
        student_stats.append({
            'student_id': student.id,
            'roll_no': student.roll_no,
            'name': student.name,
            'present': present,
            'total': total,
            'percentage': pct,
            'risk': get_risk_level(pct),
        })

    avg_pct = 0
    if student_stats:
        avg_pct = round(sum(s['percentage'] for s in student_stats) / len(student_stats), 2)

    return {
        'subject_id': subject_id,
        'subject_name': subject.name,
        'subject_code': subject.code,
        'semester': subject.semester,
        'section': subject.section,
        'students': student_stats,
        'average_percentage': avg_pct,
    }


def get_risk_level(percentage):
    """Transparent rule-based risk classification."""
    if percentage >= 80:
        return 'LOW'
    elif percentage >= 75:
        return 'MEDIUM'
    elif percentage >= 65:
        return 'HIGH'
    else:
        return 'CRITICAL'


def get_risk_label(risk):
    labels = {
        'LOW': 'Safe',
        'MEDIUM': 'Medium Risk',
        'HIGH': 'Shortage',
        'CRITICAL': 'Critical',
    }
    return labels.get(risk, risk)


def get_dashboard_stats():
    """Compute all dashboard statistics."""
    total_students = Student.query.filter_by(is_active=True).count()
    total_subjects = Subject.query.count()
    total_records = Attendance.query.count()
    total_present = Attendance.query.filter_by(status='Present').count()

    avg_attendance = calculate_percentage(total_present, total_records)

    # Students below thresholds (check per-student overall attendance)
    students = Student.query.filter_by(is_active=True).all()
    below_75 = 0
    below_65 = 0
    for s in students:
        records = Attendance.query.filter_by(student_id=s.id).all()
        if not records:
            continue
        present = sum(1 for r in records if r.status == 'Present')
        pct = calculate_percentage(present, len(records))
        if pct < 75:
            below_75 += 1
        if pct < 65:
            below_65 += 1

    # Recent attendance activity (last 10 records)
    recent = db.session.query(Attendance, Student, Subject)\
        .join(Student, Attendance.student_id == Student.id)\
        .join(Subject, Attendance.subject_id == Subject.id)\
        .order_by(Attendance.created_at.desc())\
        .limit(10).all()

    recent_activity = []
    for att, stu, sub in recent:
        recent_activity.append({
            'roll_no': stu.roll_no,
            'student_name': stu.name,
            'subject_name': sub.name,
            'date': att.date.strftime('%d %b %Y'),
            'status': att.status,
        })

    return {
        'total_students': total_students,
        'total_subjects': total_subjects,
        'total_records': total_records,
        'avg_attendance': avg_attendance,
        'below_75': below_75,
        'below_65': below_65,
        'recent_activity': recent_activity,
    }


def get_whatif_analysis(student_id, n_classes):
    """
    Calculate what-if scenarios for attending/missing next N classes.
    All calculations in Python — not delegated to AI.
    """
    data = get_student_attendance(student_id)
    if not data:
        return None

    present = data['total_present']
    total = data['total_classes']
    current_pct = data['overall_percentage']

    # Scenario 1: Attend all N
    attend_pct = calculate_percentage(present + n_classes, total + n_classes)

    # Scenario 2: Miss all N
    miss_pct = calculate_percentage(present, total + n_classes)

    return {
        'n_classes': n_classes,
        'current_percentage': current_pct,
        'attend_all_percentage': attend_pct,
        'miss_all_percentage': miss_pct,
        'current_present': present,
        'current_total': total,
    }
