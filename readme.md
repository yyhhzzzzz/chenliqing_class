# 🏫 基于 YOLOv8 + Flask + MySQL 的智慧课堂考勤与抬头率检测系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/YOLO-v8-red.svg" alt="YOLOv8">
  <img src="https://img.shields.io/badge/Flask-Framework-green.svg" alt="Flask">
  <img src="https://img.shields.io/badge/MySQL-Database-orange.svg" alt="MySQL">
  <img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License">
</p>

🚀 **Smart-Classroom-Analytics** 是一个全栈式的智慧课堂综合管理与视觉分析平台。系统利用 **YOLOv8** 目标检测与人脸特征提取技术，实时识别教室内学生的听课状态与身份，并通过 **Flask** 搭建轻量化 Web 后端，结合 **MySQL** 数据持久化与 **ECharts** 可视化图表，实现精准考勤打卡及课堂专注度（抬头率）的深度量化分析。

---

## ✨ 核心功能

* **👥 精准人脸考勤**
  * **特征提取**：自动捕获人脸图像并提取 512 维特征向量。
  * **自动比对**：与 MySQL 数据库中的学生面部模板实时比对，完成精准考勤。
  * **状态记录**：自动记录学生出勤、迟到、缺勤状态，告别传统肉眼点名。
* **📊 课堂行为与状态识别**
  * 👁️ **抬头听课** (`face+eye-opened`)：处于抬头且睁眼的高专注度学习状态。
  * 📱 **低头状态** (`head-down`)：低头看书、玩手机或写字。
  * 💤 **闭眼打盹** (`face+eye-closed`)：闭眼瞌睡或趴桌睡觉。
* **📈 Web 端数据可视化面板**
  * **实时数据流**：动态显示教室当前总人数、实时出勤率与抬头率。
  * **历史趋势分析**：通过 ECharts 折线图直观展示整节课的专注度波动曲线。
  * **考勤后台管理**：支持学生信息录入、考勤历史流水查询与报表导出。

---

## 🏗️ 系统架构图

```text
  ┌─────────────────┐       ┌─────────────────────────────┐
  │ 教室摄像头视频流  │ ───>  │ YOLOv8 状态分类 + 人脸特征提取 │
  └─────────────────┘       └─────────────────────────────┘
                                           │
                                           ▼ (数据持久化)
  ┌─────────────────┐       ┌─────────────────────────────┐       ┌──────────────┐
  │  Web 浏览器前端   │ <───> │        Flask 后端服务        │ <───> │  MySQL 数据库 │
  │ (ECharts 可视化)  │       │ (RESTful API & 考勤业务逻辑)  │       │ (学生信息/流水)│
  └─────────────────┘       └─────────────────────────────┘       └──────────────┘
```

---

## 🛠️ 技术栈与依赖

* **视觉算法核心**：Python 3.9+ / PyTorch / YOLOv8 (Ultralytics) / OpenCV
* **Web 后端服务**：Flask / Flask-SQLAlchemy
* **数据存储**：MySQL 8.0+
* **前端展示**：HTML5 / CSS3 / JavaScript / ECharts

---

## 📂 项目结构

```text
├── dataset/                  # 训练数据集（包含 train/valid/data.yaml）
├── weights/                  # 存放训练好的模型权重（如 best.pt）
├── src/
│   ├── detector.py           # YOLOv8 推理与状态计数核心模块
│   ├── attendance.py         # 考勤逻辑与数据导出模块
│   └── utils.py              # 图像绘制与辅助函数
├── templates/                # Web 前端 HTML 模板
├── static/                   # 静态资源（CSS, JS, Images）
├── main.py                   # 视频流/摄像头实时检测与 Web 主程序
├── requirements.txt          # 项目依赖包
└── README.md
```
