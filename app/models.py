from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class StudentClass(db.Model):
    __tablename__ = 'student_class'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    
    # Relationships
    students = db.relationship('Student', backref='student_class', lazy=True, cascade="all, delete-orphan")
    sessions = db.relationship('Session', backref='student_class', lazy=True)

class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    
    # Relationships
    sessions = db.relationship('Session', backref='course', lazy=True)

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    student_number = db.Column(db.String(80), unique=True, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('student_class.id'), nullable=False)

class Session(db.Model):
    __tablename__ = 'session'
    id = db.Column(db.String(80), primary_key=True)  # 8-char session_id
    class_id = db.Column(db.Integer, db.ForeignKey('student_class.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, default=0.0)
    avg_attention_rate = db.Column(db.Float, default=0.0)
    max_students_count = db.Column(db.Integer, default=0)
    
    # Relationships
    timeline_records = db.relationship('TimelineRecord', backref='session', lazy=True, cascade="all, delete-orphan")

class TimelineRecord(db.Model):
    __tablename__ = 'timeline_record'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(80), db.ForeignKey('session.id'), nullable=False)
    timestamp = db.Column(db.Float, nullable=False)  # Seconds offset since start
    total = db.Column(db.Integer, nullable=False)
    listening = db.Column(db.Integer, nullable=False)
    distracted = db.Column(db.Integer, nullable=False)
    attention_rate = db.Column(db.Float, nullable=False)

