import os
from app import create_app
from app.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

if __name__ == '__main__':
    # Initialize DB and create tables
    with app.app_context():
        # TODO(security): In production, use migrations instead of db.create_all().
        # db.drop_all()
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

        # Import models for seeding
        from app.models import StudentClass, Course, Student

        # Seed classes and students if empty
        if not StudentClass.query.first():
            class1 = StudentClass(name="高一1班")
            class2 = StudentClass(name="高一2班")
            class3 = StudentClass(name="高二1班")
            db.session.add_all([class1, class2, class3])
            db.session.commit()
            
            # Seed students
            names1 = ["张伟", "王伟", "李娜", "张敏", "李静", "王静", "刘洋", "王秀英", "李强", "王勇", "张杰", "李杰", "王丽", "张丽", "李娟"]
            names2 = ["刘伟", "张华", "李军", "王芳", "张凡", "肖恩", "王丽丽", "李小龙", "赵敏", "赵云", "关羽", "张飞", "刘备", "诸葛亮", "曹操"]
            names3 = ["李华", "王明", "陈浩", "林峰", "叶平", "杨光", "周杰", "蔡晓", "徐静", "孙伟", "胡丽", "马超", "黄忠", "魏延", "姜维"]
            
            for n in names1:
                db.session.add(Student(name=n, student_class=class1))
            for n in names2:
                db.session.add(Student(name=n, student_class=class2))
            for n in names3:
                db.session.add(Student(name=n, student_class=class3))
            db.session.commit()
            print("🏫 班级与学生初始数据注入完成！")

        # Seed courses if empty
        if not Course.query.first():
            course1 = Course(name="数学")
            course2 = Course(name="语文")
            course3 = Course(name="英语")
            course4 = Course(name="物理")
            db.session.add_all([course1, course2, course3, course4])
            db.session.commit()
            print("📚 学科课程初始数据注入完成！")

    # Print admin control console links
    print(f"\n{'='*50}")
    print(f"🚀 系统已启动！")
    print(f"🔗 前端监控页面: http://localhost:5001")
    print(f"🔐 管理端专用链接: http://localhost:5001/admin")
    print(f"{'='*50}\n")
    
    # Run server on port 5001
    app.run(host='127.0.0.1', port=5001, debug=True)
