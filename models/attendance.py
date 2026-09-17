from datetime import datetime
from models import db


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # 'Present' or 'Absent'
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint to prevent duplicate attendance
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'date',
                            name='uq_student_subject_date'),
    )

    def __repr__(self):
        return f'<Attendance Student:{self.student_id} Subject:{self.subject_id} {self.date} {self.status}>'
