import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

app = Flask(__name__, 
           static_url_path='/static',
           static_folder='static',
           template_folder='templates')

# ตั้งค่าพื้นฐาน
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///splitbill.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# สร้างโฟลเดอร์สำหรับอัปโหลดไฟล์
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'banners'), exist_ok=True)

# เริ่มต้นฐานข้อมูล
db = SQLAlchemy(app)

# โมเดลข้อมูล
class Food(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Person(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    foods_selected = db.relationship('PersonFood', backref='person', lazy=True, cascade='all, delete-orphan')

class PersonFood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.String(36), db.ForeignKey('person.id'), nullable=False)
    food_id = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# สร้างตาราง
with app.app_context():
    db.create_all()

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

@app.route('/')
def index():
    session_id = get_session_id()
    return render_template('index.html')

@app.route('/add_food', methods=['POST'])
def add_food():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'price' not in data:
            return jsonify({'success': False, 'error': 'ข้อมูลไม่ครบถ้วน'}), 400
        
        price = float(data['price'])
        if price <= 0:
            return jsonify({'success': False, 'error': 'ราคาต้องมากกว่า 0'}), 400
            
        food = Food(
            session_id=get_session_id(),
            name=data['name'].strip(),
            price=price
        )
        
        db.session.add(food)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'food': {
                'id': food.id,
                'name': food.name,
                'price': food.price
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_person', methods=['POST'])
def add_person():
    try:
        data = request.get_json()
        if not data or 'name' not in data or not data['name'].strip():
            return jsonify({'success': False, 'error': 'กรุณาระบุชื่อ'}), 400
            
        person = Person(
            session_id=get_session_id(),
            name=data['name'].strip()
        )
        
        db.session.add(person)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'person': {
                'id': person.id,
                'name': person.name,
                'foods_selected': []
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/select_food', methods=['POST'])
def select_food():
    try:
        data = request.get_json()
        if not data or 'person_id' not in data or 'food_ids' not in data:
            return jsonify({'success': False, 'error': 'ข้อมูลไม่ครบถ้วน'}), 400
            
        person_id = data['person_id']
        food_ids = data['food_ids']
        
        # ตรวจสอบว่ามีคนนี้ในระบบหรือไม่
        person = Person.query.get(person_id)
        if not person:
            return jsonify({'success': False, 'error': 'ไม่พบผู้ใช้'}), 404
            
        # ลบรายการอาหารเดิม
        PersonFood.query.filter_by(person_id=person_id).delete()
        
        # เพิ่มรายการอาหารใหม่
        for food_id in food_ids:
            # ตรวจสอบว่ามีอาหารนี้ในระบบหรือไม่
            food = Food.query.get(food_id)
            if not food:
                continue
                
            person_food = PersonFood(
                person_id=person_id,
                food_id=food_id
            )
            db.session.add(person_food)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_person/<person_id>', methods=['DELETE'])
def delete_person(person_id):
    try:
        # ตรวจสอบว่ามีคนนี้ในระบบหรือไม่
        person = Person.query.get(person_id)
        if not person:
            return jsonify({'success': False, 'error': 'ไม่พบผู้ใช้'}), 404
        
        # ลบรายการอาหารที่เกี่ยวข้อง
        PersonFood.query.filter_by(person_id=person_id).delete()
        
        # ลบคนออกจากฐานข้อมูล
        db.session.delete(person)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_food/<food_id>', methods=['DELETE'])
def delete_food(food_id):
    try:
        # ตรวจสอบว่ามีอาหารนี้ในระบบหรือไม่
        food = Food.query.get(food_id)
        if not food:
            return jsonify({'success': False, 'error': 'ไม่พบรายการอาหาร'}), 404
        
        # ลบรายการอาหารที่เกี่ยวข้อง
        PersonFood.query.filter_by(food_id=food_id).delete()
        
        # ลบอาหารออกจากฐานข้อมูล
        db.session.delete(food)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/calculate', methods=['GET'])
def calculate():
    try:
        session_id = get_session_id()
        
        # ดึงข้อมูลอาหารทั้งหมดของ session นี้
        all_foods = Food.query.filter_by(session_id=session_id).all()
        
        # สร้าง dictionary เพื่อเก็บจำนวนคนที่เลือกอาหารแต่ละรายการ
        food_share_count = {str(food.id): 0 for food in all_foods}
        
        # ดึงข้อมูลคนทั้งหมดของ session นี้
        all_people = Person.query.filter_by(session_id=session_id).all()
        
        # นับจำนวนคนที่เลือกอาหารแต่ละรายการ
        for person in all_people:
            for pf in person.foods_selected:
                if str(pf.food_id) in food_share_count:
                    food_share_count[str(pf.food_id)] += 1
        
        # คำนวณยอดที่แต่ละคนต้องจ่าย
        result = []
        
        # คำนวณยอดรวมทั้งหมดของอาหารทั้งหมด
        total_all_foods = sum(food.price for food in all_foods)
        
        # คำนวณยอดรวมที่แต่ละคนต้องจ่าย
        for person in all_people:
            person_total = 0
            person_foods = []
            
            # คำนวณยอดรวมสำหรับอาหารแต่ละรายการที่คนนี้เลือก
            for pf in person.foods_selected:
                food = Food.query.get(pf.food_id)
                if not food:
                    continue
                    
                # หารราคาอาหารด้วยจำนวนคนที่เลือกอาหารนี้
                share_count = food_share_count.get(str(food.id), 1)
                share_amount = food.price / share_count if share_count > 0 else 0
                person_total += share_amount
                
                # เก็บรายละเอียดอาหารที่คนนี้ต้องจ่าย
                person_foods.append({
                    'name': food.name,
                    'price': food.price,
                    'share_count': share_count,
                    'share_amount': share_amount
                })
            
            # เพิ่มข้อมูลผลลัพธ์ของคนนี้
            result.append({
                'id': person.id,
                'name': person.name,
                'total': round(person_total, 2),
                'foods': person_foods
            })
        
        # คำนวณยอดรวมทั้งหมดที่ทุกคนต้องจ่าย
        calculated_total = sum(person['total'] for person in result)
        
        # ส่งข้อมูลยอดรวมอาหารทั้งหมดและยอดรวมที่คำนวณได้กลับไปด้วย
        return jsonify({
            'success': True,
            'people': result,
            'total_all_foods': round(total_all_foods, 2),
            'calculated_total': round(calculated_total, 2)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/banner/left')
def banner_left():
    return render_template('banner_left.html')

@app.route('/banner/right')
def banner_right():
    return render_template('banner_right.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
