from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from services.attendance_service import get_student_attendance, get_whatif_analysis
from services.ai_service import (
    ask_attendance_assistant, generate_ai_insight, explain_whatif
)
from models.student import Student

ai_bp = Blueprint('ai', __name__)


def get_student_for_user():
    """Return the student record for the current user."""
    if current_user.role == 'student' and current_user.student_id:
        return Student.query.get(current_user.student_id)
    return None


@ai_bp.route('/ai-assistant')
@login_required
def ai_assistant():
    student = None
    student_data = None
    insight = None

    if current_user.role == 'student':
        student = get_student_for_user()
        if student:
            student_data = get_student_attendance(student.id)
            insight, _ = generate_ai_insight(student_data)
    elif current_user.role in ['admin', 'teacher']:
        # Admin/teacher can select a student
        student_id = request.args.get('student_id')
        if student_id:
            student = Student.query.get(student_id)
            if student:
                student_data = get_student_attendance(student.id)
                insight, _ = generate_ai_insight(student_data)

    all_students = Student.query.filter_by(is_active=True).order_by(Student.name).all() \
        if current_user.role in ['admin', 'teacher'] else []

    return render_template('ai_assistant.html',
                           student=student,
                           student_data=student_data,
                           insight=insight,
                           all_students=all_students)


@ai_bp.route('/ai-assistant/ask', methods=['POST'])
@login_required
def ask_ai():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    question = data.get('question', '').strip()
    student_id = data.get('student_id')

    if not question:
        return jsonify({'error': 'Question cannot be empty'}), 400

    # Determine student
    if current_user.role == 'student':
        student_id = current_user.student_id
    elif student_id:
        student_id = int(student_id)
    else:
        return jsonify({'error': 'No student selected'}), 400

    if not student_id:
        return jsonify({'error': 'Student profile not linked to this account'}), 400

    student_data = get_student_attendance(student_id)
    if not student_data:
        return jsonify({'error': 'Student not found'}), 404

    response_text, success = ask_attendance_assistant(student_data, question)

    return jsonify({
        'response': response_text,
        'success': success,
        'student_name': student_data['student_name'],
    })


@ai_bp.route('/ai-assistant/whatif', methods=['POST'])
@login_required
def whatif_analysis():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    student_id = data.get('student_id')
    n_classes = data.get('n_classes', 5)

    if current_user.role == 'student':
        student_id = current_user.student_id

    if not student_id:
        return jsonify({'error': 'No student selected'}), 400

    try:
        n_classes = int(n_classes)
        if n_classes < 1 or n_classes > 100:
            return jsonify({'error': 'Please enter a number between 1 and 100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid number of classes'}), 400

    result = get_whatif_analysis(int(student_id), n_classes)
    if not result:
        return jsonify({'error': 'Student not found'}), 404

    student_data = get_student_attendance(int(student_id))
    explanation = explain_whatif(
        student_data, n_classes,
        result['attend_all_percentage'],
        result['miss_all_percentage']
    )

    return jsonify({
        'n_classes': n_classes,
        'current_percentage': result['current_percentage'],
        'attend_all_percentage': result['attend_all_percentage'],
        'miss_all_percentage': result['miss_all_percentage'],
        'explanation': explanation,
    })
