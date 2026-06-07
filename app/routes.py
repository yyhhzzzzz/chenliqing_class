import os
import uuid
import json
import time
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, url_for, Response, redirect, session, current_app
from app.models import db, User, StudentClass, Course, Student, Session, TimelineRecord
from werkzeug.security import check_password_hash
from app.camera import class_state, latest_camera_stats, generate_frames

main_bp = Blueprint('main', __name__)

# 路由身份鉴权装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # 对于异步接口，返回 401 状态码，而非重定向页面
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/') or request.path in ['/start_class', '/end_class', '/predict', '/latest_stats']:
                return jsonify({'error': 'Unauthorized. Please login.'}), 401
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== 认证路由 ====================

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('main.index'))
        
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            # 更新 CSRF token 防止会话固定攻击
            import secrets
            session['csrf_token'] = secrets.token_hex(32)
            return redirect(url_for('main.index'))
        else:
            error = '用户名或密码错误！'
            
    return render_template('login.html', error=error)

@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

# ==================== 系统业务路由 ====================

@main_bp.route('/')
@login_required
def index():
    return render_template('index.html')

@main_bp.route('/get_status')
@login_required
def get_status():
    """获取当前课堂实时状态"""
    return jsonify({
        "is_active": class_state['is_active'],
        "session_id": class_state['session_id'],
        "start_time": class_state['start_time'],
        "class_id": class_state.get('class_id'),
        "course_id": class_state.get('course_id')
    })

@main_bp.route('/admin')
@login_required
def admin():
    """管理端页面"""
    return render_template('admin.html')

@main_bp.route('/api/classes')
@login_required
def get_classes():
    """获取所有班级列表"""
    classes = StudentClass.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in classes])

@main_bp.route('/api/courses')
@login_required
def get_courses():
    """获取所有学科列表"""
    courses = Course.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in courses])

@main_bp.route('/api/reports')
@login_required
def get_reports():
    """获取所有历史报告列表，支持按班级和学科过滤"""
    class_id = request.args.get('class_id', type=int)
    course_id = request.args.get('course_id', type=int)
    
    query = Session.query
    if class_id:
        query = query.filter_by(class_id=class_id)
    if course_id:
        query = query.filter_by(course_id=course_id)
        
    sessions = query.order_by(Session.start_time.desc()).all()
    
    reports = []
    for s in sessions:
        reports.append({
            "session_id": s.id,
            "class_id": s.class_id,
            "class_name": s.student_class.name if s.student_class else "未知班级",
            "course_id": s.course_id,
            "course_name": s.course.name if s.course else "未知学科",
            "date": s.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": s.duration_seconds,
            "avg_attention_rate": f"{s.avg_attention_rate:.1f}%",
            "max_students_count": s.max_students_count,
            "data_points": len(s.timeline_records)
        })
    return jsonify(reports)

@main_bp.route('/api/reports/<session_id>/timeline')
@login_required
def get_report_timeline(session_id):
    """获取某场课堂的详细时序数据"""
    records = TimelineRecord.query.filter_by(session_id=session_id).order_by(TimelineRecord.timestamp).all()
    return jsonify([{
        "timestamp": r.timestamp,
        "total": r.total,
        "listening": r.listening,
        "distracted": r.distracted,
        "attention_rate": r.attention_rate
    } for r in records])

@main_bp.route('/api/analytics/class_compare')
@login_required
def get_class_compare():
    """统计各班级的平均抬头率与出勤人数"""
    results = db.session.query(
        StudentClass.name,
        db.func.avg(Session.avg_attention_rate),
        db.func.avg(Session.max_students_count)
    ).join(Session, Session.class_id == StudentClass.id).group_by(StudentClass.id).all()
    
    return jsonify([{
        "class_name": r[0],
        "avg_attention_rate": round(r[1], 1) if r[1] is not None else 0.0,
        "avg_max_students": round(r[2], 1) if r[2] is not None else 0.0
    } for r in results])

@main_bp.route('/api/analytics/course_compare')
@login_required
def get_course_compare():
    """统计各学科的平均抬头率"""
    results = db.session.query(
        Course.name,
        db.func.avg(Session.avg_attention_rate)
    ).join(Session, Session.course_id == Course.id).group_by(Course.id).all()
    
    return jsonify([{
        "course_name": r[0],
        "avg_attention_rate": round(r[1], 1) if r[1] is not None else 0.0
    } for r in results])

@main_bp.route('/start_class', methods=['POST'])
@login_required
def start_class():
    """开始上课逻辑 (保存班级与学科信息)"""
    if not class_state['is_active']:
        class_id = request.form.get('class_id', type=int)
        course_id = request.form.get('course_id', type=int)
        
        if not class_id or not course_id:
            return jsonify({"status": "error", "message": "请选择授课班级和学科！"}), 400
            
        # 验证班级与学科是否存在
        school_class = StudentClass.query.get(class_id)
        course = Course.query.get(course_id)
        if not school_class or not course:
            return jsonify({"status": "error", "message": "班级或学科数据不存在！"}), 400
            
        class_state['is_active'] = True
        class_state['start_time'] = time.time()
        class_state['session_id'] = str(uuid.uuid4())[:8]
        class_state['class_id'] = class_id
        class_state['course_id'] = course_id
        class_state['history_stats'] = []
        print(f"[{datetime.now()}] 🔔 课堂开始！Session ID: {class_state['session_id']}, 班级: {school_class.name}, 学科: {course.name}")
        
    return jsonify({"status": "success", "session_id": class_state['session_id']})

@main_bp.route('/end_class', methods=['POST'])
@login_required
def end_class():
    """下课逻辑：保存汇总指标至 Session 表，并批量导入时序 TimelineRecord"""
    if class_state['is_active']:
        class_state['is_active'] = False
        end_time = time.time()
        duration = end_time - class_state['start_time']
        
        # 计算整节课的汇总数据
        history = class_state['history_stats']
        if history:
            avg_attention = sum([float(s['attention_rate'].replace('%','')) for s in history]) / len(history)
            max_students = max([s['total'] for s in history])
        else:
            avg_attention = 0.0
            max_students = 0

        try:
            # 1. 存储 Session 汇总记录
            new_session = Session(
                id=class_state['session_id'],
                class_id=class_state['class_id'],
                course_id=class_state['course_id'],
                teacher_id=session['user_id'],
                start_time=datetime.fromtimestamp(class_state['start_time']),
                end_time=datetime.fromtimestamp(end_time),
                duration_seconds=round(duration, 2),
                avg_attention_rate=round(avg_attention, 1),
                max_students_count=max_students
            )
            db.session.add(new_session)
            
            # 2. 存储 Timeline 详细时序记录
            start_t = class_state['start_time']
            for i, pt in enumerate(history):
                rate = float(pt['attention_rate'].replace('%', ''))
                # 记录相对上课时间的秒数偏移
                time_offset = round(i + 1.0, 1)
                record = TimelineRecord(
                    session_id=class_state['session_id'],
                    timestamp=time_offset,
                    total=pt['total'],
                    listening=pt['listening'],
                    distracted=pt['distracted'],
                    attention_rate=rate
                )
                db.session.add(record)
                
            db.session.commit()
            
            # 同时保留一份 JSON 备份以确保向后兼容 (安全地保存到 reports/ 目录下)
            report = {
                "session_id": class_state['session_id'],
                "class_name": new_session.student_class.name,
                "course_name": new_session.course.name,
                "date": new_session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": new_session.duration_seconds,
                "avg_attention_rate": f"{new_session.avg_attention_rate:.1f}%",
                "max_students_count": new_session.max_students_count,
                "data_points": len(history)
            }
            report_dir = os.path.join(os.getcwd(), "reports")
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f"report_{class_state['session_id']}.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            db.session.rollback()
            print(f"[错误] 无法保存课堂报告到数据库: {e}")
            return jsonify({"status": "error", "message": f"无法保存报告: {e}"}), 500

        print(f"\n{'='*40}")
        print(f"📊 课堂报告已成功同步到 SQLite 数据库！")
        print(f"平均抬头率: {report['avg_attention_rate']}")
        print(f"上课时长: {report['duration_seconds']} 秒")
        print(f"{'='*40}\n")

        return jsonify({"status": "success", "report": report})
    
    return jsonify({"status": "error", "message": "课堂尚未开始"})

@main_bp.route('/latest_stats')
@login_required
def get_latest_stats():
    """获取最新的摄像头统计数据"""
    return jsonify(latest_camera_stats)

@main_bp.route('/video_feed')
@login_required
def video_feed():
    """视频流路由"""
    return Response(generate_frames(current_app.camera_manager), mimetype='multipart/x-mixed-replace; boundary=frame')

@main_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    detector = current_app.detector
    if detector.model is None:
        return jsonify({'error': 'YOLO 模型未成功加载，请检查 weights/best.pt 文件。'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '请求包中未找到图片文件。'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择任何有效图片。'}), 400

    # 1. 自动生成随机唯一文件名，保存原图到上传文件夹
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(upload_path)

    # 2. 读取配置 of 置信度阈值 (默认为 0.30)
    conf_threshold = float(request.form.get('conf', 0.30))

    # 3. 调用核心模块进行推理绘制
    result_data, error_msg = detector.predict(
        image_path=upload_path,
        output_dir=current_app.config['OUTPUT_FOLDER'],
        conf_threshold=conf_threshold
    )

    if error_msg:
        return jsonify({'error': error_msg}), 500

    # 4. 封装结果返回 JSON
    return jsonify({
        'success': True,
        'total': result_data['total'],
        'listening': result_data['listening'],
        'distracted': result_data['distracted'],
        'attention_rate': result_data['attention_rate'],
        'uploaded_image_url': url_for('static', filename=f'uploads/{unique_filename}'),
        'result_image_url': url_for('static', filename=f'outputs/{result_data["output_filename"]}'),
        'students': result_data['students']
    })

@main_bp.route('/api/classes', methods=['POST'])
@login_required
def create_class():
    """新增班级 API"""
    name = request.form.get('name')
    if not name or not name.strip():
        return jsonify({"status": "error", "message": "班级名称不能为空"}), 400
        
    name = name.strip()
    # 检查是否重复
    existing = StudentClass.query.filter_by(name=name).first()
    if existing:
        return jsonify({"status": "error", "message": "该班级已存在"}), 400
        
    try:
        new_class = StudentClass(name=name)
        db.session.add(new_class)
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": "班级添加成功", 
            "class": {"id": new_class.id, "name": new_class.name}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"保存班级失败: {e}"}), 500

@main_bp.route('/api/students', methods=['POST'])
@login_required
def create_student():
    """新增学生 API"""
    name = request.form.get('name')
    class_id = request.form.get('class_id', type=int)
    student_number = request.form.get('student_number')
    
    if not name or not name.strip() or not class_id:
        return jsonify({"status": "error", "message": "学生姓名和所属班级不能为空"}), 400
        
    name = name.strip()
    student_number = student_number.strip() if student_number else None
    
    # 验证班级是否存在
    school_class = StudentClass.query.get(class_id)
    if not school_class:
        return jsonify({"status": "error", "message": "所选班级不存在"}), 400
        
    if student_number:
        # 验证学号是否重复
        existing = Student.query.filter_by(student_number=student_number).first()
        if existing:
            return jsonify({"status": "error", "message": "学号已被其他学生占用"}), 400
            
    try:
        new_student = Student(name=name, class_id=class_id, student_number=student_number)
        db.session.add(new_student)
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": "学生添加成功", 
            "student": {"id": new_student.id, "name": new_student.name}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"保存学生失败: {e}"}), 500
