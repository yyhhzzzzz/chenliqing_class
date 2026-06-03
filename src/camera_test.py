import cv2
import os
import sys

# 将项目根目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.detector import ClassroomDetector

def run_camera():
    # 初始化检测器
    detector = ClassroomDetector()
    
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    print("正在启动实时识别 (按下 'q' 退出)...")
    
    # 设置窗口
    window_name = "AI Classroom Attention Detection"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 实时检测并绘制
        annotated_frame, stats = detector.predict_frame(frame, conf_threshold=0.3)

        # 在窗口上显示统计信息
        info_text = f"Total: {stats['total']} | Listening: {stats['listening']} | Rate: {stats['attention_rate']}"
        cv2.putText(annotated_frame, info_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # 显示画面
        cv2.imshow(window_name, annotated_frame)

        # 按 'q' 退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_camera()
