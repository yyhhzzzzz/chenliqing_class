import os
from ultralytics import YOLO

def test_model_accuracy():
    # 1. 确定当前项目路径与最佳模型权重路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 指向您训练好的最佳权重。
    # 请确认 runs 目录下的最佳权重路径。通常位于下述路径：
    # 优先查找训练好的 yolov8s 权重，其次查找 yolov8n
    possible_paths = [
        os.path.join(current_dir, "runs", "detect", "student_attention_yolov8s", "weights", "best.pt"),
        os.path.join(current_dir, "runs", "detect", "runs", "detect", "student_attention_yolov8s", "weights", "best.pt"),
        os.path.join(current_dir, "runs", "detect", "runs", "detect", "student_attention_yolov8n", "weights", "best.pt"),
    ]
    
    best_model_path = None
    for path in possible_paths:
        if os.path.exists(path):
            best_model_path = path
            break
            
    if best_model_path is None:
        print(f"提示: 未在 runs 目录下找到训练好的 best.pt 权重。")
        best_model_path = os.path.join(current_dir, "best.pt")
        if not os.path.exists(best_model_path):
            best_model_path = os.path.join(current_dir, "yolo26n.pt")
            print(f"将使用未训练的预训练模型 {best_model_path} 进行测试。")
            
    print(f"正在加载模型: {best_model_path}")
    model = YOLO(best_model_path)

    # ==========================================
    # 测试方式一：使用验证集进行批量准确度评估 (Evaluation)
    # ==========================================
    print("\n--- 正在评估模型在验证集上的准确度指标 (mAP/Precision/Recall) ---")
    dataset_yaml_path = os.path.join(
        current_dir, "dataset", "STUDENT-ATTENTION.v2-v2.yolov8", "data.yaml"
    )
    
    # 运行评估
    metrics = model.val(data=dataset_yaml_path)
    
    print("\n--- 验证集准确度结果如下： ---")
    print(f"整体 mAP50:     {metrics.box.map50:.4f}  (越大越好，接近1为完美)")
    print(f"整体 mAP50-95:  {metrics.box.map:.4f}   (严苛指标，越大越好)")
    print(f"精准率 Precision: {metrics.box.mp:.4f}    (预测出的框中对的比例)")
    print(f"召回率 Recall:    {metrics.box.mr:.4f}    (所有真实目标中找出来的比例)")

    # ==========================================
    # 测试方式二：使用单张图片进行可视化预测并保存结果 (Inference)
    # ==========================================
    print("\n--- 正在使用测试集中的单张图片进行可视化测试 ---")
    
    # 指定测试集目录下的某一张图片路径
    test_image_dir = os.path.join(
        current_dir, "dataset", "STUDENT-ATTENTION.v2-v2.yolov8", "test", "images"
    )
    
    # 获取测试目录下所有的图片名
    if os.path.exists(test_image_dir):
        images = [f for f in os.listdir(test_image_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        if images:
            # 选取第一张图片进行测试
            target_image = os.path.join(test_image_dir, images[0])
            print(f"选取测试图片: {target_image}")
            
            # 运行预测并保存带有边框的图片
            # save=True 会将画有预测边框的图片保存到 runs/detect/predict 目录下
            results = model.predict(source=target_image, save=True, conf=0.25)
            
            # 输出预测的具体框信息
            for result in results:
                print(f"预测出目标数量: {len(result.boxes)}")
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    label = model.names[cls_id]
                    conf = float(box.conf[0])
                    print(f" - 目标类别: {label}, 置信度: {conf:.2f}")
            
            print(f"\n可视化预测图片已保存至: {results[0].save_dir}")
        else:
            print("测试图片目录下未找到图片。")
    else:
        print(f"未找到测试图片目录: {test_image_dir}")

if __name__ == "__main__":
    test_model_accuracy()
