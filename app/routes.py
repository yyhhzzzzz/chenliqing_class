import os
import uuid
import json
import time
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, url_for, Response, redirect, session, current_app
from app.models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
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
        "start_time": class_state['start_time']
    })

@main_bp.route('/admin')
@login_required
def admin():
    """管理端页面"""
    return render_template('admin.html')

@main_bp.route('/api/reports')
@login_required
def get_reports():
    """获取所有历史报告列表"""
    report_dir = os.path.join(os.getcwd(), "reports")
    if not os.path.exists(report_dir):
        return jsonify([])
    
    reports = []
    for filename in os.listdir(report_dir):
        if filename.endswith('.json'):
            path = os.path.join(report_dir, filename)
            with open(path, 'r', encoding='utf-8') as f:
                reports.append(json.load(f))
    
    # 按日期降序排列
    reports.sort(key=lambda x: x.get('date', ''), reverse=True)
    return jsonify(reports)

@main_bp.route('/start_class', methods=['POST'])
@login_required
def start_class():
    """开始上课逻辑"""
    if not class_state['is_active']:
        class_state['is_active'] = True
        class_state['start_time'] = time.time()
        class_state['session_id'] = str(uuid.uuid4())[:8]
        class_state['history_stats'] = []
        print(f"[{datetime.now()}] 🔔 课堂开始！Session ID: {class_state['session_id']}")
    return jsonify({"status": "success", "session_id": class_state['session_id']})

@main_bp.route('/end_class', methods=['POST'])
@login_required
def end_class():
    """下课逻辑：统计数据并“发送”到管理端"""
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
            avg_attention = 0
            max_students = 0

        # 生成报告
        report = {
            "session_id": class_state['session_id'],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(duration, 2),
            "avg_attention_rate": f"{avg_attention:.1f}%",
            "max_students_count": max_students,
            "data_points": len(history)
        }

        # 模拟“发送到管理端”：保存到本地文件并打印日志
        report_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"report_{class_state['session_id']}.json")
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[错误] 无法保存课堂报告: {e}")
            return jsonify({"status": "error", "message": f"无法保存报告: {e}"}), 500

        print(f"\n{'='*40}")
        print(f"📊 课堂报告已生成并发送至管理端！")
        print(f"平均抬头率: {report['avg_attention_rate']}")
        print(f"上课时长: {report['duration_seconds']} 秒")
        print(f"报告路径: {report_path}")
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
