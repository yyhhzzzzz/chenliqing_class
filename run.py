import os
from app import create_app
from app.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

if __name__ == '__main__':
    # Initialize DB and create tables
    with app.app_context():
        db.create_all()
        # Seed default admin user if not present
        if not User.query.first():
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin_user)
            db.session.commit()
            print("\n" + "="*50)
            print("👤 已成功初始化默认管理员账号！")
            print("   用户名：admin")
            print("   密  码：admin123")
            print("="*50 + "\n")

    # Print admin control console links
    print(f"\n{'='*50}")
    print(f"🚀 系统已启动！")
    print(f"🔗 前端监控页面: http://localhost:5001")
    print(f"🔐 管理端专用链接: http://localhost:5001/admin")
    print(f"{'='*50}\n")
    
    # Run server on port 5001
    app.run(host='127.0.0.1', port=5001, debug=True)
