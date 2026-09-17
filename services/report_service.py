import csv
import io
from services.attendance_service import (
    get_student_attendance, calculate_percentage, get_risk_level, get_risk_label,
    calculate_required_classes
)
from models.student import Student
from models.subject import Subject
from models.attendance import Attendance


def get_shortage_report(threshold=75.0, section=None, semester=None,
                        subject_id=None, risk_filter=None):
    """
    Generate the shortage/defaulter report.
    Returns list of dicts with per-student-per-subject stats.
    """
    query = Student.query.filter_by(is_active=True)
    if section:
        query = query.filter_by(section=section)
    if semester:
        query = query.filter_by(semester=int(semester))

    students = query.all()
    rows = []

    for student in students:
        # Get subjects for this student's semester/section
        subj_query = Subject.query.filter_by(
            semester=student.semester,
            section=student.section
        )
        if subject_id:
            subj_query = subj_query.filter_by(id=int(subject_id))

        subjects = subj_query.all()

        for subject in subjects:
            records = Attendance.query.filter_by(
                student_id=student.id,
                subject_id=subject.id
            ).all()

            present = sum(1 for r in records if r.status == 'Present')
            total = len(records)
            pct = calculate_percentage(present, total)
            required = calculate_required_classes(present, total, threshold)
            risk = get_risk_level(pct)

            if risk_filter and risk != risk_filter:
                continue

            rows.append({
                'student_id': student.id,
                'roll_no': student.roll_no,
                'name': student.name,
                'section': student.section,
                'semester': student.semester,
                'subject_id': subject.id,
                'subject_name': subject.name,
                'subject_code': subject.code,
                'present': present,
                'total': total,
                'percentage': pct,
                'required_classes': required,
                'risk': risk,
                'risk_label': get_risk_label(risk),
            })

    # Sort by percentage ascending (worst first)
    rows.sort(key=lambda x: x['percentage'])
    return rows


def export_shortage_csv(rows):
    """Generate CSV bytes from shortage report rows."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'Roll No', 'Name', 'Section', 'Semester', 'Subject', 'Subject Code',
        'Present', 'Total', 'Attendance %', 'Required Classes', 'Risk Level'
    ])
    writer.writeheader()
    for row in rows:
        writer.writerow({
            'Roll No': row['roll_no'],
            'Name': row['name'],
            'Section': row['section'],
            'Semester': row['semester'],
            'Subject': row['subject_name'],
            'Subject Code': row['subject_code'],
            'Present': row['present'],
            'Total': row['total'],
            'Attendance %': f"{row['percentage']:.1f}",
            'Required Classes': row['required_classes'] if row['required_classes'] >= 0 else 'N/A',
            'Risk Level': row['risk_label'],
        })
    return output.getvalue()
