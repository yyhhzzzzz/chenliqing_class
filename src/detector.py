import os

# 修复 Windows 下的 OpenMP 冲突和 DLL 加载问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import cv2
import tempfile
from ultralytics import YOLO, settings
from glob import glob

# 重定向 ultralytics 生成的 runs 文件夹到系统临时目录下，防止污染项目根目录
settings.update({'runs_dir': os.path.join(tempfile.gettempdir(), 'ultralytics_runs')})

# 听讲状态聚合字典（核心分类映射）
ATTENTION_MAPPING = {
    # 🟢 听讲中 / 抬头专注 (绿色框)
    'face-eye-opened': 'Listening',
    'raise_head': 'Listening',
    'upright': 'Listening',
    'hand-raising': 'Listening',
    'reading': 'Listening',
    'writing': 'Listening',
    'book': 'Listening',
    
    # 🔴 未听讲 / 低头分心 (红色框)
    'face-eye-closed': 'Distracted',
    'head-down': 'Distracted',
    'bow_head': 'Distracted',
    'sleep': 'Distracted',
    'Using_phone': 'Distracted',
    'turn_head': 'Distracted',
    'bend': 'Distracted',
    'phone': 'Distracted',
}

# 细分动作中文映射字典
LABEL_CN_MAPPING = {
    'face-eye-opened': '抬头听讲',
    'face-eye-closed': '闭眼打盹',
    'head-down': '低头分心',
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

class ClassroomDetector:
    def __init__(self):
        self.model = None
        self.load_model()

    def find_best_model(self):
        """
        自动定位最新训练好的最佳权重文件
        """
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        search_paths = [
            os.path.join(current_dir, "weights", "best.pt"),
            os.path.join(current_dir, "runs", "detect", "student_attention_yolov8s_1024p", "weights", "best.pt"),
            os.path.join(current_dir, "best.pt"),
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
                
        # 模糊搜索最新包含 student_attention 的 best.pt
        candidates = glob(os.path.join(current_dir, "runs", "detect", "student_attention*", "weights", "best.pt"))
        if candidates:
            candidates.sort(key=os.path.getmtime, reverse=True)
            return candidates[0]
            
        return None

    def load_model(self):
        model_path = self.find_best_model()
        if model_path:
            print(f"==================================================")
            print(f"YOLO 核心检测器加载模型: {model_path}")
            print(f"==================================================")
            self.model = YOLO(model_path)
        else:
            print("[错误] 检测器未能定位到 best.pt 权重文件，请确保路径正确。")
            self.model = None

    def predict_frame(self, frame, conf_threshold=0.30):
        """
        用于实时视频流处理的帧预测
        """
        if not self.model:
            return frame, {"total": 0, "listening": 0, "distracted": 0, "attention_rate": "0%"}

        # 1. 运行 YOLOv8 预测
        results = self.model.predict(source=frame, conf=conf_threshold, save=False, verbose=False)[0]

        COLOR_LISTENING = (0, 200, 0)      # 绿色 (BGR)
        COLOR_DISTRACTED = (0, 0, 225)     # 红色 (BGR)

        count_listening = 0
        count_distracted = 0
        
        boxes = results.boxes
        for i, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            raw_label = self.model.names[cls_id]
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()

            status = ATTENTION_MAPPING.get(raw_label, "Distracted")
            
            if status == "Listening":
                color = COLOR_LISTENING
                display_label = f"Listening {conf:.1%}"
                count_listening += 1
            else:
                color = COLOR_DISTRACTED
                display_label = f"Distracted {conf:.1%}"
                count_distracted += 1

            # 绘制检测框与状态标签
            p1, p2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
            cv2.rectangle(frame, p1, p2, color, thickness=2, lineType=cv2.LINE_AA)
            
            tf = max(2 - 1, 1)
            t_size = cv2.getTextSize(display_label, 0, fontScale=0.5, thickness=tf)[0]
            p2_txt = p1[0] + t_size[0] + 3, p1[1] - t_size[1] - 4
            cv2.rectangle(frame, p1, p2_txt, color, -1, cv2.LINE_AA)
            cv2.putText(frame, display_label, (p1[0], p1[1] - 2), 0, 0.5, (255, 255, 255), thickness=tf, lineType=cv2.LINE_AA)

        total_students = count_listening + count_distracted
        attention_rate = (count_listening / total_students * 100) if total_students > 0 else 0

        stats = {
            'total': total_students,
            'listening': count_listening,
            'distracted': count_distracted,
            'attention_rate': f"{attention_rate:.1f}%"
        }
        
        return frame, stats

    def predict(self, image_path, output_dir, conf_threshold=0.30):
        if not self.model:
            return None, "模型未加载，请确保 best.pt 存在。"

        # 1. 运行 YOLOv8 预测
        results = self.model.predict(source=image_path, conf=conf_threshold, save=False)[0]

        # 2. 读取原始图片并用 OpenCV 绘制
        img = cv2.imread(image_path)
        
        COLOR_LISTENING = (0, 200, 0)      # 绿色 (BGR)
        COLOR_DISTRACTED = (0, 0, 225)     # 红色 (BGR)

        count_listening = 0
        count_distracted = 0
        students_list = []

        boxes = results.boxes
        for i, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            raw_label = self.model.names[cls_id]
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()

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

            # 绘制检测框与状态标签
            p1, p2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
            cv2.rectangle(img, p1, p2, color, thickness=2, lineType=cv2.LINE_AA)
            
            tf = max(2 - 1, 1)
            t_size = cv2.getTextSize(display_label, 0, fontScale=0.5, thickness=tf)[0]
            p2_txt = p1[0] + t_size[0] + 3, p1[1] - t_size[1] - 4
            cv2.rectangle(img, p1, p2_txt, color, -1, cv2.LINE_AA)
            cv2.putText(img, display_label, (p1[0], p1[1] - 2), 0, 0.5, (255, 255, 255), thickness=tf, lineType=cv2.LINE_AA)

        # 3. 保存渲染标注后的图片
        unique_filename = os.path.basename(image_path)
        output_filename = f"classroom_result_{unique_filename}"
        output_path = os.path.join(output_dir, output_filename)
        cv2.imwrite(output_path, img)

        total_students = count_listening + count_distracted
        attention_rate = (count_listening / total_students * 100) if total_students > 0 else 0

        return {
            'total': total_students,
            'listening': count_listening,
            'distracted': count_distracted,
            'attention_rate': f"{attention_rate:.2f}%",
            'output_filename': output_filename,
            'students': students_list
        }, None
