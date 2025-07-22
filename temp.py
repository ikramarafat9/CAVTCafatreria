from flask import Flask, request, render_template, redirect, session, flash, url_for
from database import get_db_connection #عبارة عن دالة مهمتها  انشاء اتالمع الداتا بيز 
from functools import wraps
from flask_socketio import SocketIO, emit, join_room
from flask_session import Session
from datetime import timedelta
from datetime import datetime
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import random
import json
import pytz

amman = pytz.timezone('Asia/Amman')
now = datetime.now(amman).strftime('%Y-%m-%d %H:%M:%S')

#******************* picture
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join("static", "items")  # الأفضل من "static/items"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#****************

def delete_old_orders():
    conn = sqlite3.connect('college_users.db')
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("DELETE FROM orders WHERE DATE(order_time) < ?", (today,))
    conn.commit()
    conn.close()
    print("Deleted old orders.")

# جدولة حذف الطلبات يوميًا
scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_old_orders, trigger="cron", hour=0, minute=0)
scheduler.start()



#****************


app = Flask(__name__)
app.secret_key = 'secret'  # مهم للجلسات

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_PERMANENT'] = True

Session(app)

# إعداد SocketIO بدون eventlet على Windows
socketio = SocketIO(app, async_mode='threading', manage_session=False)
#---------------------------------------------------------------------------------------------------------------------

# إعداد المسار الافتراضي ليحول إلى القائمة مباشرة
@app.route('/')
def index():
    return "<script>window.location.href='/login';</script>"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يجب تسجيل الدخول أولاً')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

#---------------------------------------------------------------------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        specialty = request.form['specialty']
        phone = request.form['phone']
        password = request.form['password']
        if len(password)<8 :
                flash("كلمة المرور اقل من 8 احرف")
                return redirect(url_for('signup')) 
        if len(phone)<10 :
                flash("رقم الهاتف غير صحيح")   
                return redirect(url_for('signup')) 

        # إدخال البيانات في قاعدة البيانات
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO User (name, specialty, phone_number, password)
                VALUES (?, ?, ?, ?)
            ''', (name, specialty, phone, password))
            conn.commit()
        
            # استرجاع بيانات المستخدم الجديد
            cursor.execute("SELECT * FROM User WHERE phone_number=? AND password=?", (phone, password))
            user = cursor.fetchone()
        
            # تخزين البيانات في الجلسة
            if user:
                session['user_id'] = user['id']
                session['name'] = user['name']
                session['specialty'] = user['specialty']
                session['phone_number'] = user['phone_number']
        
        except sqlite3.Error as e:
            flash(f'حدث خطأ: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('homepage'))  # إعادة توجيه لنفس الصفحة بعد التسجيل
    
    return render_template('signup.html' , pagetitle="Sign up")

#---------------------------------------------------------------------------------------------------------------------
#********************
@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if 'role_id' in session and session['role_id'] == 1:
        return redirect(url_for('admin_dashboard'))

    if 'role_id' in session and session['role_id'] != 1:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        session.permanent = True

        phone_number = request.form['phoneNumber']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM User WHERE phone_number=? AND password=?", (phone_number, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['specialty'] = user['specialty']
            session['phone_number'] = user['phone_number']
            session['role_id'] = user['role_id']

            # توجيه حسب الدور
            if user['role_id'] == 1:
                return redirect('/admin')  # لوحة الأدمن
            else:
                return redirect('/home')   # باقي المستخدمين

        else:
            flash('رقم الهاتف أو كلمة المرور غير صحيحة')
            return redirect('/login')

    return render_template('login.html', pagetitle="Log In")
#**************************
#---------------------------------------------------------------------------------------------------------------------

@app.route('/forgetPassword')
def forgetPassword():
    return render_template('forgetPassword.html', pagetitle="Forget Password")

#---------------------------------------------------------------------------------------------------------------------

@app.route('/home')
@login_required
def homepage():
    return render_template('home.html', pagetitle="Home")

#---------------------------------------------------------------------------------------------------------------------
#*******************************************
@app.route('/admin')
@login_required
def admin_dashboard():
    if session.get('role_id') != 1:
        flash("🚫 لا تملك صلاحية الدخول لهذه الصفحة.")
        return redirect(url_for('homepage'))
    return render_template('admin_dashboard.html', pagetitle="لوحة تحكم الأدمن")


@app.route('/admin/manage-menu', methods=['GET', 'POST'])
@login_required
def admin_manage_menu():
    if session.get('role_id') != 1:
        flash("🚫 لا تملك صلاحية الدخول لهذه الصفحة.")
        return redirect(url_for('homepage'))

    conn = get_db_connection()
    cursor = conn.cursor()
    form = request.form
    files = request.files

    action = form.get('action', '')

    # --- إدارة الفئات ---
    if action == 'add_category' and 'add_category_name' in form:
        cursor.execute("INSERT INTO category (name) VALUES (?)", (form['add_category_name'],))
        conn.commit()  # أضف هذا
        flash("✅ تم إضافة الفئة.")


    elif action == 'edit_category' and 'edit_category_id' in form:
        cursor.execute("UPDATE category SET name=? WHERE id=?", (form['edit_category_name'], form['edit_category_id']))
        flash("✏️ تم تعديل الفئة.")

    elif action == 'delete_category' and 'delete_category_id' in form:
        cursor.execute("DELETE FROM category WHERE id=?", (form['delete_category_id'],))
        flash("🗑️ تم حذف الفئة.")

    # --- إدارة الأصناف ---
    elif action == 'add_item' and 'add_item_name' in form:
        name = form['add_item_name']
        price = form['add_item_price']
        category_id = form['add_item_category']
        image = files.get('add_item_image')
        image_filename = None
    
        existing = cursor.execute("SELECT * FROM MenuItem WHERE name = ?", (name,)).fetchone()
        if existing:
            flash("❌ هذا الاسم مستخدم مسبقًا.")
        else:
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                image_filename = f"image/{filename}"
                image.save(os.path.join('static/image', filename))
            else:
                # 🟢 تعيين الصورة الافتراضية في حال لم تُرفع صورة
                image_filename = "image/defult.jpg"
    
            cursor.execute(
                "INSERT INTO MenuItem (name, price, category_id, image) VALUES (?, ?, ?, ?)",
                (name, price, category_id, image_filename)
            )
            flash("✅ تم إضافة الصنف.")


    elif action == 'edit_item' and 'edit_item_id' in form:
        item_id = form['edit_item_id']
        name = form['edit_item_name']
        price = form['edit_item_price']
        category_id = form['edit_item_category']
        image = files.get('edit_item_image')

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_filename = f"image/{filename}"
            image.save(os.path.join('static/image', filename))

            old = cursor.execute("SELECT image FROM MenuItem WHERE id = ?", (item_id,)).fetchone()
            if old and old['image']:
                old_path = os.path.join('static', old['image'])
                if os.path.exists(old_path):
                    os.remove(old_path)

            cursor.execute(
                "UPDATE MenuItem SET name=?, price=?, category_id=?, image=? WHERE id=?",
                (name, price, category_id, image_filename, item_id)
            )
        else:
            cursor.execute(
                "UPDATE MenuItem SET name=?, price=?, category_id=? WHERE id=?",
                (name, price, category_id, item_id)
            )
        flash("✏️ تم تعديل الصنف.")

    elif action == 'delete_item' and 'delete_item_id' in form:
        item_id = form['delete_item_id']
        old = cursor.execute("SELECT image FROM MenuItem WHERE id = ?", (item_id,)).fetchone()
        if old and old['image']:
            path = os.path.join('static', old['image'])
            if os.path.exists(path):
                os.remove(path)
        cursor.execute("DELETE FROM MenuItem WHERE id = ?", (item_id,))
        flash("🗑️ تم حذف الصنف.")

    # --- إدارة المكونات الثابتة ---
    elif action == 'add_fixed' and 'add_fixed_name' in form:
        cursor.execute("INSERT INTO fixed_ingredients (name) VALUES (?)", (form['add_fixed_name'],))
        flash("✅ تم إضافة مكون ثابت.")

    elif action == 'edit_fixed' and 'edit_fixed_id' in form:
        cursor.execute("UPDATE fixed_ingredients SET name=? WHERE id=?", (form['edit_fixed_name'], form['edit_fixed_id']))
        flash("✏️ تم تعديل المكون الثابت.")

    elif action == 'delete_fixed' and 'delete_fixed_id' in form:
        cursor.execute("DELETE FROM fixed_ingredients WHERE id=?", (form['delete_fixed_id'],))
        flash("🗑️ تم حذف المكون الثابت.")

    # --- ربط المكونات الثابتة مع الأصناف ---
    elif action == 'link_fixed' and 'link_fixed_item_id' in form:
        item_id = form['link_fixed_item_id']
        selected_ids = request.form.getlist('fixed_ingredient_ids')
        cursor.execute("DELETE FROM item_fixed_ingredients WHERE item_id=?", (item_id,))
        for fid in selected_ids:
            cursor.execute("INSERT INTO item_fixed_ingredients (item_id, fixed_ingredient_id) VALUES (?, ?)", (item_id, fid))
        flash("🔗 تم ربط المكونات الثابتة.")

    elif action == 'unlink_fixed' and 'unlink_fixed_item_id' in form and 'unlink_fixed_ing_id' in form:
        cursor.execute(
            "DELETE FROM item_fixed_ingredients WHERE item_id=? AND fixed_ingredient_id=?",
            (form['unlink_fixed_item_id'], form['unlink_fixed_ing_id'])
        )
        flash("❌ تم إلغاء ربط المكون الثابت.")

    # --- إدارة المكونات القابلة للتخصيص ---
    elif action == 'add_customizable' and 'add_customizable_name' in form:
        cursor.execute("INSERT INTO customizable_ingredients (name) VALUES (?)", (form['add_customizable_name'],))
        flash("✅ تم إضافة مكون قابل للتخصيص.")

    elif action == 'edit_customizable' and 'edit_customizable_id' in form:
        cursor.execute("UPDATE customizable_ingredients SET name=? WHERE id=?", (form['edit_customizable_name'], form['edit_customizable_id']))
        flash("✏️ تم تعديل المكون القابل للتخصيص.")

    elif action == 'delete_customizable' and 'delete_customizable_id' in form:
        cursor.execute("DELETE FROM customizable_ingredients WHERE id=?", (form['delete_customizable_id'],))
        flash("🗑️ تم حذف المكون القابل للتخصيص.")

    # --- إضافة خيار لمكون قابل للتخصيص ---
    elif action == 'add_option' and 'add_option_name' in form and 'customizable_id_for_option' in form:
        name = form['add_option_name']
        ingredient_id = form['customizable_id_for_option']
        extra_price = form.get('extra_price', 0)
    
        # تأكد من تحويل السعر إلى رقم (float)
        try:
            extra_price = float(extra_price)
        except ValueError:
            extra_price = 0
    
        cursor.execute(
            "INSERT INTO customizable_options (name, customizable_ingredient_id, extra_price) VALUES (?, ?, ?)",
            (name, ingredient_id, extra_price)
        )
        flash("✅ تم إضافة خيار للمكون.")


    # --- ربط خيارات مكونات قابلة للتخصيص مع الأصناف ---
    elif action == 'link_custom' and 'link_custom_item_id' in form:
        item_id = form['link_custom_item_id']
        selected_option_ids = request.form.getlist('customizable_option_ids')
        cursor.execute("DELETE FROM item_customizable_options WHERE item_id=?", (item_id,))
        for option_id in selected_option_ids:
            cursor.execute("INSERT INTO item_customizable_options (item_id, customizable_option_id) VALUES (?, ?)", (item_id, option_id))
        flash("🔗 تم ربط المكونات القابلة للتخصيص.")

    elif action == 'unlink_custom' and 'unlink_custom_item_id' in form and 'unlink_custom_option_id' in form:
        cursor.execute(
            "DELETE FROM item_customizable_options WHERE item_id=? AND customizable_option_id=?",
            (form['unlink_custom_item_id'], form['unlink_custom_option_id'])
        )
        flash("❌ تم إلغاء ربط المكون القابل للتخصيص.")

    conn.commit()

    # --- جلب البيانات للعرض ---
    categories = cursor.execute("SELECT * FROM category").fetchall()
    items = cursor.execute("SELECT * FROM MenuItem").fetchall()
    fixed_ingredients = cursor.execute("SELECT * FROM fixed_ingredients").fetchall()
    customizables = cursor.execute("SELECT * FROM customizable_ingredients").fetchall()
    options = cursor.execute("SELECT * FROM customizable_options").fetchall()

    item_fixed_links = cursor.execute("""
        SELECT ifi.item_id, ifi.fixed_ingredient_id AS ing_id,
               mi.name AS item_name, fi.name AS ing_name
        FROM item_fixed_ingredients ifi
        JOIN MenuItem mi ON ifi.item_id = mi.id
        JOIN fixed_ingredients fi ON ifi.fixed_ingredient_id = fi.id
    """).fetchall()

    item_custom_links = cursor.execute("""
        SELECT ico.item_id, ico.customizable_option_id AS option_id,
               mi.name AS item_name, co.name AS option_name
        FROM item_customizable_options ico
        JOIN MenuItem mi ON ico.item_id = mi.id
        JOIN customizable_options co ON ico.customizable_option_id = co.id
    """).fetchall()

    conn.close()

    return render_template("admin_manage_menu.html",
        categories=categories,
        items=items,
        fixed_ingredients=fixed_ingredients,
        customizables=customizables,
        options=options,
        item_fixed_links=item_fixed_links,
        item_custom_links=item_custom_links,
        pagetitle="إدارة قائمة الطعام"
    )


    
#***************************************************


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    conn = get_db_connection()
    cursor = conn.cursor()

    # في حالة إرسال النموذج لتحديث البيانات
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']

        specialty = request.form['specialty']
        password = request.form['password']

        if password.strip():  # إذا تم إدخال كلمة مرور جديدة
            cursor.execute("""
                UPDATE User SET name=?, specialty=?, password=? , phone_number=?  WHERE id=?
            """, (name, specialty, password, phone, session['user_id']))
        else:  # إذا لم تدخل كلمة مرور جديدة
            cursor.execute("""
                UPDATE User SET name=?, specialty=? WHERE id=?
            """, (name, specialty, session['user_id']))

        conn.commit()
        flash('تم تحديث البيانات بنجاح')
        return redirect(url_for('account'))

    # جلب بيانات المستخدم للعرض
    cursor.execute("SELECT * FROM User WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    return render_template('account.html', user=user, pagetitle="Account")

#--------------------------------------------------------------------------------------------------------------------- 

@app.route('/about_app')
@login_required
def waiting():
    return render_template('about_app.html')

#---------------------------------------------------------------------------------------------------------------------

@app.route('/logout')
def logout():
    session.clear()  # حذف كل بيانات الجلسة
    return redirect(url_for('login'))  # رجوع لصفحة تسجيل الدخول

#--------------------------------------------------------------------------------------------------------------------

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    
    if request.method == 'POST':
        content = request.form['content']
        if not content:
            flash('الرجاء إدخال ملاحظاتك')
            return redirect(url_for('feedback'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Feedback (user_id,content)
                VALUES (?, ?)
            ''', (session['user_id'], content))
            conn.commit()
            flash('شكراً لملاحظاتك!', 'success')
        except sqlite3.Error as e:
            flash(f'حدث خطأ: {e}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('feedback'))
    
    return render_template('feedback.html', pagetitle="تقديم ملاحظات")

#---------------------------------------------------------------------------------------------------------------------

@app.route('/Showfeedbacks')
@login_required
def show_feedbacks():
    selected_month = request.args.get('month')  # يستقبل قيمة الشهر من رابط الصفحة، مثلا ?month=7

    conn = get_db_connection()  # اتصال بقاعدة البيانات
    cursor = conn.cursor()

    if selected_month and selected_month.isdigit():
        month_str = selected_month.zfill(2)  # يحول 7 إلى '07' لأن strftime('%m') يعيد رقم الشهر 2 خانات
        query = """
        SELECT Feedback.content, Feedback.feedback_date, User.name
        FROM Feedback
        JOIN User ON Feedback.user_id = User.id
        WHERE strftime('%m', Feedback.feedback_date) = ?
        ORDER BY Feedback.feedback_date DESC
        """
        cursor.execute(query, (month_str,))
    else:
        query = """
        SELECT Feedback.content, Feedback.feedback_date, User.name
        FROM Feedback
        JOIN User ON Feedback.user_id = User.id
        ORDER BY Feedback.feedback_date DESC
        """
        cursor.execute(query)

    feedbacks = cursor.fetchall()
    conn.commit()
    conn.close()

    return render_template('showfeedback.html', pagetitle="الملاحظات", feedbacks=feedbacks, selected_month=selected_month)

#---------------------------------------------------------------------------------------------------------------------

@app.route('/menu')
@login_required
def show_menu():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM category').fetchall()
    menu_data = {}
    for cat in categories:
        items = conn.execute('SELECT * FROM MenuItem WHERE category_id = ?', (cat['id'],)).fetchall()
        menu_data[cat['name']] = [dict(item) for item in items]
    conn.close()
    return render_template('menu.html', menu_data=menu_data)

#---------------------------------------------------------------------------------------------------------------------
@app.route('/customize/<int:item_id>', methods=['GET', 'POST'])
@login_required
def customize_item(item_id):
    conn = get_db_connection()
    item = conn.execute('''
        SELECT i.*, c.name as category FROM MenuItem i
        JOIN category c ON i.category_id = c.id
        WHERE i.id = ?
    ''', (item_id,)).fetchone()
    if not item:
        conn.close()
        return "العنصر غير موجود", 404

    item = dict(item)

    fixed_ings = conn.execute('''
        SELECT fi.id, fi.name FROM fixed_ingredients fi
        JOIN item_fixed_ingredients ifi ON fi.id = ifi.fixed_ingredient_id
        WHERE ifi.item_id = ?
    ''', (item_id,)).fetchall()
    fixed_ings = [dict(f) for f in fixed_ings]

    customizable_opts = conn.execute('''
        SELECT co.id, co.name, ci.name as ingredient_type, co.extra_price FROM customizable_options co
        JOIN customizable_ingredients ci ON co.customizable_ingredient_id = ci.id
        JOIN item_customizable_options ico ON co.id = ico.customizable_option_id
        WHERE ico.item_id = ?
        ORDER BY ci.name
    ''', (item_id,)).fetchall()
    customizable_opts = [dict(c) for c in customizable_opts]

    customization_options = {}
    for opt in customizable_opts:
        ing_type = opt['ingredient_type'].strip()  # يحذف المساحات والسطر الجديد
        customization_options.setdefault(ing_type, []).append({
            'id': opt['id'],
            'name': opt['name'],
            'extra_price': opt['extra_price'] or 0
        })

    # ------------------- هنا صار برا اللوب -------------------
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))
        cursor = conn.cursor()
     
        order = cursor.execute('''
            SELECT id FROM orders
            WHERE user_id = ? AND status = 'pending'
            ORDER BY order_time DESC LIMIT 1
        ''', (session['user_id'],)).fetchone()
        
        if order:
            order_id = order['id']
        else:
            cursor.execute('INSERT INTO orders (user_id, status) VALUES (?, ?)', (session['user_id'], 'pending'))
            order_id = cursor.lastrowid
        
        session['order_id'] = order_id

        for i in range(quantity):
            selected_fixed = []
            for f in fixed_ings:
                if request.form.get(f'fixed_{f["id"]}_{i}') == 'on':
                    selected_fixed.append(f['name'])

            selected_custom = []
            extra_price = 0.0
            for ing_type, options in customization_options.items():
                selected_option_id = request.form.get(f'custom_{ing_type}_{i}')
                if selected_option_id:
                    selected_option = next((o for o in options if str(o['id']) == selected_option_id), None)
                    if selected_option:
                        selected_custom.append({'ingredient_name': ing_type, 'option_name': selected_option['name']})
                        extra_price += float(selected_option.get('extra_price') or 0)

            notes = request.form.get(f'notes_{i}', '')
            details_json = json.dumps({
                'fixed_ingredients': selected_fixed,
                'custom_options': selected_custom,
                'notes': notes
            }, ensure_ascii=False)

            base_price = item['price'] or 0
            cursor.execute('''
                INSERT INTO order_details (order_id, item_id, base_price, extra_price, details_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, item_id, base_price, extra_price, details_json))

        conn.commit()
        conn.close()
        return redirect(url_for('view_cart'))

    conn.close()

    return render_template('customize.html',
                           item=item,
                           fixed_ingredients=fixed_ings,
                           customization_options=customization_options)
#---------------------------------------------------------------------------------------------------------------------

@app.route('/cart')
@login_required
def view_cart():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cart_items = []
    total = 0.0

    # جلب الطلب المفتوح (pending) للمستخدم الحالي
    order = conn.execute('''
        SELECT id FROM orders
        WHERE user_id = ? AND status = 'pending'
        ORDER BY order_time DESC
        LIMIT 1
    ''', (user_id,)).fetchone()

    if not order:
        # لا يوجد طلب مفتوح → السلة فارغة
        conn.close()
        return render_template('cart.html', cart_items=[], total=0.0)

    order_id = order['id']

    # جلب عناصر السلة المرتبطة بالطلب المفتوح
    rows = conn.execute('''
        SELECT od.id AS order_detail_id,
               i.name AS item_name,
               od.base_price,
               od.extra_price,
               od.details_json
        FROM order_details od
        JOIN MenuItem i ON od.item_id = i.id
        WHERE od.order_id = ?
        ORDER BY od.id DESC
    ''', (order_id,)).fetchall()

    for row in rows:
        row = dict(row)
        details = json.loads(row['details_json']) if row['details_json'] else {}
        fixed_ingredients = details.get('fixed_ingredients', [])
        custom_options = details.get('custom_options', [])
        notes = details.get('notes', '')
        total_price = row['base_price'] + row['extra_price']
        total += total_price

        cart_items.append({
            'order_detail_id': row['order_detail_id'],
            'item_name': row['item_name'],
            'base_price': row['base_price'],
            'extra_price': row['extra_price'],
            'fixed_ingredients': fixed_ingredients,
            'custom_options': custom_options,
            'notes': notes,
            'total_price': total_price,
            'quantity': 1
        })

    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

#---------------------------------------------------------------------------------------------------------------------

@app.route('/cart/delete/<int:order_detail_id>', methods=['POST'])
@login_required
def delete_cart_item(order_detail_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM order_details WHERE id = ?', (order_detail_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_cart'))

#---------------------------------------------------------------------------------------------------------------------

@app.route('/checkout')
@login_required
def checkout():
    
    user_id = session.get('user_id')
    student_name = session.get('student_name')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # جلب الطلب المفتوح (pending) للمستخدم
    order = conn.execute('''
        SELECT id FROM orders
        WHERE user_id = ? AND status = 'pending'
        ORDER BY order_time DESC
        LIMIT 1
    ''', (user_id,)).fetchone()

    if not order:
        flash("🚫 لا يوجد طلب لتأكيده.")
        conn.close()
        return redirect(url_for('view_cart'))

    order_id = order['id']

    # تحقق هل هناك عناصر مرتبطة بهذا الطلب؟
    items_count = conn.execute('SELECT COUNT(*) FROM order_details WHERE order_id = ?', (order_id,)).fetchone()[0]
    if items_count == 0:
        flash("🚫 لا يوجد عناصر في السلة لتأكيدها.")
        conn.close()
        return redirect(url_for('view_cart'))

    # تغيير حالة الطلب من 'pending' إلى 'confirmed' (أو أي حالة تناسب سير العمل)
    conn.execute('UPDATE orders SET status = "confirmed", order_time = ? WHERE id = ?', (now, order_id))
    conn.commit()
    conn.close()

    # إرسال إشعار للـ owner (المطبخ) عن الطلب الجديد المؤكد
    message = f"🔔 تم تأكيد طلب جديد من {student_name} يحتوي على {items_count} عنصر."
    socketio.emit('new_order', {'message': message}, to='owner_room')# إرسال الإشعار للمطبخ
    socketio.emit('new_order', {'message': message}, to='owner_room')


    flash("✅ تم تأكيد طلبك بنجاح.")
    return redirect(url_for('order_waiting', order_id=order_id))

#---------------------------------------------------------------------------------------------------------------------
@app.route('/kitchen')
@login_required
def kitchen():
    if session.get('role_id') != 1:
        return redirect(url_for('login'))

    conn = get_db_connection()
    orders = conn.execute('''
        SELECT o.id, o.order_time, o.status, u.name , u.phone_number
        FROM orders o
        JOIN User u ON o.user_id = u.id
        WHERE o.status IN ("confirmed", "ready")
        ORDER BY o.order_time DESC
    ''').fetchall()

    order_data = []
    for order in orders:
        items = conn.execute('''
            SELECT od.quantity, od.base_price, od.extra_price, od.details_json, m.name
            FROM order_details od
            JOIN MenuItem m ON od.item_id = m.id
            WHERE od.order_id = ?
        ''', (order['id'],)).fetchall()
    
        items_list = []
        total = 0  
        for item in items:
            details = {}
            if item['details_json']:
                try:
                    details = json.loads(item['details_json'])
                except Exception:
                    details = {}
    
            item_total = (item['base_price'] + item['extra_price']) * item['quantity']
            total += item_total
    
            items_list.append({
                'name': item['name'],
                'quantity': item['quantity'],
                'base_price': item['base_price'],
                'extra_price': item['extra_price'],
                'fixed_ingredients': details.get('fixed_ingredients', []),
                'custom_options': details.get('custom_options', []),
                'notes': details.get('notes', ''),
                'item_total': item_total  
            })
    
        order_data.append({
            'id': order['id'],
            'order_time': order['order_time'],
            'status': order['status'],
            'name': order['name'],
            'phone_number': order['phone_number'],
            'items_count': len(items_list),
            'order_items': items_list,
            'total': round(total, 2) 
        })



    conn.close()
    return render_template('kitchen.html', orders=order_data)


@app.route('/admin/menu')
@login_required
def admin_menu():
    if session.get('role_id') != 1:
        flash("🚫 لا تملك صلاحية الدخول لهذه الصفحة.")
        return redirect(url_for('homepage'))
    return render_template('admin_menu.html', pagetitle="إدارة المنيو")



@app.route('/mark_ready/<int:order_id>')
@login_required
def mark_ready(order_id):
    
    
    if session.get('role_id') != 1:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # تحديث حالة الطلب إلى جاهز (مثلاً 'ready')
    conn.execute('UPDATE orders SET status = "ready" WHERE id = ?', (order_id,))
    conn.commit()

    # جلب user_id صاحب الطلب
    user = conn.execute('SELECT user_id FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()

    if user:
        student_room = f"user_{user['user_id']}"  # غرفة خاصة بكل طالب
        message = f"🍔 مرحبًا، طلبك رقم {order_id} أصبح جاهزًا!"
        socketio.emit('order_status', {'message': message}, to=student_room)

    flash(f"📢 تم وضع الطلب رقم {order_id} كجاهز.")
    return redirect(url_for('kitchen'))

#---------------------------------------------------------------------------------------------------------------------


@app.route('/order_waiting/<int:order_id>')
@login_required
def order_waiting(order_id):
    conn = get_db_connection()

    # جلب بيانات الطلب
    order = conn.execute('''
        SELECT id, order_time, status
        FROM orders
        WHERE id = ?
    ''', (order_id,)).fetchone()

    if not order:
        conn.close()
        flash("🚫 لم يتم العثور على الطلب.")
        return redirect(url_for('home'))

    # جلب عناصر الطلب
    rows = conn.execute('''
        SELECT od.quantity, od.base_price, od.extra_price, od.details_json,
               m.name AS item_name
        FROM order_details od
        JOIN MenuItem m ON od.item_id = m.id
        WHERE od.order_id = ?
    ''', (order_id,)).fetchall()

    order_items = []
    total = 0

    for row in rows:
        details = json.loads(row['details_json']) if row['details_json'] else {}
        fixed_ingredients = details.get('fixed_ingredients', [])
        custom_options = details.get('custom_options', [])
        notes = details.get('notes', '')

        total_price = row['base_price'] + row['extra_price']
        total += total_price * row['quantity']

        order_items.append({
            'item_name': row['item_name'],
            'quantity': row['quantity'],
            'base_price': row['base_price'],
            'extra_price': row['extra_price'],
            'fixed_ingredients': fixed_ingredients,
            'custom_options': custom_options,
            'notes': notes
        })

    conn.close()
    return render_template('order_confirmed.html', order=order, order_items=order_items, total=round(total, 2))




#---------------------------------------------------------------------------------------------------------------------

@app.route('/track')
@login_required
def track_latest_order():
    user_id = session.get('user_id')

    conn = get_db_connection()
    order = conn.execute('''
        SELECT id FROM orders
        WHERE user_id = ? AND status = 'confirmed'
        ORDER BY order_time DESC
        LIMIT 1
    ''', (user_id,)).fetchone()
    conn.close()

    if not order:
        flash(" لا يوجد طلب لتتبعه. اطلب الآن أولاً!")
        return redirect(url_for('homepage'))

    return redirect(url_for('order_waiting', order_id=order['id']))


#---------------------------------------------------------------------------------------------------------------------


@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    if user_id == 'owner_room':
        join_room('owner_room')
    else:
        join_room(f"user_{user_id}")


#---------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)