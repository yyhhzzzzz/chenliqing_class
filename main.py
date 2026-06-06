import os

# 修复 Windows 下的 OpenMP 冲突和 DLL 加载问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import uuid
import cv2
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for, Response
from src.detector import ClassroomDetector

app = Flask(__name__)

# 配置静态目录下的上传与输出目录
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(app.root_path, 'static', 'outputs')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 实例化核心 YOLOv8 检测器
detector = ClassroomDetector()

# 全局变量用于存储课堂状态和统计数据
class_state = {
    'is_active': False,
    'start_time': None,
    'session_id': None,
    'history_stats': [],  # 存储每秒的统计快照
    'last_sample_time': 0
}

latest_camera_stats = {
    'total': 0,
    'listening': 0,
    'distracted': 0,
    'attention_rate': "0.0%"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_status')
def get_status():
    """获取当前课堂实时状态"""
    return jsonify({
        "is_active": class_state['is_active'],
        "session_id": class_state['session_id'],
        "start_time": class_state['start_time']
    })

@app.route('/admin')
def admin():
    """管理端页面"""
    return render_template('admin.html')

@app.route('/api/reports')
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

@app.route('/start_class', methods=['POST'])
def start_class():
    """开始上课逻辑"""
    if not class_state['is_active']:
        class_state['is_active'] = True
        class_state['start_time'] = time.time()
        class_state['session_id'] = str(uuid.uuid4())[:8]
        class_state['history_stats'] = []
        print(f"[{datetime.now()}] 🔔 课堂开始！Session ID: {class_state['session_id']}")
    return jsonify({"status": "success", "session_id": class_state['session_id']})

@app.route('/end_class', methods=['POST'])
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
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        print(f"\n{'='*40}")
        print(f"📊 课堂报告已生成并发送至管理端！")
        print(f"平均抬头率: {report['avg_attention_rate']}")
        print(f"上课时长: {report['duration_seconds']} 秒")
        print(f"报告路径: {report_path}")
        print(f"{'='*40}\n")

        return jsonify({"status": "success", "report": report})
    
    return jsonify({"status": "error", "message": "课堂尚未开始"})

def generate_frames():
    global latest_camera_stats
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # 只有在上课状态下才进行 AI 识别并记录数据
            if class_state['is_active']:
                annotated_frame, stats = detector.predict_frame(frame, conf_threshold=0.3)
                latest_camera_stats = stats
                
                # 每秒采集一次统计样本，避免内存占用过大
                current_time = time.time()
                if current_time - class_state['last_sample_time'] >= 1.0:
                    class_state['history_stats'].append(stats)
                    class_state['last_sample_time'] = current_time
            else:
                # 非上课状态仅显示原始画面，不消耗 AI 算力
                annotated_frame = frame
                latest_camera_stats = {'total': 0, 'listening': 0, 'distracted': 0, 'attention_rate': "0.0%"}

            # 编码推流
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    camera.release()

@app.route('/latest_stats')
def get_latest_stats():
    """获取最新的摄像头统计数据"""
    return jsonify(latest_camera_stats)

@app.route('/video_feed')
def video_feed():
    """视频流路由"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/predict', methods=['POST'])
def predict():
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
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(upload_path)

    # 2. 读取配置的置信度阈值 (默认为 0.30)
    conf_threshold = float(request.form.get('conf', 0.30))

    # 3. 调用核心模块进行推理绘制
    result_data, error_msg = detector.predict(
        image_path=upload_path,
        output_dir=app.config['OUTPUT_FOLDER'],
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

if __name__ == '__main__':
    # 打印管理端专用链接
    print(f"\n{'='*50}")
    print(f"🚀 系统已启动！")
    print(f"🔗 前端监控页面: http://localhost:5001")
    print(f"🔐 管理端专用链接: http://localhost:5001/admin")
    print(f"{'='*50}\n")
    
    # 绑定 5001 端口，避开 macOS 默认的 AirPlay Receiver (5000 端口)
    # TODO(security): Bind to localhost for security during testing/dev
    app.run(host='127.0.0.1', port=5001, debug=True)
