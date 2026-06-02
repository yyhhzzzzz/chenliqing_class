import os
from ultralytics import YOLO

def train_model():
    # 1. 获取数据集配置文件 data.yaml 的绝对路径
    # 使用绝对路径可以有效避免 YOLOv8 训练时找不到数据集路径的问题
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_yaml_path = os.path.join(
        current_dir, 
        "dataset", 
        "Student Behaviour Detection.v6i.yolov8", 
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
        epochs=300,          # 既然有1天时间，直接拉到 300 轮（配合 patience 早停机制，绝不会白白浪费时间）
        patience=50,         # 50 轮内 mAP 精度不再提升，则自动提前终止训练，防止过拟合
    
    # 👁️ 【核心精度调优：分辨率与批次的博弈】
        imgsz=1024,          # 🔥 关键提升！将分辨率从 640 提升到 1024，大幅增强后排小人头/低头动作的识别率
        batch=4,             # ⚠️ 配合 1024 分辨率，8GB 显存极限大概只能开到 batch=8 (如果报错 OOM，请降为 4)
    
    # ⚙️ 【系统性能调优：榨干 IO 速度】
        device=0,            # 使用首张 GPU
        workers=0,           # Windows 下设为 4。如果训练中出现 DataLoader 报错，再改回 0
        cache='disk',        # 推荐使用 'disk'（缓存到硬盘）。如果你的电脑内存大于 32GB，可以设为 True（纯内存缓存，飞快）
    
    # 🧠 【高级训练技巧：适合长时间训练的魔法参数】
        cos_lr=True,         # 开启余弦退火学习率：学习率会像波浪一样平滑下降，适合 300 轮的长线作战，能寻找到更好的最优解
        close_mosaic=20,     # 在最后 20 轮关闭马赛克数据增强：让模型在最后阶段看“真实的完整教室”，对最终精度提升极大
        project="runs/detect",
        name="student_attention_yolov8s_1024p"
    )
    
    print("模型训练完成！")
    print(f"训练结果与最佳模型权重已保存至: {results.save_dir}")

if __name__ == "__main__":
    train_model()
