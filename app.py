import os
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__, 
           static_url_path='/static',
           static_folder='static',
           template_folder='templates')

# ตั้งค่าพื้นฐาน
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# สร้างโฟลเดอร์สำหรับอัปโหลดไฟล์
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'banners'), exist_ok=True)

# เก็บข้อมูลชั่วคราว
foods = []
people = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_food', methods=['POST'])
def add_food():
    data = request.json
    food = {
        'id': len(foods) + 1,
        'name': data['name'],
        'price': float(data['price'])
    }
    foods.append(food)
    return jsonify({'success': True, 'foods': foods})

@app.route('/add_person', methods=['POST'])
def add_person():
    data = request.json
    person = {
        'id': len(people) + 1,
        'name': data['name'],
        'foods_selected': []
    }
    people.append(person)
    return jsonify({'success': True, 'people': people})

@app.route('/select_food', methods=['POST'])
def select_food():
    data = request.json
    person_id = data['person_id']
    food_ids = data['food_ids']
    
    for person in people:
        if person['id'] == person_id:
            person['foods_selected'] = food_ids
            break
    
    return jsonify({'success': True})

@app.route('/calculate', methods=['GET'])
def calculate():
    # สร้าง dictionary เพื่อเก็บจำนวนคนที่เลือกอาหารแต่ละรายการ
    food_share_count = {food['id']: 0 for food in foods}
    
    # นับจำนวนคนที่เลือกอาหารแต่ละรายการ
    for person in people:
        for food_id in person['foods_selected']:
            if food_id in food_share_count:
                food_share_count[food_id] += 1
    
    # คำนวณยอดที่แต่ละคนต้องจ่าย
    result = []
    food_details = []
    
    # คำนวณยอดรวมทั้งหมดของอาหารทั้งหมด
    total_all_foods = sum(food['price'] for food in foods)
    
    # คำนวณยอดรวมที่แต่ละคนต้องจ่าย
    for person in people:
        person_total = 0
        person_foods = []
        
        # คำนวณยอดรวมสำหรับอาหารแต่ละรายการที่คนนี้เลือก
        for food in foods:
            if food['id'] in person['foods_selected']:
                # หารราคาอาหารด้วยจำนวนคนที่เลือกอาหารนี้
                share_count = food_share_count[food['id']]
                share_amount = food['price'] / share_count if share_count > 0 else 0
                person_total += share_amount
                
                # เก็บรายละเอียดอาหารที่คนนี้ต้องจ่าย
                person_foods.append({
                    'name': food['name'],
                    'price': food['price'],
                    'share_count': share_count,
                    'share_amount': share_amount
                })
        
        # เพิ่มข้อมูลผลลัพธ์ของคนนี้
        result.append({
            'name': person['name'],
            'total': round(person_total, 2),
            'foods': person_foods
        })
    
    # คำนวณยอดรวมทั้งหมดที่ทุกคนต้องจ่าย (ควรใกล้เคียงกับยอดรวมอาหารทั้งหมด)
    calculated_total = sum(person['total'] for person in result)
    
    # ส่งข้อมูลยอดรวมอาหารทั้งหมดและยอดรวมที่คำนวณได้กลับไปด้วย
    return jsonify({
        'people': result,
        'total_all_foods': round(total_all_foods, 2),
        'calculated_total': round(calculated_total, 2)
    })

@app.route('/banner/left')
def banner_left():
    return render_template('banner_left.html')

@app.route('/banner/right')
def banner_right():
    return render_template('banner_right.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
