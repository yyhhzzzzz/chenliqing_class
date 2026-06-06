import os
import time
import threading
import cv2
import numpy as np

# 全局变量用于存储课堂状态和统计数据
class_state = {
    'is_active': False,
    'start_time': None,
    'session_id': None,
    'history_stats': [],  # 存储每秒的统计快照
    'last_sample_time': 0
}

latest_camera_stats = {
    'total': 0,
    'listening': 0,
    'distracted': 0,
    'attention_rate': "0.0%"
}

class CameraManager:
    def __init__(self, detector):
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.latest_frame = None
        self.camera = None
        self.detector = detector
        self.fps_limit = 20  # target FPS to save CPU/GPU resources

    def start(self):
        with self.lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()
                print("[CameraManager] Background camera thread started.")

    def stop(self):
        with self.lock:
            self.running = False
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            print("[CameraManager] Background camera thread stopped.")

    def _run(self):
        global latest_camera_stats
        
        # Frame delay matching target FPS
        frame_delay = 1.0 / self.fps_limit
        
        while self.running:
            start_time = time.time()
            
            if class_state['is_active']:
                # Active class: open camera and perform detection
                try:
                    if self.camera is None or not self.camera.isOpened():
                        print("[CameraManager] Opening camera...")
                        self.camera = cv2.VideoCapture(0)
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        
                    if not self.camera.isOpened():
                        print("[CameraManager] Error: Camera could not be opened. Retrying in 1s...")
                        time.sleep(1.0)
                        continue

                    success, frame = self.camera.read()
                    if not success:
                        print("[CameraManager] Warning: Failed to read frame from camera. Retrying...")
                        time.sleep(0.5)
                        continue

                    # YOLO prediction
                    annotated_frame, stats = self.detector.predict_frame(frame, conf_threshold=0.3)
                    
                    # Update local module variable
                    for key in latest_camera_stats:
                        latest_camera_stats[key] = stats[key]

                    # Collect stats history every 1.0s
                    current_time = time.time()
                    if current_time - class_state['last_sample_time'] >= 1.0:
                        class_state['history_stats'].append(stats)
                        class_state['last_sample_time'] = current_time

                    self.latest_frame = annotated_frame
                except Exception as e:
                    print(f"[CameraManager] Error in detection loop: {e}")
                    time.sleep(1.0)
            else:
                # Class inactive: release camera and output offline placeholder
                try:
                    if self.camera is not None:
                        print("[CameraManager] Class inactive. Releasing camera...")
                        self.camera.release()
                        self.camera = None

                    # Create glassmorphic light theme placeholder
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    frame[:, :] = (248, 244, 240)  # BGR background color matching Light Theme

                    text = "Camera Offline. Click 'Start Class' to activate."
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text_size = cv2.getTextSize(text, font, 0.55, 1)[0]
                    text_x = (640 - text_size[0]) // 2
                    text_y = (480 + text_size[1]) // 2
                    cv2.putText(frame, text, (text_x, text_y), font, 0.55, (100, 116, 139), 1, cv2.LINE_AA)

                    self.latest_frame = frame
                    
                    # Reset stats
                    for key in latest_camera_stats:
                        if key == 'attention_rate':
                            latest_camera_stats[key] = "0.0%"
                        else:
                            latest_camera_stats[key] = 0
                except Exception as e:
                    print(f"[CameraManager] Error in offline loop: {e}")

                # Sleep longer when offline to reduce CPU usage
                time.sleep(0.5)
                continue

            # Maintain stable FPS
            elapsed = time.time() - start_time
            sleep_time = max(0.01, frame_delay - elapsed)
            time.sleep(sleep_time)

def generate_frames(camera_manager):
    camera_manager.start()
    
    while True:
        frame = camera_manager.latest_frame
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05)  # Polling interval matching target FPS
