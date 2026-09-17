import os
from openai import OpenAI
from flask import current_app


def get_ai_client_and_model():
    """
    Return an OpenAI-compatible client and model name.
    Seamlessly supports both Groq (gsk_...) and xAI Grok (xai-...) API keys.
    """
    try:
        api_key = current_app.config.get('XAI_API_KEY', '')
    except Exception:
        api_key = ''
    if not api_key:
        api_key = os.environ.get('XAI_API_KEY', '')
    if not api_key or api_key == 'your_xai_api_key_here':
        return None, None

    if api_key.startswith('gsk_'):
        # Groq Cloud API key
        client = OpenAI(
            api_key=api_key,
            base_url='https://api.groq.com/openai/v1',
        )
        model = 'openai/gpt-oss-20b'
        return client, model
    else:
        # xAI Grok API key
        client = OpenAI(
            api_key=api_key,
            base_url='https://api.x.ai/v1',
        )
        model = 'grok-3-mini'
        return client, model


def ask_attendance_assistant(student_data, user_question):
    """
    Send verified attendance data + user question to Grok/Groq.
    The model receives only pre-calculated data — it CANNOT access the DB.
    Returns (response_text, success_bool).
    """
    client, model = get_ai_client_and_model()
    if not client:
        return (
            "AI assistant is currently unavailable. The API key is not configured. "
            "Please add your API key to the .env file.",
            False
        )

    # Build context from verified Python-calculated data
    subjects_text = "\n".join([
        f"  - {s['subject_name']} ({s['subject_code']}): "
        f"{s['present']}/{s['total']} classes = {s['percentage']:.1f}% [{s['risk']}]"
        f"{' — Need ' + str(s['required_classes']) + ' more classes to reach 75%' if s['required_classes'] > 0 else ' — Above 75% requirement'}"
        for s in student_data.get('subjects', [])
    ])

    context = f"""
STUDENT ATTENDANCE DATA (Pre-calculated by the backend system):
Student Name: {student_data['student_name']}
Roll No: {student_data['roll_no']}
Course: {student_data['course']}
Semester: {student_data['semester']}
Section: {student_data['section']}

Overall Attendance: {student_data['total_present']}/{student_data['total_classes']} classes = {student_data['overall_percentage']:.1f}%
Overall Risk Level: {student_data['risk']}
Classes needed to reach 75% overall: {student_data['required_classes'] if student_data['required_classes'] > 0 else 'Already above 75%'}

Subject-wise Breakdown:
{subjects_text}

Attendance Threshold: 75% (minimum required)
Critical Threshold: 65%
"""

    system_prompt = """You are EduFlow AI Assistant, an attendance advisor for students. 
You will be given verified attendance data that has been calculated by the backend system.

CRITICAL RULES:
1. Only use the attendance data provided in the context. Do NOT invent or modify any numbers.
2. Do NOT claim to have access to the database. All data is provided to you.
3. Do NOT recalculate attendance percentages — use the ones provided.
4. Give friendly, encouraging, and actionable advice.
5. Keep responses concise (2-4 paragraphs maximum).
6. If a student asks something you cannot answer from the data, say so honestly.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"Context:\n{context}\n\nStudent Question: {user_question}"}
            ],
            max_tokens=600,
            temperature=0.7,
        )
        return (response.choices[0].message.content, True)
    except Exception as e:
        error_msg = str(e)
        if 'api_key' in error_msg.lower() or 'authentication' in error_msg.lower():
            return ("Invalid API key. Please check your API key in the .env file.", False)
        # Fallback to rule-based answer
        return (
            f"Note: Live AI service encountered an issue ({error_msg[:60]}...). "
            f"Here is your current status: Overall attendance is {student_data['overall_percentage']:.1f}% "
            f"({student_data['risk']} risk). "
            + (f"You need {student_data['required_classes']} classes to reach 75%." if student_data['required_classes'] > 0 else "You are above the 75% requirement!"),
            False
        )


def generate_ai_insight(student_data):
    """
    Generate a short proactive insight for the student dashboard.
    Returns (insight_text, success_bool).
    """
    client, model = get_ai_client_and_model()
    if not client:
        return generate_fallback_insight(student_data), False

    subjects = student_data.get('subjects', [])
    worst_subject = min(subjects, key=lambda s: s['percentage']) if subjects else None

    context = f"""
Student: {student_data['student_name']}
Overall Attendance: {student_data['overall_percentage']:.1f}%
Risk: {student_data['risk']}
Subjects: {', '.join([f"{s['subject_name']} {s['percentage']:.1f}%" for s in subjects])}
Classes needed overall: {student_data['required_classes'] if student_data['required_classes'] > 0 else 0}
Worst subject: {worst_subject['subject_name'] + ' at ' + str(worst_subject['percentage']) + '%' if worst_subject else 'N/A'}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'Generate a concise 2-3 sentence attendance insight for a student. '
                        'Use only the provided data. Be encouraging but honest about risks. '
                        'Mention the worst subject if attendance is below 75%. '
                        'Do NOT invent numbers.'
                    )
                },
                {'role': 'user', 'content': context}
            ],
            max_tokens=200,
            temperature=0.6,
        )
        return (response.choices[0].message.content, True)
    except Exception:
        return generate_fallback_insight(student_data), False


def generate_fallback_insight(student_data):
    """Rule-based insight when AI is unavailable."""
    pct = student_data['overall_percentage']
    risk = student_data['risk']
    subjects = student_data.get('subjects', [])

    if risk == 'LOW':
        msg = f"Great job! Your overall attendance is {pct:.1f}%, well above the 75% requirement. Keep it up!"
    elif risk == 'MEDIUM':
        msg = f"Your attendance is {pct:.1f}%. You're close to the 75% threshold — stay consistent to maintain your standing."
    elif risk == 'HIGH':
        required = student_data['required_classes']
        msg = f"Your attendance is {pct:.1f}%, below the required 75%. You need to attend {required} more consecutive classes to meet the requirement."
    else:
        required = student_data['required_classes']
        msg = f"Critical: Your attendance is {pct:.1f}%, significantly below 75%. Attend the next {required} classes to get back on track."

    if subjects:
        worst = min(subjects, key=lambda s: s['percentage'])
        if worst['percentage'] < 75:
            msg += f" Your lowest attendance is in {worst['subject_name']} at {worst['percentage']:.1f}% — prioritize those classes."

    return msg


def explain_whatif(student_data, n_classes, attend_pct, miss_pct):
    """
    Ask Grok/Groq to explain the what-if scenario in natural language.
    Calculations already done in Python — AI only explains.
    """
    client, model = get_ai_client_and_model()
    current_pct = student_data['overall_percentage']

    context = f"""
Student: {student_data['student_name']}
Current attendance: {current_pct:.1f}%
Current: {student_data['total_present']}/{student_data['total_classes']} classes

What-if analysis for next {n_classes} classes (calculated by backend):
- If attending all {n_classes}: {attend_pct:.1f}%
- If missing all {n_classes}: {miss_pct:.1f}%
75% threshold requirement applies.
"""

    if not client:
        return _fallback_whatif_explanation(current_pct, n_classes, attend_pct, miss_pct)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'Explain this attendance what-if analysis to the student in 2-3 friendly sentences. '
                        'Use ONLY the provided percentages — do not recalculate. '
                        'Mention whether they would be above or below 75% in each scenario.'
                    )
                },
                {'role': 'user', 'content': context}
            ],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception:
        return _fallback_whatif_explanation(current_pct, n_classes, attend_pct, miss_pct)


def _fallback_whatif_explanation(current_pct, n_classes, attend_pct, miss_pct):
    attend_status = "above" if attend_pct >= 75 else "below"
    miss_status = "above" if miss_pct >= 75 else "below"
    return (
        f"Currently at {current_pct:.1f}%, if you attend all {n_classes} upcoming classes, "
        f"your attendance will rise to {attend_pct:.1f}% ({attend_status} 75%). "
        f"If you miss all {n_classes}, it drops to {miss_pct:.1f}% ({miss_status} 75%)."
    )
