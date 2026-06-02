import os
import uuid
from flask import Flask, render_template, request, jsonify, url_for
from src.detector import ClassroomDetector

app = Flask(__name__)

# 配置静态目录下的上传与输出目录
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(app.root_path, 'static', 'outputs')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 实例化核心 YOLOv8 检测器
detector = ClassroomDetector()

@app.route('/')
def index():
    return render_template('index.html')

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
    # 绑定 5001 端口，避开 macOS 默认的 AirPlay Receiver (5000 端口)
    app.run(host='0.0.0.0', port=5001, debug=True)
