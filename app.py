import os
import cv2
import uuid
from flask import Flask, render_template, request, jsonify, url_for
from ultralytics import YOLO
from glob import glob

app = Flask(__name__)

# 配置静态目录下的上传与输出目录
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(app.root_path, 'static', 'outputs')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 听讲状态聚合字典（核心分类映射）
ATTENTION_MAPPING = {
    # 🟢 听讲中 / 抬头专注 (绿色框)
    'raise_head': 'Listening',
    'upright': 'Listening',
    'hand-raising': 'Listening',
    'reading': 'Listening',
    'writing': 'Listening',
    'book': 'Listening',
    
    # 🔴 未听讲 / 低头分心 (红色框)
    'bow_head': 'Distracted',
    'sleep': 'Distracted',
    'Using_phone': 'Distracted',
    'turn_head': 'Distracted',
    'bend': 'Distracted',
    'phone': 'Distracted',
}

# 细分动作中文映射字典
LABEL_CN_MAPPING = {
    'raise_head': '抬头听讲',
    'upright': '端正坐姿',
    'hand-raising': '举手提问',
    'reading': '看书阅读',
    'writing': '伏案书写',
    'book': '书本课本',
    'bow_head': '低头分心',
    'sleep': '趴桌睡觉',
    'Using_phone': '玩手机',
    'turn_head': '东张西望',
    'bend': '弯腰侧身',
    'phone': '手机设备',
}

def find_best_model():
    """
    自动定位最新训练好的最佳权重文件
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
        os.path.join(current_dir, "weights", "best.pt"),
        os.path.join(current_dir, "runs", "detect", "runs", "detect", "student_attention_yolov8s_1024p", "weights", "best.pt"),
        os.path.join(current_dir, "runs", "detect", "student_attention_yolov8s_1024p", "weights", "best.pt"),
        os.path.join(current_dir, "best.pt"),
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            return path
            
    # 模糊搜索最新包含 student_attention 的 best.pt
    candidates = glob(os.path.join(current_dir, "runs", "detect", "runs", "detect", "student_attention*", "weights", "best.pt"))
    if candidates:
        candidates.sort(key=os.path.getmtime, reverse=True)
        return candidates[0]
        
    return None

# 预先加载 YOLO 模型以缩短接口响应时间
model_path = find_best_model()
if model_path:
    print(f"==================================================")
    print(f"Flask 正在加载课堂检测模型: {model_path}")
    print(f"==================================================")
    model = YOLO(model_path)
else:
    print("[错误] 未找到任何训练好的 best.pt 权重文件，请确保模型已存在。")
    model = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'YOLO 模型未成功加载，请检查 best.pt 权重文件是否存在。'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '请求包中未找到图片文件。'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择任何有效图片。'}), 400

    # 1. 自动生成随机唯一文件名，保存原图
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(upload_path)

    # 2. 读取配置的置信度阈值 (默认为 0.30)
    conf_threshold = float(request.form.get('conf', 0.30))

    # 3. 运行模型预测
    results = model.predict(source=upload_path, conf=conf_threshold, save=False)[0]

    # 4. 用 OpenCV 绘制二分类结果
    img = cv2.imread(upload_path)
    
    COLOR_LISTENING = (0, 200, 0)      # 绿色 (BGR)
    COLOR_DISTRACTED = (0, 0, 225)     # 红色 (BGR)

    count_listening = 0
    count_distracted = 0
    students_list = []

    boxes = results.boxes
    for i, box in enumerate(boxes):
        cls_id = int(box.cls[0])
        raw_label = model.names[cls_id]  # 原始标签 (如 bow_head, upright 等)
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].tolist()      # 坐标

        # 二分类映射判定
        status = ATTENTION_MAPPING.get(raw_label, "Distracted")
        
        if status == "Listening":
            color = COLOR_LISTENING
            display_label = f"Listening {conf:.1%}"
            count_listening += 1
        else:
            color = COLOR_DISTRACTED
            display_label = f"Distracted {conf:.1%}"
            count_distracted += 1

        students_list.append({
            'id': i + 1,
            'status': status,
            'status_cn': '听讲中' if status == 'Listening' else '分心中',
            'raw_label': raw_label,
            'label_cn': LABEL_CN_MAPPING.get(raw_label, raw_label),
            'confidence': f"{conf:.2%}",
            'bbox': [int(val) for val in xyxy]
        })

        # 绘制检测框与状态文字
        p1, p2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
        cv2.rectangle(img, p1, p2, color, thickness=2, lineType=cv2.LINE_AA)
        
        tf = max(2 - 1, 1)
        t_size = cv2.getTextSize(display_label, 0, fontScale=0.5, thickness=tf)[0]
        p2_txt = p1[0] + t_size[0] + 3, p1[1] - t_size[1] - 4
        cv2.rectangle(img, p1, p2_txt, color, -1, cv2.LINE_AA)
        cv2.putText(img, display_label, (p1[0], p1[1] - 2), 0, 0.5, (255, 255, 255), thickness=tf, lineType=cv2.LINE_AA)

    # 5. 保存渲染标记后的输出图片
    output_filename = f"classroom_result_{unique_filename}"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    cv2.imwrite(output_path, img)

    total_students = count_listening + count_distracted
    attention_rate = (count_listening / total_students * 100) if total_students > 0 else 0

    return jsonify({
        'success': True,
        'total': total_students,
        'listening': count_listening,
        'distracted': count_distracted,
        'attention_rate': f"{attention_rate:.2f}%",
        'uploaded_image_url': url_for('static', filename=f'uploads/{unique_filename}'),
        'result_image_url': url_for('static', filename=f'outputs/{output_filename}'),
        'students': students_list
    })

if __name__ == '__main__':
    # 绑定 5001 端口，避开 macOS 默认的 AirPlay Receiver (5000 端口)
    app.run(host='0.0.0.0', port=5001, debug=True)
