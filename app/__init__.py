import os
import secrets
from flask import Flask, jsonify, request, session
from app.models import db
from app.detector import ClassroomDetector
from app.camera import CameraManager

# Initialize the detector and camera manager globally
detector = ClassroomDetector()
camera_manager = CameraManager(detector)

def create_app():
    app = Flask(__name__)
    
    # Configure directories
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['OUTPUT_FOLDER'] = os.path.join(app.root_path, 'static', 'outputs')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    # SQLite Database Config (located in project root directory)
    root_dir = os.path.dirname(app.root_path)
    db_path = os.path.join(root_dir, 'classroom.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Secret key generation
    def get_secret_key():
        key = os.environ.get('FLASK_SECRET_KEY')
        if key:
            return key
        
        key_path = os.path.join(root_dir, 'secret_key.txt')
        if os.path.exists(key_path):
            with open(key_path, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
                    
        key = secrets.token_hex(32)
        try:
            with open(key_path, 'w', encoding='utf-8') as f:
                f.write(key)
        except Exception as e:
            print(f"[警告] 无法保存 SECRET_KEY 到本地文件: {e}")
        return key
        
    app.config['SECRET_KEY'] = get_secret_key()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Bind database to app
    db.init_app(app)
    
    # Bind detector and camera manager to the app
    app.detector = detector
    app.camera_manager = camera_manager
    
    # Injected CSRF protection
    @app.context_processor
    def inject_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return dict(csrf_token=lambda: session['csrf_token'])
        
    @app.before_request
    def csrf_protect():
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if request.path == '/login':
                return
            
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_token = session.get('csrf_token')
            
            if not session_token or not token or token != session_token:
                print(f"[安全警告] CSRF 校验失败！请求路径: {request.path}")
                return jsonify({'error': 'CSRF token verification failed.'}), 403
                
    # Register main blueprint
    from app.routes import main_bp
    app.register_blueprint(main_bp)
        
    return app
