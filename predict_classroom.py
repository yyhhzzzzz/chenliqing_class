import os
import argparse
import cv2
from glob import glob
from ultralytics import YOLO

# ==================================================
# 听讲状态聚合字典（核心分类映射）
# ==================================================
ATTENTION_MAPPING = {
    # 🟢 听讲中 / 抬头专注 (绿色框)
    'raise_head': 'Listening',
    'upright': 'Listening',
    'hand-raising': 'Listening',
    'reading': 'Listening',
    'writing': 'Listening',
    
    # 🔴 未听讲 / 低头分心 (红色框)
    'bow_head': 'Distracted',
    'sleep': 'Distracted',
    'Using_phone': 'Distracted',
    'turn_head': 'Distracted',
    'bend': 'Distracted',
    
    # 物品类目标不做直接行为框，但在此分类中为了稳妥可以归为分心或略过
    'phone': 'Distracted',
    'book': 'Listening'
}

def find_best_model():
    """
    自动定位最新训练好的 1024p 最佳权重文件
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
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

def main():
    parser = argparse.ArgumentParser(description="YOLOv8 教室学生听讲/低头分心二分类检测脚本")
    parser.add_argument(
        "--source", 
        type=str, 
        default="", 
        help="待测试的教室图片路径。若不指定，将自动使用测试集中的第一张图片。"
    )
    parser.add_argument(
        "--conf", 
        type=float, 
        default=0.30, 
        help="检测置信度阈值 (默认 0.30)"
    )
    args = parser.parse_args()

    # 1. 查找并加载最佳权重
    model_path = find_best_model()
    if not model_path:
        print("[错误] 未找到任何训练好的 best.pt 权重文件，请确保训练已完成并生成了 runs 目录。")
        return
        
    print(f"==================================================")
    print(f"正在加载课堂检测模型: {model_path}")
    print(f"==================================================")
    
    model = YOLO(model_path)

    # 2. 定位图片路径
    image_path = args.source
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    if not image_path:
        # 默认去新数据集的测试文件夹下找图片
        default_test_dir = os.path.join(
            current_dir, "dataset", "Student Behaviour Detection.v6i.yolov8", "test", "images"
        )
        if os.path.exists(default_test_dir):
            supported_formats = (".jpg", ".jpeg", ".png", ".bmp")
            images = [f for f in os.listdir(default_test_dir) if f.lower().endswith(supported_formats)]
            if images:
                image_path = os.path.join(default_test_dir, images[0])
                print(f"未指定图片，已自动选择测试集图片: {image_path}")
            
    if not image_path or not os.path.exists(image_path):
        print(f"[错误] 图片路径无效或不存在: {image_path}")
        return

    # 3. 运行模型预测
    results = model.predict(source=image_path, conf=args.conf, save=False)[0]

    # 4. 读取原始图片进行自定义的高级渲染绘制
    img = cv2.imread(image_path)
    h, w, _ = img.shape
    
    # 颜色配置 (BGR格式)：听讲中为绿色，分心低头为红色
    COLOR_LISTENING = (0, 200, 0)      # 绿色
    COLOR_DISTRACTED = (0, 0, 225)     # 红色
    
    count_listening = 0
    count_distracted = 0

    print(f"\n================ 检测与分类统计 ================")
    
    # 遍历所有边界框进行映射和分类渲染
    boxes = results.boxes
    for i, box in enumerate(boxes):
        cls_id = int(box.cls[0])
        raw_label = model.names[cls_id]  # 原始 12 分类标签
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].tolist()      # 坐标：[xmin, ymin, xmax, ymax]
        
        # 获取映射状态
        status = ATTENTION_MAPPING.get(raw_label, "Distracted")
        
        # 确定绘制颜色和显示文案
        if status == "Listening":
            color = COLOR_LISTENING
            display_label = f"Listening {conf:.1%}"
            count_listening += 1
        else:
            color = COLOR_DISTRACTED
            display_label = f"Distracted ({raw_label}) {conf:.1%}"
            count_distracted += 1
            
        # 打印至控制台
        print(f"  学生 [{i+1:<2}] 行为: {raw_label:<14} -> 状态判定: {status:<10} (置信度: {conf:.2%})")

        # 绘制边界框
        p1, p2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
        cv2.rectangle(img, p1, p2, color, thickness=2, lineType=cv2.LINE_AA)
        
        # 绘制标签背景框
        tf = max(2 - 1, 1)  # 字体粗细
        t_size = cv2.getTextSize(display_label, 0, fontScale=0.5, thickness=tf)[0]
        p2_txt = p1[0] + t_size[0] + 3, p1[1] - t_size[1] - 4
        cv2.rectangle(img, p1, p2_txt, color, -1, cv2.LINE_AA)  # 填充背景色
        
        # 绘制标签文字
        cv2.putText(img, display_label, (p1[0], p1[1] - 2), 0, 0.5, (255, 255, 255), thickness=tf, lineType=cv2.LINE_AA)

    total_students = count_listening + count_distracted
    attention_rate = (count_listening / total_students * 100) if total_students > 0 else 0
    
    print(f"------------------------------------------------")
    print(f" 📊 全班听讲统计汇总:")
    print(f"  - 总人数: {total_students} 人")
    print(f"  - 听讲中 (🟢 Listening): {count_listening} 人")
    print(f"  - 分心中 (🔴 Distracted): {count_distracted} 人")
    print(f"  - 班级整体专注率: {attention_rate:.2f}%")
    print(f"================================================")

    # 5. 保存高级标注图片
    output_dir = os.path.join(current_dir, "runs", "detect", "predict_classroom")
    os.makedirs(output_dir, exist_ok=True)
    
    image_name = os.path.basename(image_path)
    output_path = os.path.join(output_dir, f"classroom_result_{image_name}")
    cv2.imwrite(output_path, img)
    
    print(f"\n🎉 专属课堂检测渲染图片已成功保存至:\n{output_path}")

if __name__ == "__main__":
    main()
