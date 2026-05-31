# 基于 YOLOv8 的智慧课堂考勤与抬头率检测系统

🚀 **Smart-Classroom-Attendance** 是一个基于计算机视觉的智慧课堂管理系统。系统利用 **YOLOv8** 目标检测模型，实时识别教室内学生的上课状态（抬头听课、低头看书/玩手机、闭眼睡觉），并在进行人员考勤打卡的同时，自动计算并可视化输出课堂的**实时抬头率**与**专注度分析**。

---

## ✨ 核心功能

* **👥 课堂人员考勤**：实时检测教室内的人数，结合人脸/人体识别技术，统计出勤、缺勤及迟到人数。
* **📊 实时抬头率统计**：基于图像特征，动态计算：
    $$\text{实时抬头率} = \frac{\text{抬头听课人数}}{\text{教室内总人数}} \times 100\%$$
* **💤 课堂行为状态分类**：
    * `face+eye-opened`：抬头清醒听课（高专注度）。
    * `head-down`：低头看书/看手机（低头状态）。
    * `face+eye-closed`：闭眼打瞌睡/睡觉。
* **📈 数据可视化**：支持将考勤报表与听课专注度曲线导出为 Excel/实时图表（可选配 PyQT5/Web 界面）。

---

## 🛠️ 技术栈

* **核心算法**：Python 3.9+ / PyTorch / YOLOv8 (Ultralytics)
* **图像处理**：OpenCV-Python
* **数据处理**：Pandas / NumPy
* **数据集来源**：Roboflow Universe (STUDENT-ATTENTION Dataset)

---

## 📂 项目结构

```text
├── dataset/                  # 训练数据集（包含train/valid/data.yaml）
├── weights/                  # 存放训练好的模型权重（如 best.pt）
├── src/
│   ├── detector.py           # YOLOv8 推理与状态计数核心模块
│   ├── attendance.py         # 考勤逻辑与数据导出模块
│   └── utils.py              # 图像绘制与辅助函数
├── main.py                   # 视频流/摄像头实时检测主程序
├── requirements.txt          # 项目依赖包
└── README.md