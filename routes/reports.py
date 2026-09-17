from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from services.report_service import get_shortage_report, export_shortage_csv
from models.subject import Subject
from models.student import Student
from models import db

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def reports():
    threshold = float(request.args.get('threshold', 75.0))
    section_filter = request.args.get('section', '').strip()
    semester_filter = request.args.get('semester', '').strip()
    subject_filter = request.args.get('subject_id', '').strip()
    risk_filter = request.args.get('risk', '').strip()

    rows = get_shortage_report(
        threshold=threshold,
        section=section_filter or None,
        semester=semester_filter or None,
        subject_id=subject_filter or None,
        risk_filter=risk_filter or None,
    )

    sections = db.session.query(Student.section).distinct().order_by(Student.section).all()
    sections = [s[0] for s in sections]

    subjects = Subject.query.order_by(Subject.name).all()

    # Summary counts
    summary = {
        'safe': sum(1 for r in rows if r['risk'] == 'LOW'),
        'medium': sum(1 for r in rows if r['risk'] == 'MEDIUM'),
        'shortage': sum(1 for r in rows if r['risk'] == 'HIGH'),
        'critical': sum(1 for r in rows if r['risk'] == 'CRITICAL'),
        'total': len(rows),
    }

    return render_template('reports.html',
                           rows=rows,
                           sections=sections,
                           subjects=subjects,
                           summary=summary,
                           threshold=threshold,
                           section_filter=section_filter,
                           semester_filter=semester_filter,
                           subject_filter=subject_filter,
                           risk_filter=risk_filter)


@reports_bp.route('/reports/export/csv')
@login_required
def export_csv():
    threshold = float(request.args.get('threshold', 75.0))
    section_filter = request.args.get('section', '').strip() or None
    semester_filter = request.args.get('semester', '').strip() or None
    subject_filter = request.args.get('subject_id', '').strip() or None
    risk_filter = request.args.get('risk', '').strip() or None

    rows = get_shortage_report(
        threshold=threshold,
        section=section_filter,
        semester=semester_filter,
        subject_id=subject_filter,
        risk_filter=risk_filter,
    )

    csv_data = export_shortage_csv(rows)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=attendance_report.csv'}
    )
