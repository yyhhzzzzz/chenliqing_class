# 🏫 基于 YOLOv8 + Flask + SQLite 的智慧课堂专注度检测系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/YOLO-v8-red.svg" alt="YOLOv8">
  <img src="https://img.shields.io/badge/Flask-Framework-green.svg" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-Database-lightgrey.svg" alt="SQLite">
  <img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License">
</p>

🚀 **Smart-Classroom-Analytics** 是一个全栈式的智慧课堂综合管理与视觉分析平台。系统利用 **YOLOv8** 目标检测与分类技术，实时检测教室内学生的听课动作状态，并通过 **Flask** 搭建轻量化 Web 后端，结合 **SQLite** 本地数据持久化与 **ECharts** 可视化图表，实现精美白微光玻璃态风格的前后端交互与专注度（抬头率）的深度量化分析。

## ✨ 核心功能




* **🔐 教师身份鉴权与安全会话**
  * **登录验证**：通过本地 SQLite 数据库进行教师账户登录，密码采用 `werkzeug.security` 的强加盐哈希算法存储。
  * **自动播种**：系统首次启动时若数据库为空，会自动播种默认管理员账号 `admin` / `admin123`。
  * **会话安全**：登录凭证采用 `HttpOnly` 防止 XSS 挟持，并配置 `SameSite=Lax` 提升防跨站攻击能力。

* **🛡️ 全局 CSRF 强防护机制**
  * **中间件拦截**：所有非幂等的写请求（POST/PUT/DELETE/PATCH）在进入视图前均由 `before_request` 钩子拦截。
  * **安全凭证比对**：验证前端表单字段或 Headers 携带的 `X-CSRF-Token` 是否同会话中的 Token 匹配，杜绝跨站请求伪造。

* **📹 独占摄像头线程与状态门控**
  * **异步轮询**：后台搭建多线程 `CameraManager` 服务，避免并发访问摄像头时硬件锁冲突导致页面卡死。
  * **按需硬件调用**：仅在教师点击“开始上课”后真正调起物理摄像头与 YOLO 推理；未开课状态下自动释放摄像头，并为客户端提供精致的浅色玻璃态离线占位画面，从根本上杜绝摄像头指示灯异常长亮的 Bug。

* **📊 实时专注度双向看板与管理端**
  * **客户端实时分析**：支持侧边栏统计与底栏“实时课堂数据”看板同时轮询 `/latest_stats` 实时更新出勤与专注人数。
  * **下课确认模态框**：弃用阻塞自动化测试的浏览器原生 `confirm` 提示，采用定制开发的白微光玻璃态 HTML 模态弹窗，取消时维持课程状态，确定时停止监控并生成报告。
  * **管理端监控与大屏**：支持实时跟踪当前 Session 会话时长、在屏状态，并以明亮主题的 ECharts 折线图、柱状图动态分析历史课堂的抬头率和人数波动趋势。

* **🏫 班级、学生与学科教务关联**
  * **教务实体建模**：建立了班级 (`StudentClass`)、学生 (`Student`) 和学科课程 (`Course`) 关系表，支持完整的多对一实体关系建模，支持更精细的课程分类归档与教务管理。
  * **自动初始化注入**：若数据库为空，系统启动时会自动播种默认班级（如 `高一1班`、`高一2班`、`高二1班`）、默认学生花名册以及默认课程（`数学`、`语文`、`英语`、`物理`）。
  * **授课状态锁定绑定**：点击“开始上课”前必须选择授课班级与学科，上课期间选择框自动锁定，确保专注度及出勤时序数据（`TimelineRecord`）精准归档到本次 `Session` 会话。
  * **教务动态管理与接口**：提供 `/api/classes` 与 `/api/students` 动态新增班级和学生接口，对班级重名、学号冲突等逻辑进行完整后端校验。
  * **多维度对比分析分析**：管理端不仅能按班级和学科对历史报告进行过滤与检索，还支持班级维度（出勤/平均抬头率）以及学科维度的多图表横向对比大屏展示。

---


## 🏗️ 系统架构图

```text
  ┌─────────────────┐       ┌─────────────────────────────┐
  │ 教室摄像头视频流  │ ───>  │ YOLOv8 状态分类 + 专注度量化   │
  └─────────────────┘       └─────────────────────────────┘
                                           │
                                           ▼ (数据持久化)
  ┌─────────────────┐       ┌─────────────────────────────┐       ┌──────────────┐
  │  Web 浏览器前端   │ <───> │   Flask 标准分层包服务       │ <───> │ SQLite 数据库 │
  │ (ECharts 可视化)  │       │ (SQLAlchemy ORM + 业务路由) │       │ (classroom.db)│
  └─────────────────┘       └─────────────────────────────┘       └──────────────┘
```

---

## 📂 项目结构

项目采用标准 Flask 开发包（Package）分层架构，实现了路由、模型、视频流控制和检测逻辑的全面解耦：

```text
├── run.py                    # 项目唯一启动入口 (配置 DB 并启动 Flask)
├── classroom.db              # 本地数据库 (自动生成且 gitignore)
├── secret_key.txt            # 安全密钥文件 (自动生成且 gitignore)
├── weights/                  # 存放 YOLO 模型权重（如 best.pt）
├── reports/                  # 生成的历史课堂报告目录
├── requirements.txt          # 项目依赖包
├── readme.md                 # 项目说明文档
└── app/                      # 核心应用包
    ├── __init__.py           # 应用工厂 (初始化 DB、YOLO 核心、CameraManager)
    ├── models.py             # 数据模型 (User ORM)
    ├── camera.py             # 独占摄像头管理线程 (CameraManager)
    ├── detector.py           # YOLO 检测引擎 (自动相对定位 weights/best.pt)
    ├── routes.py             # 业务视图控制器与鉴权中间件
    ├── static/               # 静态资源 (含 css, uploads, outputs)
    └── templates/            # 前端 HTML 页面 (index, admin, login)
```

---


## 🚀 快速开始

### 1. 克隆项目与安装环境
确保本地已安装 Python 3.9+ 环境，在根目录下安装项目依赖：
```bash
pip install -r requirements.txt
```

### 2. 准备 YOLO 权重文件
确认 `weights/best.pt` 权重文件已放置在项目根目录的 `weights/` 目录下。

### 3. 运行服务
运行主启动程序以初始化数据库并启动 Web 服务器：
```bash
python run.py
```
* 服务默认运行于 `http://127.0.0.1:5001`。
* 首次运行将自动播种默认管理员账号：
  * **用户名**：`admin`
  * **密  码**：`admin123`
* 首次运行还会自动注入默认的班级、学生花名册与学科课程数据，方便开箱即用直接进行体验。

---

## 🛡️ 安全提示

为了防止敏感数据泄露，项目已将 `classroom.db` 数据库文件与 `secret_key.txt` 密钥文件添加至 `.gitignore` 中，在生产部署或推送代码时，请切勿将这些本地凭证推送到公开仓库中。
