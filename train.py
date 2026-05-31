import os
from ultralytics import YOLO

def train_model():
    # 1. 获取数据集配置文件 data.yaml 的绝对路径
    # 使用绝对路径可以有效避免 YOLOv8 训练时找不到数据集路径的问题
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_yaml_path = os.path.join(
        current_dir, 
        "dataset", 
        "STUDENT-ATTENTION.v2-v2.yolov8", 
        "data.yaml"
    )
    
    print(f"正在加载数据集配置: {dataset_yaml_path}")
    
    # 2. 加载预训练的 YOLOv8 目标检测模型（使用 small 版本，平衡精度与速度）
    # 对于 2080S (8GB)，使用 yolov8s.pt 效果相比 yolov8n.pt 会有显著提升
    model = YOLO("yolov8s.pt")
    
    # 3. 开始模型训练
    # 针对 RTX 2080 Super 优化的训练配置
    results = model.train(
        data=dataset_yaml_path,
        epochs=200,          # 训练 200 轮
        patience=50,         # 50 轮精度未提升则自动提前终止（早停）
        imgsz=640,           # 输入分辨率 640
        batch=32,            # 8GB 显存推荐批大小为 32
        device=0,            # 使用首张 GPU 进行训练
        workers=4,           # Windows 环境下建议设置 4 个数据加载线程
        cache=True,          # 缓存数据集至内存，减少硬盘I/O，加快训练速度
        project="runs/detect",
        name="student_attention_yolov8s"
    )
    
    print("模型训练完成！")
    print(f"训练结果与最佳模型权重已保存至: {results.save_dir}")

if __name__ == "__main__":
    train_model()
