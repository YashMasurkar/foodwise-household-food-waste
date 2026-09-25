"""
Digital Food Waste Reduction and Awareness System for Households
B.Sc. Computer Science Community Engagement Project (CEP)
Backend Application - Flask & SQLite
"""

import os
import sqlite3
import json
import csv
import io
import re
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for, flash, g, Response, jsonify
)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cep-food-waste-reduction-2026-key')
DATABASE = os.path.join(app.root_path, 'database.db')


# ==============================================================================
# Database Connection & Initialization
# ==============================================================================
def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

def init_db():
    """Initializes SQLite tables from schema.sql if database does not exist."""
    db = get_db()
    cursor = db.cursor()
    # Check if food_items table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='food_items';")
    if not cursor.fetchone():
        schema_path = os.path.join(app.root_path, 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                db.cursor().executescript(f.read())
            db.commit()
            print("Database initialized successfully from schema.sql.")

@app.before_request
def ensure_db_initialized():
    """Ensure database exists before handling requests."""
    init_db()


# ==============================================================================
# Helper Utilities & Date Calculations
# ==============================================================================
def calculate_expiry_status(expiry_date_str):
    """
    Computes days remaining and status label based on current system date.
    Returns: (days_left, status_label)
    """
    try:
        exp_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        today = date.today()
        days_left = (exp_date - today).days

        if days_left < 0:
            return days_left, 'Expired'
        elif days_left == 0:
            return 0, 'Expiring Today'
        elif days_left <= 3:
            return days_left, 'Expiring Soon'
        else:
            return days_left, 'Fresh'
    except (ValueError, TypeError):
        return 0, 'Unknown'

def get_day_name(date_str):
    """Returns the English day name for a given YYYY-MM-DD date."""
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return d.strftime('%A')
    except (ValueError, TypeError):
        return ''


# ==============================================================================
# 1. Home / Landing Page
# ==============================================================================
@app.route('/')
def index():
    return render_template('index.html', active_page='index')


# ==============================================================================
# 2. System Dashboard
# ==============================================================================
@app.route('/dashboard')
def dashboard():
    db = get_db()

    # 1. Food Items Analysis
    food_rows = db.execute("SELECT * FROM food_items ORDER BY expiry_date ASC").fetchall()
    total_items = len(food_rows)
    expiring_soon_count = 0
    expired_count = 0
    expiring_items = []

    for row in food_rows:
        item = dict(row)
        days_left, status = calculate_expiry_status(item['expiry_date'])
        item['days_left'] = days_left
        item['status_label'] = status

        if status == 'Expired':
            expired_count += 1
            expiring_items.append(item)
        elif status in ['Expiring Today', 'Expiring Soon']:
            expiring_soon_count += 1
            expiring_items.append(item)

    # 2. Leftovers Count
    leftovers_count = db.execute("SELECT COUNT(*) as count FROM leftovers").fetchone()['count']

    # 3. Waste Records Aggregation
    waste_rows = db.execute("SELECT * FROM waste_records").fetchall()
    total_waste_records = len(waste_rows)
    total_waste_value = sum(float(r['estimated_value'] or 0.0) for r in waste_rows)

    # Waste by Category
    waste_by_category = db.execute("""
        SELECT category, SUM(quantity_wasted) as total_qty, COUNT(*) as count
        FROM waste_records
        GROUP BY category
        ORDER BY total_qty DESC
    """).fetchall()

    # Waste by Reason
    waste_by_reason = db.execute("""
        SELECT reason, COUNT(*) as count
        FROM waste_records
        GROUP BY reason
        ORDER BY count DESC
    """).fetchall()

    # Monthly Waste Loss Trend
    monthly_waste = db.execute("""
        SELECT SUBSTR(waste_date, 1, 7) as month, SUM(estimated_value) as total_val, COUNT(*) as count
        FROM waste_records
        GROUP BY SUBSTR(waste_date, 1, 7)
        ORDER BY month ASC
    """).fetchall()

    is_empty = (total_items == 0 and total_waste_records == 0 and leftovers_count == 0)

    metrics = {
        'total_items': total_items,
        'expiring_soon_count': expiring_soon_count,
        'expired_count': expired_count,
        'total_leftovers': leftovers_count,
        'total_waste_records': total_waste_records,
        'total_waste_value': total_waste_value,
        'is_empty': is_empty
    }

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        metrics=metrics,
        expiring_items=expiring_items[:8],
        waste_by_category=[dict(r) for r in waste_by_category],
        waste_by_reason=[dict(r) for r in waste_by_reason],
        monthly_waste=[dict(r) for r in monthly_waste]
    )


# ==============================================================================
# 3. Food Inventory Module
# ==============================================================================
@app.route('/inventory')
def inventory():
    sort_by = request.args.get('sort', 'expiry_asc')
    db = get_db()

    query = "SELECT * FROM food_items"
    if sort_by == 'expiry_desc':
        query += " ORDER BY expiry_date DESC"
    elif sort_by == 'name_asc':
        query += " ORDER BY name ASC"
    elif sort_by == 'date_desc':
        query += " ORDER BY created_at DESC"
    else:
        query += " ORDER BY expiry_date ASC"

    rows = db.execute(query).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        days_left, status = calculate_expiry_status(item['expiry_date'])
        item['days_left'] = days_left
        item['status_label'] = status
        items.append(item)

    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('inventory.html', active_page='inventory', items=items, sort_by=sort_by, today_date=today_str)

@app.route('/inventory/add', methods=['POST'])
def add_food():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    storage_type = request.form.get('storage_type', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    unit = request.form.get('unit', '').strip()
    purchase_date = request.form.get('purchase_date', '').strip()
    expiry_date = request.form.get('expiry_date', '').strip()
    notes = request.form.get('notes', '').strip()

    # Form Validation
    if not name or not category or not storage_type or not quantity_str or not unit or not purchase_date or not expiry_date:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('inventory'))

    try:
        quantity = float(quantity_str)
        if quantity <= 0:
            flash('Quantity must be a positive number.', 'danger')
            return redirect(url_for('inventory'))
        
        datetime.strptime(purchase_date, '%Y-%m-%d')
        datetime.strptime(expiry_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid numeric quantity or date format.', 'danger')
        return redirect(url_for('inventory'))

    db = get_db()
    db.execute("""
        INSERT INTO food_items (name, category, quantity, unit, purchase_date, expiry_date, storage_type, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category, quantity, unit, purchase_date, expiry_date, storage_type, notes))
    db.commit()

    flash(f'Food item "{name}" added to inventory successfully.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/edit/<int:item_id>', methods=['POST'])
def edit_food(item_id):
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    storage_type = request.form.get('storage_type', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    unit = request.form.get('unit', '').strip()
    purchase_date = request.form.get('purchase_date', '').strip()
    expiry_date = request.form.get('expiry_date', '').strip()
    notes = request.form.get('notes', '').strip()

    if not name or not category or not storage_type or not quantity_str or not unit or not purchase_date or not expiry_date:
        flash('All required fields must be populated.', 'danger')
        return redirect(url_for('inventory'))

    try:
        quantity = float(quantity_str)
        if quantity <= 0:
            flash('Quantity must be greater than zero.', 'danger')
            return redirect(url_for('inventory'))
        datetime.strptime(purchase_date, '%Y-%m-%d')
        datetime.strptime(expiry_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid quantity or date entered.', 'danger')
        return redirect(url_for('inventory'))

    db = get_db()
    db.execute("""
        UPDATE food_items
        SET name = ?, category = ?, quantity = ?, unit = ?, purchase_date = ?, expiry_date = ?, storage_type = ?, notes = ?
        WHERE id = ?
    """, (name, category, quantity, unit, purchase_date, expiry_date, storage_type, notes, item_id))
    db.commit()

    flash(f'Food item "{name}" updated successfully.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/delete/<int:item_id>', methods=['POST'])
def delete_food(item_id):
    db = get_db()
    db.execute("DELETE FROM food_items WHERE id = ?", (item_id,))
    db.commit()
    flash('Food item removed from inventory.', 'info')
    return redirect(url_for('inventory'))


# ==============================================================================
# 4. Expiry Tracker Module
# ==============================================================================
@app.route('/expiry-tracker')
def expiry_tracker():
    db = get_db()
    rows = db.execute("SELECT * FROM food_items ORDER BY expiry_date ASC").fetchall()

    all_items = []
    expired_items = []
    today_items = []
    soon_items = []
    fresh_items = []

    for row in rows:
        item = dict(row)
        days_left, status = calculate_expiry_status(item['expiry_date'])
        item['days_left'] = days_left
        item['status_label'] = status
        all_items.append(item)

        if status == 'Expired':
            expired_items.append(item)
        elif status == 'Expiring Today':
            today_items.append(item)
        elif status == 'Expiring Soon':
            soon_items.append(item)
        else:
            fresh_items.append(item)

    return render_template(
        'expiry_tracker.html',
        active_page='expiry_tracker',
        all_items=all_items,
        expired_items=expired_items,
        today_items=today_items,
        soon_items=soon_items,
        fresh_items=fresh_items
    )


# ==============================================================================
# 5. Meal Planner Module
# ==============================================================================
@app.route('/meal-planner')
def meal_planner():
    db = get_db()
    meal_rows = db.execute("SELECT * FROM meal_plans ORDER BY meal_date ASC").fetchall()
    meal_plans = []
    for row in meal_rows:
        m = dict(row)
        m['day_name'] = get_day_name(m['meal_date'])
        meal_plans.append(m)

    # Dynamic suggestions based on active inventory items expiring in <= 3 days
    food_rows = db.execute("SELECT * FROM food_items ORDER BY expiry_date ASC").fetchall()
    expiring_suggestions = []
    for row in food_rows:
        item = dict(row)
        days_left, status = calculate_expiry_status(item['expiry_date'])
        if 0 <= days_left <= 3:
            item['days_left'] = days_left
            expiring_suggestions.append(item)

    today_str = date.today().strftime('%Y-%m-%d')
    return render_template(
        'meal_planner.html',
        active_page='meal_planner',
        meal_plans=meal_plans,
        expiring_suggestions=expiring_suggestions,
        today_date=today_str
    )

@app.route('/meal-planner/add', methods=['POST'])
def add_meal():
    meal_name = request.form.get('meal_name', '').strip()
    ingredients = request.form.get('ingredients', '').strip()
    meal_type = request.form.get('meal_type', '').strip()
    meal_date = request.form.get('meal_date', '').strip()
    notes = request.form.get('notes', '').strip()

    if not meal_name or not ingredients or not meal_type or not meal_date:
        flash('Please fill in all required meal planning fields.', 'danger')
        return redirect(url_for('meal_planner'))

    try:
        datetime.strptime(meal_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid meal date format.', 'danger')
        return redirect(url_for('meal_planner'))

    db = get_db()
    db.execute("""
        INSERT INTO meal_plans (meal_name, ingredients, meal_type, meal_date, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (meal_name, ingredients, meal_type, meal_date, notes))
    db.commit()

    flash(f'Meal plan "{meal_name}" scheduled successfully.', 'success')
    return redirect(url_for('meal_planner'))

@app.route('/meal-planner/edit/<int:meal_id>', methods=['POST'])
def edit_meal(meal_id):
    meal_name = request.form.get('meal_name', '').strip()
    ingredients = request.form.get('ingredients', '').strip()
    meal_type = request.form.get('meal_type', '').strip()
    meal_date = request.form.get('meal_date', '').strip()
    notes = request.form.get('notes', '').strip()

    if not meal_name or not ingredients or not meal_type or not meal_date:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('meal_planner'))

    try:
        datetime.strptime(meal_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date entered.', 'danger')
        return redirect(url_for('meal_planner'))

    db = get_db()
    db.execute("""
        UPDATE meal_plans
        SET meal_name = ?, ingredients = ?, meal_type = ?, meal_date = ?, notes = ?
        WHERE id = ?
    """, (meal_name, ingredients, meal_type, meal_date, notes, meal_id))
    db.commit()

    flash(f'Meal plan "{meal_name}" updated.', 'success')
    return redirect(url_for('meal_planner'))

@app.route('/meal-planner/delete/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    db = get_db()
    db.execute("DELETE FROM meal_plans WHERE id = ?", (meal_id,))
    db.commit()
    flash('Meal plan deleted.', 'info')
    return redirect(url_for('meal_planner'))


# ==============================================================================
# 6. Leftovers Management Module
# ==============================================================================
@app.route('/leftovers')
def leftovers():
    db = get_db()
    rows = db.execute("SELECT * FROM leftovers ORDER BY consume_before ASC").fetchall()
    leftovers_list = []
    for row in rows:
        item = dict(row)
        days_left, _ = calculate_expiry_status(item['consume_before'])
        item['days_left'] = days_left
        leftovers_list.append(item)

    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('leftovers.html', active_page='leftovers', leftovers=leftovers_list, today_date=today_str)

@app.route('/leftovers/add', methods=['POST'])
def add_leftover():
    food_name = request.form.get('food_name', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    unit = request.form.get('unit', '').strip()
    date_prepared = request.form.get('date_prepared', '').strip()
    storage_method = request.form.get('storage_method', '').strip()
    consume_before = request.form.get('consume_before', '').strip()
    notes = request.form.get('notes', '').strip()

    if not food_name or not quantity_str or not unit or not date_prepared or not storage_method or not consume_before:
        flash('All required leftover fields must be completed.', 'danger')
        return redirect(url_for('leftovers'))

    try:
        quantity = float(quantity_str)
        if quantity <= 0:
            flash('Quantity must be greater than zero.', 'danger')
            return redirect(url_for('leftovers'))
        datetime.strptime(date_prepared, '%Y-%m-%d')
        datetime.strptime(consume_before, '%Y-%m-%d')
    except ValueError:
        flash('Invalid quantity or date format.', 'danger')
        return redirect(url_for('leftovers'))

    db = get_db()
    db.execute("""
        INSERT INTO leftovers (food_name, quantity, unit, date_prepared, storage_method, consume_before, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (food_name, quantity, unit, date_prepared, storage_method, consume_before, notes))
    db.commit()

    flash(f'Leftover record for "{food_name}" saved.', 'success')
    return redirect(url_for('leftovers'))

@app.route('/leftovers/edit/<int:leftover_id>', methods=['POST'])
def edit_leftover(leftover_id):
    food_name = request.form.get('food_name', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    unit = request.form.get('unit', '').strip()
    date_prepared = request.form.get('date_prepared', '').strip()
    storage_method = request.form.get('storage_method', '').strip()
    consume_before = request.form.get('consume_before', '').strip()
    notes = request.form.get('notes', '').strip()

    if not food_name or not quantity_str or not unit or not date_prepared or not storage_method or not consume_before:
        flash('All required fields must be filled.', 'danger')
        return redirect(url_for('leftovers'))

    try:
        quantity = float(quantity_str)
        if quantity <= 0:
            flash('Quantity must be greater than zero.', 'danger')
            return redirect(url_for('leftovers'))
        datetime.strptime(date_prepared, '%Y-%m-%d')
        datetime.strptime(consume_before, '%Y-%m-%d')
    except ValueError:
        flash('Invalid input entered.', 'danger')
        return redirect(url_for('leftovers'))

    db = get_db()
    db.execute("""
        UPDATE leftovers
        SET food_name = ?, quantity = ?, unit = ?, date_prepared = ?, storage_method = ?, consume_before = ?, notes = ?
        WHERE id = ?
    """, (food_name, quantity, unit, date_prepared, storage_method, consume_before, notes, leftover_id))
    db.commit()

    flash(f'Leftover record "{food_name}" updated.', 'success')
    return redirect(url_for('leftovers'))

@app.route('/leftovers/delete/<int:leftover_id>', methods=['POST'])
def delete_leftover(leftover_id):
    db = get_db()
    db.execute("DELETE FROM leftovers WHERE id = ?", (leftover_id,))
    db.commit()
    flash('Leftover record removed.', 'info')
    return redirect(url_for('leftovers'))


# ==============================================================================
# 7. Food Waste Tracking Module
# ==============================================================================
@app.route('/waste-tracking')
def waste_tracking():
    db = get_db()
    waste_rows = db.execute("SELECT * FROM waste_records ORDER BY waste_date DESC").fetchall()
    waste_records = [dict(r) for r in waste_rows]

    # Calculate weight in standard kg where possible (kg directly, g / 1000)
    total_weight_kg = 0.0
    for r in waste_records:
        qty = float(r['quantity_wasted'] or 0.0)
        u = (r['unit'] or '').lower()
        if u == 'kg':
            total_weight_kg += qty
        elif u == 'g':
            total_weight_kg += (qty / 1000.0)

    total_monetary_loss = sum(float(r['estimated_value'] or 0.0) for r in waste_records)

    # Waste by Category
    waste_by_category = db.execute("""
        SELECT category, SUM(quantity_wasted) as total_qty, COUNT(*) as count
        FROM waste_records
        GROUP BY category
        ORDER BY total_qty DESC
    """).fetchall()

    # Waste by Reason
    waste_by_reason = db.execute("""
        SELECT reason, COUNT(*) as count
        FROM waste_records
        GROUP BY reason
        ORDER BY count DESC
    """).fetchall()

    top_category = waste_by_category[0]['category'] if waste_by_category else None

    today_str = date.today().strftime('%Y-%m-%d')
    return render_template(
        'waste_tracking.html',
        active_page='waste_tracking',
        waste_records=waste_records,
        total_weight_kg=total_weight_kg,
        total_monetary_loss=total_monetary_loss,
        top_category=top_category,
        waste_by_category=[dict(r) for r in waste_by_category],
        waste_by_reason=[dict(r) for r in waste_by_reason],
        today_date=today_str
    )

@app.route('/waste-tracking/add', methods=['POST'])
def add_waste():
    food_item = request.form.get('food_item', '').strip()
    category = request.form.get('category', '').strip()
    quantity_str = request.form.get('quantity_wasted', '').strip()
    unit = request.form.get('unit', '').strip()
    waste_date = request.form.get('waste_date', '').strip()
    reason = request.form.get('reason', '').strip()
    estimated_val_str = request.form.get('estimated_value', '0').strip()
    remarks = request.form.get('remarks', '').strip()

    if not food_item or not category or not quantity_str or not unit or not waste_date or not reason:
        flash('Please fill in all mandatory waste record fields.', 'danger')
        return redirect(url_for('waste_tracking'))

    try:
        quantity_wasted = float(quantity_str)
        estimated_value = float(estimated_val_str or 0.0)
        if quantity_wasted <= 0 or estimated_value < 0:
            flash('Quantity must be positive and estimated value non-negative.', 'danger')
            return redirect(url_for('waste_tracking'))
        datetime.strptime(waste_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid numeric value or date entered.', 'danger')
        return redirect(url_for('waste_tracking'))

    db = get_db()
    db.execute("""
        INSERT INTO waste_records (food_item, category, quantity_wasted, unit, waste_date, reason, estimated_value, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (food_item, category, quantity_wasted, unit, waste_date, reason, estimated_value, remarks))
    db.commit()

    flash(f'Waste record for "{food_item}" logged successfully.', 'success')
    return redirect(url_for('waste_tracking'))

@app.route('/waste-tracking/edit/<int:waste_id>', methods=['POST'])
def edit_waste(waste_id):
    food_item = request.form.get('food_item', '').strip()
    category = request.form.get('category', '').strip()
    quantity_str = request.form.get('quantity_wasted', '').strip()
    unit = request.form.get('unit', '').strip()
    waste_date = request.form.get('waste_date', '').strip()
    reason = request.form.get('reason', '').strip()
    estimated_val_str = request.form.get('estimated_value', '0').strip()
    remarks = request.form.get('remarks', '').strip()

    if not food_item or not category or not quantity_str or not unit or not waste_date or not reason:
        flash('All mandatory fields must be completed.', 'danger')
        return redirect(url_for('waste_tracking'))

    try:
        quantity_wasted = float(quantity_str)
        estimated_value = float(estimated_val_str or 0.0)
        if quantity_wasted <= 0 or estimated_value < 0:
            flash('Invalid quantities or monetary values.', 'danger')
            return redirect(url_for('waste_tracking'))
        datetime.strptime(waste_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid input.', 'danger')
        return redirect(url_for('waste_tracking'))

    db = get_db()
    db.execute("""
        UPDATE waste_records
        SET food_item = ?, category = ?, quantity_wasted = ?, unit = ?, waste_date = ?, reason = ?, estimated_value = ?, remarks = ?
        WHERE id = ?
    """, (food_item, category, quantity_wasted, unit, waste_date, reason, estimated_value, remarks, waste_id))
    db.commit()

    flash(f'Waste record "{food_item}" updated.', 'success')
    return redirect(url_for('waste_tracking'))

@app.route('/waste-tracking/delete/<int:waste_id>', methods=['POST'])
def delete_waste(waste_id):
    db = get_db()
    db.execute("DELETE FROM waste_records WHERE id = ?", (waste_id,))
    db.commit()
    flash('Waste record deleted.', 'info')
    return redirect(url_for('waste_tracking'))


# ==============================================================================
# 8. Official CEP Survey Data Entry & Import Module
# ==============================================================================
ALLOWED_SURVEY_VALUES = {
    'household_size': ['1–2', '3–4', '5–6', 'More than 6'],
    'food_manager': ['Self', 'Parent/Guardian', 'Spouse', 'Shared responsibility', 'Other'],
    'waste_frequency': ['Daily', 'Several times a week', 'Once a week', 'Occasionally', 'Rarely', 'Never'],
    'weekly_waste_amount': ['Less than 1 kg', '1–2 kg', '2–5 kg', 'More than 5 kg', 'Not sure'],
    'common_waste_category': ['Cooked food', 'Vegetables', 'Fruits', 'Dairy', 'Bakery', 'Grains/Rice', 'Meat/Eggs', 'Other'],
    'waste_reasons': ['Cooking too much', 'Expiry', 'Spoilage', 'Leftovers not consumed', 'Excess purchasing', 'Improper storage', 'Change in preference', 'Other'],
    'check_expiry_freq': ['Always', 'Often', 'Sometimes', 'Rarely', 'Never'],
    'meal_planning_freq': ['Always', 'Often', 'Sometimes', 'Rarely', 'Never'],
    'leftover_practice': ['Reuse it in another meal', 'Store it for later', 'Give it to someone', 'Dispose of it', 'Compost it', 'Other'],
    'storage_location': ['Refrigerator', 'Freezer', 'Pantry', 'Room Temperature', 'Depends on the food item'],
    'impact_awareness': ['Very aware', 'Somewhat aware', 'Neutral', 'Slightly aware', 'Not aware'],
    'current_practices': ['Meal planning', 'Checking expiry dates', 'Buying only what is required', 'Proper food storage', 'Reusing leftovers', 'Composting', 'Donating suitable surplus', 'None of these'],
    'digital_tool_interest': ['Yes', 'Maybe', 'No'],
    'useful_features': ['Food inventory', 'Expiry reminders', 'Meal planner', 'Leftover management', 'Waste tracking', 'Food-waste awareness/tips', 'Waste analysis/charts', 'Other'],
    'biggest_problem_to_solve': ['Forgetting expiry dates', 'Buying too much food', 'Cooking excess food', 'Managing leftovers', 'Food storage', 'Tracking food waste', 'Other']
}

@app.route('/survey/data')
def survey_data():
    db = get_db()
    rows = db.execute("SELECT * FROM survey_responses ORDER BY id DESC").fetchall()
    responses = [dict(r) for r in rows]
    return render_template('survey_data.html', active_page='survey_data', responses=responses)

@app.route('/survey/data/add', methods=['POST'])
def add_survey_response():
    household_size = request.form.get('household_size', '').strip()
    food_manager = request.form.get('food_manager', '').strip()
    waste_frequency = request.form.get('waste_frequency', '').strip()
    weekly_waste_amount = request.form.get('weekly_waste_amount', '').strip()
    common_waste_category = request.form.get('common_waste_category', '').strip()
    waste_reasons_list = request.form.getlist('waste_reasons')
    check_expiry_freq = request.form.get('check_expiry_freq', '').strip()
    meal_planning_freq = request.form.get('meal_planning_freq', '').strip()
    leftover_practice = request.form.get('leftover_practice', '').strip()
    storage_location = request.form.get('storage_location', '').strip()
    impact_awareness = request.form.get('impact_awareness', '').strip()
    current_practices_list = request.form.getlist('current_practices')
    digital_tool_interest = request.form.get('digital_tool_interest', '').strip()
    useful_features_list = request.form.getlist('useful_features')
    biggest_problem_to_solve = request.form.get('biggest_problem_to_solve', '').strip()
    biggest_challenge = request.form.get('biggest_challenge', '').strip()
    improvement_suggestions = request.form.get('improvement_suggestions', '').strip()

    # Required validation
    if not (household_size and food_manager and waste_frequency and weekly_waste_amount and 
            common_waste_category and waste_reasons_list and check_expiry_freq and 
            meal_planning_freq and leftover_practice and storage_location and 
            impact_awareness and current_practices_list and digital_tool_interest and 
            useful_features_list and biggest_problem_to_solve and biggest_challenge):
        flash('Please complete all mandatory questionnaire fields.', 'danger')
        return redirect(url_for('survey_data'))

    # Store multi-selects as JSON strings
    waste_reasons_json = json.dumps(waste_reasons_list)
    current_practices_json = json.dumps(current_practices_list)
    useful_features_json = json.dumps(useful_features_list)

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    db.execute("""
        INSERT INTO survey_responses (
            submission_timestamp, household_size, food_manager, waste_frequency, weekly_waste_amount,
            common_waste_category, waste_reasons, check_expiry_freq, meal_planning_freq, leftover_practice,
            storage_location, impact_awareness, current_practices, digital_tool_interest, useful_features,
            biggest_problem_to_solve, biggest_challenge, improvement_suggestions
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_str, household_size, food_manager, waste_frequency, weekly_waste_amount,
        common_waste_category, waste_reasons_json, check_expiry_freq, meal_planning_freq, leftover_practice,
        storage_location, impact_awareness, current_practices_json, digital_tool_interest, useful_features_json,
        biggest_problem_to_solve, biggest_challenge, improvement_suggestions
    ))
    db.commit()

    flash('Survey response successfully saved to database.', 'success')
    return redirect(url_for('survey_data'))

@app.route('/survey/data/delete/<int:resp_id>', methods=['POST'])
def delete_survey_response(resp_id):
    db = get_db()
    db.execute("DELETE FROM survey_responses WHERE id = ?", (resp_id,))
    db.commit()
    flash('Survey response record deleted.', 'info')
    return redirect(url_for('survey_data'))

@app.route('/survey/data/download-template')
def download_csv_template():
    headers = [
        'household_size', 'food_manager', 'waste_frequency', 'weekly_waste_amount',
        'common_waste_category', 'waste_reasons', 'check_expiry_freq', 'meal_planning_freq',
        'leftover_practice', 'storage_location', 'impact_awareness', 'current_practices',
        'digital_tool_interest', 'useful_features', 'biggest_problem_to_solve',
        'biggest_challenge', 'improvement_suggestions'
    ]
    sample_row = [
        '3–4', 'Self', 'Occasionally', '1–2 kg', 'Cooked food',
        'Cooking too much, Leftovers not consumed', 'Often', 'Sometimes',
        'Reuse it in another meal', 'Refrigerator', 'Very aware',
        'Checking expiry dates, Proper food storage', 'Yes',
        'Food inventory, Expiry reminders, Meal planner', 'Forgetting expiry dates',
        'Busy weekday schedules lead to forgotten fridge produce',
        'Mobile app reminders would be very helpful'
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(sample_row)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=cep_survey_template.csv"}
    )

# ==============================================================================
# Survey CSV Header Aliases & Normalization Helpers
# ==============================================================================
CANONICAL_SURVEY_COLUMNS = [
    'household_size', 'food_manager', 'waste_frequency', 'weekly_waste_amount',
    'common_waste_category', 'waste_reasons', 'check_expiry_freq', 'meal_planning_freq',
    'leftover_practice', 'storage_location', 'impact_awareness', 'current_practices',
    'digital_tool_interest', 'useful_features', 'biggest_problem_to_solve',
    'biggest_challenge', 'improvement_suggestions'
]

SURVEY_HEADER_ALIASES = {
    # 1. Timestamp
    'timestamp': 'submission_timestamp',
    'submission_timestamp': 'submission_timestamp',
    'submission timestamp': 'submission_timestamp',
    
    # 2. Q1 (Household Size)
    'what is the size of your household?': 'household_size',
    'what is the size of your household': 'household_size',
    'household_size': 'household_size',
    'household size': 'household_size',
    
    # 3. Q2 (Food Manager)
    'who is mainly responsible for preparing food in your household?': 'food_manager',
    'who is mainly responsible for preparing food in your household': 'food_manager',
    'who mainly manages food preparation in your household?': 'food_manager',
    'who mainly manages food preparation in your household': 'food_manager',
    'food_manager': 'food_manager',
    'food manager': 'food_manager',
    
    # 4. Q3 (Waste Frequency)
    'how often does food get wasted in your household?': 'waste_frequency',
    'how often does food get wasted in your household': 'waste_frequency',
    'how often does food wastage occur?': 'waste_frequency',
    'how often does food wastage occur': 'waste_frequency',
    'waste_frequency': 'waste_frequency',
    'waste frequency': 'waste_frequency',
    
    # 5. Q4 (Weekly Waste Amount)
    'approximately how much food is wasted in your household per week?': 'weekly_waste_amount',
    'approximately how much food is wasted in your household per week': 'weekly_waste_amount',
    'approx. weekly wasted food quantity?': 'weekly_waste_amount',
    'approx. weekly wasted food quantity': 'weekly_waste_amount',
    'weekly_waste_amount': 'weekly_waste_amount',
    'weekly waste amount': 'weekly_waste_amount',
    
    # 6. Q5 (Common Waste Category)
    'which type of food is most commonly wasted in your household?': 'common_waste_category',
    'which type of food is most commonly wasted in your household': 'common_waste_category',
    'most commonly wasted food category?': 'common_waste_category',
    'most commonly wasted food category': 'common_waste_category',
    'common_waste_category': 'common_waste_category',
    'common waste category': 'common_waste_category',
    
    # 7. Q6 (Waste Reasons - Multi)
    'what are the main reasons food gets wasted in your household?': 'waste_reasons',
    'what are the main reasons food gets wasted in your household': 'waste_reasons',
    'what are the reasons for food wastage in your household?': 'waste_reasons',
    'what are the reasons for food wastage in your household': 'waste_reasons',
    'waste_reasons': 'waste_reasons',
    'waste reasons': 'waste_reasons',
    
    # 8. Q7 (Check Expiry Freq)
    'how often do you check expiry or best-before dates before using food?': 'check_expiry_freq',
    'how often do you check expiry or best-before dates before using food': 'check_expiry_freq',
    'how often do you check food expiry dates?': 'check_expiry_freq',
    'how often do you check food expiry dates': 'check_expiry_freq',
    'check_expiry_freq': 'check_expiry_freq',
    'check expiry freq': 'check_expiry_freq',
    
    # 9. Q8 (Meal Planning Freq)
    'how often does your household plan meals in advance?': 'meal_planning_freq',
    'how often does your household plan meals in advance': 'meal_planning_freq',
    'how often do you plan meals before cooking?': 'meal_planning_freq',
    'how often do you plan meals before cooking': 'meal_planning_freq',
    'meal_planning_freq': 'meal_planning_freq',
    'meal planning freq': 'meal_planning_freq',
    
    # 10. Q9 (Leftover Practice)
    'what does your household usually do with leftover food?': 'leftover_practice',
    'what does your household usually do with leftover food': 'leftover_practice',
    'leftover_practice': 'leftover_practice',
    'leftover practice': 'leftover_practice',
    
    # 11. Q10 (Storage Location)
    'where is food usually stored in your household?': 'storage_location',
    'where is food usually stored in your household': 'storage_location',
    'where do you usually store food items?': 'storage_location',
    'where do you usually store food items': 'storage_location',
    'storage_location': 'storage_location',
    'storage location': 'storage_location',
    
    # 12. Q11 (Impact Awareness)
    'how aware are you of the environmental and economic impact of food waste?': 'impact_awareness',
    'how aware are you of the environmental and economic impact of food waste': 'impact_awareness',
    'awareness of environmental & economic impact of food waste?': 'impact_awareness',
    'awareness of environmental & economic impact of food waste': 'impact_awareness',
    'impact_awareness': 'impact_awareness',
    'impact awareness': 'impact_awareness',
    
    # 13. Q12 (Current Practices - Multi)
    'which of the following practices does your household currently use to reduce food waste?': 'current_practices',
    'which of the following practices does your household currently use to reduce food waste': 'current_practices',
    'which practices do you currently use to reduce food waste?': 'current_practices',
    'which practices do you currently use to reduce food waste': 'current_practices',
    'current_practices': 'current_practices',
    'current practices': 'current_practices',
    
    # 14. Q13 (Digital Tool Interest)
    'would you use a digital app or tool to help reduce food waste at home?': 'digital_tool_interest',
    'would you use a digital app or tool to help reduce food waste at home': 'digital_tool_interest',
    'would you use a digital application to reduce food waste?': 'digital_tool_interest',
    'would you use a digital application to reduce food waste': 'digital_tool_interest',
    'digital_tool_interest': 'digital_tool_interest',
    'digital tool interest': 'digital_tool_interest',
    
    # 15. Q14 (Useful Features - Multi)
    'which features would be most useful in a food-waste reduction application?': 'useful_features',
    'which features would be most useful in a food-waste reduction application': 'useful_features',
    'which digital features would be most useful?': 'useful_features',
    'which digital features would be most useful': 'useful_features',
    'useful_features': 'useful_features',
    'useful features': 'useful_features',
    
    # 16. Q15 (Biggest Problem to Solve)
    'which household food-waste problem would you most like a digital solution to help solve?': 'biggest_problem_to_solve',
    'which household food-waste problem would you most like a digital solution to help solve': 'biggest_problem_to_solve',
    "problem you'd most like a digital tool to solve?": 'biggest_problem_to_solve',
    "problem you'd most like a digital tool to solve": 'biggest_problem_to_solve',
    'biggest_problem_to_solve': 'biggest_problem_to_solve',
    'biggest problem to solve': 'biggest_problem_to_solve',
    
    # 17. Q16 (Biggest Challenge)
    'what is the biggest challenge you face when trying to reduce food waste at home?': 'biggest_challenge',
    'what is the biggest challenge you face when trying to reduce food waste at home': 'biggest_challenge',
    'what is the biggest challenge you face in reducing food waste at home?': 'biggest_challenge',
    'what is the biggest challenge you face in reducing food waste at home': 'biggest_challenge',
    'biggest_challenge': 'biggest_challenge',
    'biggest challenge': 'biggest_challenge',
    
    # 18. Q17 (Suggestions - Optional)
    'do you have any suggestions for reducing food waste or improving a digital food-waste management solution?': 'improvement_suggestions',
    'do you have any suggestions for reducing food waste or improving a digital food-waste management solution': 'improvement_suggestions',
    'do you have any suggestions for improving household food-waste management?': 'improvement_suggestions',
    'do you have any suggestions for improving household food-waste management': 'improvement_suggestions',
    'improvement_suggestions': 'improvement_suggestions',
    'improvement suggestions': 'improvement_suggestions',
}

def normalize_survey_option(val, allowed_options):
    """Normalizes option values (e.g. hyphens/en-dashes, casing, whitespace) to match allowed choices."""
    if not val:
        return ''
    val_clean = str(val).strip()
    if val_clean in allowed_options:
        return val_clean
    # Normalize dashes/hyphens
    norm_val = val_clean.replace('–', '-').replace('—', '-').lower()
    for opt in allowed_options:
        if opt.replace('–', '-').replace('—', '-').lower() == norm_val:
            return opt
    # Match case-insensitively
    for opt in allowed_options:
        if opt.lower() == val_clean.lower():
            return opt
    return val_clean

def parse_survey_multiselect(val, allowed_options=None):
    """Parses multi-select checkboxes separated by semicolons or commas into a clean list."""
    if not val:
        return []
    val_str = str(val).strip()
    if not val_str:
        return []
    # Check if already a JSON list
    if val_str.startswith('[') and val_str.endswith(']'):
        try:
            items = json.loads(val_str)
            if isinstance(items, list):
                res = [str(x).strip() for x in items if str(x).strip()]
                if allowed_options:
                    res = [normalize_survey_option(x, allowed_options) for x in res]
                return res
        except (json.JSONDecodeError, TypeError):
            pass
    # Split by semicolon or comma
    items = [x.strip() for x in re.split(r'[;,]', val_str) if x.strip()]
    if allowed_options:
        items = [normalize_survey_option(x, allowed_options) for x in items]
    return items

@app.route('/survey/data/import-csv', methods=['POST'])
def import_survey_csv():
    if 'csv_file' not in request.files:
        flash('No file selected for import.', 'danger')
        return redirect(url_for('survey_data'))

    file = request.files['csv_file']
    if file.filename == '':
        flash('Please select a valid CSV file.', 'danger')
        return redirect(url_for('survey_data'))

    try:
        raw_text = file.stream.read().decode("utf-8-sig", errors="replace")
        stream = io.StringIO(raw_text, newline=None)
        reader = csv.reader(stream)
        
        headers = next(reader, None)
        if not headers:
            flash('Uploaded CSV file is empty.', 'danger')
            return redirect(url_for('survey_data'))

        # Map each CSV column index to its canonical field name
        col_to_canonical = {}
        for idx, h in enumerate(headers):
            h_norm = re.sub(r'\s+', ' ', (h or '').strip()).lower()
            if h_norm in SURVEY_HEADER_ALIASES:
                col_to_canonical[idx] = SURVEY_HEADER_ALIASES[h_norm]
            else:
                # Partial match for question headers
                for alias_k, canonical_v in SURVEY_HEADER_ALIASES.items():
                    if alias_k in h_norm or h_norm in alias_k:
                        col_to_canonical[idx] = canonical_v
                        break

        # Positional fallbacks for standard 18-col Google Form or 17-col template
        if len(col_to_canonical) < 10 and len(headers) == 18:
            positional_map = [
                'submission_timestamp', 'household_size', 'food_manager', 'waste_frequency',
                'weekly_waste_amount', 'common_waste_category', 'waste_reasons', 'check_expiry_freq',
                'meal_planning_freq', 'leftover_practice', 'storage_location', 'impact_awareness',
                'current_practices', 'digital_tool_interest', 'useful_features',
                'biggest_problem_to_solve', 'biggest_challenge', 'improvement_suggestions'
            ]
            for idx, canonical_v in enumerate(positional_map):
                col_to_canonical[idx] = canonical_v
        elif len(col_to_canonical) < 10 and len(headers) == 17:
            for idx, canonical_v in enumerate(CANONICAL_SURVEY_COLUMNS):
                col_to_canonical[idx] = canonical_v

        # Validate that essential survey fields are mapped
        core_fields = ['household_size', 'food_manager', 'waste_frequency', 'weekly_waste_amount']
        mapped_canonicals = set(col_to_canonical.values())
        if not all(cf in mapped_canonicals for cf in core_fields):
            flash('CSV headers could not be recognized. Please check column format or use the official template.', 'danger')
            return redirect(url_for('survey_data'))

        db = get_db()
        imported_count = 0
        skipped_duplicates = 0
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for row_idx, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue  # Skip completely blank lines

            # Extract fields by mapped canonical name
            row_dict = {}
            for col_idx, val in enumerate(row):
                if col_idx in col_to_canonical:
                    row_dict[col_to_canonical[col_idx]] = val.strip()

            # Values extraction & normalization
            sub_ts = row_dict.get('submission_timestamp') or now_str
            h_size = normalize_survey_option(row_dict.get('household_size', ''), ALLOWED_SURVEY_VALUES['household_size'])
            f_mgr = normalize_survey_option(row_dict.get('food_manager', ''), ALLOWED_SURVEY_VALUES['food_manager'])
            w_freq = normalize_survey_option(row_dict.get('waste_frequency', ''), ALLOWED_SURVEY_VALUES['waste_frequency'])
            w_amt = normalize_survey_option(row_dict.get('weekly_waste_amount', ''), ALLOWED_SURVEY_VALUES['weekly_waste_amount'])
            w_cat = normalize_survey_option(row_dict.get('common_waste_category', ''), ALLOWED_SURVEY_VALUES['common_waste_category'])
            
            reasons_list = parse_survey_multiselect(row_dict.get('waste_reasons', ''), ALLOWED_SURVEY_VALUES['waste_reasons'])
            
            chk_exp = normalize_survey_option(row_dict.get('check_expiry_freq', ''), ALLOWED_SURVEY_VALUES['check_expiry_freq'])
            meal_plan = normalize_survey_option(row_dict.get('meal_planning_freq', ''), ALLOWED_SURVEY_VALUES['meal_planning_freq'])
            left_prac = normalize_survey_option(row_dict.get('leftover_practice', ''), ALLOWED_SURVEY_VALUES['leftover_practice'])
            store_loc = normalize_survey_option(row_dict.get('storage_location', ''), ALLOWED_SURVEY_VALUES['storage_location'])
            awareness = normalize_survey_option(row_dict.get('impact_awareness', ''), ALLOWED_SURVEY_VALUES['impact_awareness'])
            
            practices_list = parse_survey_multiselect(row_dict.get('current_practices', ''), ALLOWED_SURVEY_VALUES['current_practices'])
            
            dig_int = normalize_survey_option(row_dict.get('digital_tool_interest', ''), ALLOWED_SURVEY_VALUES['digital_tool_interest'])
            
            features_list = parse_survey_multiselect(row_dict.get('useful_features', ''), ALLOWED_SURVEY_VALUES['useful_features'])
            
            big_prob = normalize_survey_option(row_dict.get('biggest_problem_to_solve', ''), ALLOWED_SURVEY_VALUES['biggest_problem_to_solve'])
            challenge = row_dict.get('biggest_challenge', '').strip()
            suggestions = row_dict.get('improvement_suggestions', '').strip()

            reasons_json = json.dumps(reasons_list)
            practices_json = json.dumps(practices_list)
            features_json = json.dumps(features_list)

            # Prevent duplicate entries if CSV import is run multiple times
            existing = db.execute("""
                SELECT id FROM survey_responses 
                WHERE (submission_timestamp = ? AND household_size = ? AND food_manager = ? AND waste_frequency = ?)
                   OR (household_size = ? AND food_manager = ? AND waste_frequency = ? AND weekly_waste_amount = ? AND common_waste_category = ? AND waste_reasons = ? AND biggest_challenge = ?)
            """, (
                sub_ts, h_size, f_mgr, w_freq,
                h_size, f_mgr, w_freq, w_amt, w_cat, reasons_json, challenge
            )).fetchone()

            if existing:
                skipped_duplicates += 1
                continue

            db.execute("""
                INSERT INTO survey_responses (
                    submission_timestamp, household_size, food_manager, waste_frequency, weekly_waste_amount,
                    common_waste_category, waste_reasons, check_expiry_freq, meal_planning_freq, leftover_practice,
                    storage_location, impact_awareness, current_practices, digital_tool_interest, useful_features,
                    biggest_problem_to_solve, biggest_challenge, improvement_suggestions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sub_ts, h_size, f_mgr, w_freq, w_amt,
                w_cat, reasons_json, chk_exp, meal_plan, left_prac,
                store_loc, awareness, practices_json, dig_int, features_json,
                big_prob, challenge, suggestions
            ))
            imported_count += 1

        db.commit()
        if imported_count > 0:
            msg = f'Successfully imported {imported_count} survey responses from CSV.'
            if skipped_duplicates > 0:
                msg += f' ({skipped_duplicates} duplicate responses skipped).'
            flash(msg, 'success')
        elif skipped_duplicates > 0:
            flash(f'All {skipped_duplicates} rows in the CSV were already imported previously (duplicates skipped).', 'info')
        else:
            flash('No valid survey rows could be imported from the CSV.', 'danger')

    except Exception as e:
        flash(f'Error reading CSV file: {str(e)}', 'danger')

    return redirect(url_for('survey_data'))


# ==============================================================================
# 9. Survey Results & Live Dynamic Analytics
# ==============================================================================
def aggregate_counts(rows, field_name, allowed_options):
    """Aggregates single-select option counts dynamically."""
    counts = {opt: 0 for opt in allowed_options}
    for r in rows:
        val = r[field_name]
        if val in counts:
            counts[val] += 1
        elif val:
            counts[val] = counts.get(val, 0) + 1
    return list(counts.keys()), list(counts.values())

def aggregate_multiselect(rows, field_name, allowed_options, total_count):
    """Aggregates multi-select options as independent counts and percentages."""
    counts = {opt: 0 for opt in allowed_options}
    for r in rows:
        try:
            items = json.loads(r[field_name]) if r[field_name] else []
        except (json.JSONDecodeError, TypeError):
            items = [x.strip() for x in str(r[field_name]).split(',') if x.strip()]
        for item in items:
            if item in counts:
                counts[item] += 1
            elif item:
                counts[item] = counts.get(item, 0) + 1

    labels = list(counts.keys())
    raw_counts = list(counts.values())
    percentages = [round((c / total_count * 100), 1) if total_count > 0 else 0 for c in raw_counts]
    return labels, raw_counts, percentages

@app.route('/survey/results')
def survey_results():
    db = get_db()
    rows = db.execute("SELECT * FROM survey_responses ORDER BY id ASC").fetchall()
    total_responses = len(rows)

    if total_responses == 0:
        return render_template(
            'survey_results.html',
            active_page='survey_results',
            total_responses=0,
            dynamic_findings=[],
            survey_analytics={},
            qualitative_responses=[]
        )

    # Q1. Household size
    q1_labels, q1_counts = aggregate_counts(rows, 'household_size', ALLOWED_SURVEY_VALUES['household_size'])
    # Q2. Food manager
    q2_labels, q2_counts = aggregate_counts(rows, 'food_manager', ALLOWED_SURVEY_VALUES['food_manager'])
    # Q3. Waste frequency
    q3_labels, q3_counts = aggregate_counts(rows, 'waste_frequency', ALLOWED_SURVEY_VALUES['waste_frequency'])
    # Q4. Weekly amount
    q4_labels, q4_counts = aggregate_counts(rows, 'weekly_waste_amount', ALLOWED_SURVEY_VALUES['weekly_waste_amount'])
    # Q5. Common category
    q5_labels, q5_counts = aggregate_counts(rows, 'common_waste_category', ALLOWED_SURVEY_VALUES['common_waste_category'])
    # Q6. Reasons (Multi)
    q6_labels, q6_counts, q6_percentages = aggregate_multiselect(rows, 'waste_reasons', ALLOWED_SURVEY_VALUES['waste_reasons'], total_responses)
    # Q7. Expiry checking
    q7_labels, q7_counts = aggregate_counts(rows, 'check_expiry_freq', ALLOWED_SURVEY_VALUES['check_expiry_freq'])
    # Q8. Meal planning
    q8_labels, q8_counts = aggregate_counts(rows, 'meal_planning_freq', ALLOWED_SURVEY_VALUES['meal_planning_freq'])
    # Q9. Leftover practice
    q9_labels, q9_counts = aggregate_counts(rows, 'leftover_practice', ALLOWED_SURVEY_VALUES['leftover_practice'])
    # Q10. Storage location
    q10_labels, q10_counts = aggregate_counts(rows, 'storage_location', ALLOWED_SURVEY_VALUES['storage_location'])
    # Q11. Impact awareness
    q11_labels, q11_counts = aggregate_counts(rows, 'impact_awareness', ALLOWED_SURVEY_VALUES['impact_awareness'])
    # Q12. Current practices (Multi)
    q12_labels, q12_counts, q12_percentages = aggregate_multiselect(rows, 'current_practices', ALLOWED_SURVEY_VALUES['current_practices'], total_responses)
    # Q13. Digital tool interest
    q13_labels, q13_counts = aggregate_counts(rows, 'digital_tool_interest', ALLOWED_SURVEY_VALUES['digital_tool_interest'])
    # Q14. Useful features (Multi)
    q14_labels, q14_counts, q14_percentages = aggregate_multiselect(rows, 'useful_features', ALLOWED_SURVEY_VALUES['useful_features'], total_responses)
    # Q15. Priority problem
    q15_labels, q15_counts = aggregate_counts(rows, 'biggest_problem_to_solve', ALLOWED_SURVEY_VALUES['biggest_problem_to_solve'])

    # Dynamic Survey Interpretations (Strict adherence to actual survey data)
    dynamic_findings = []

    # 1. Top wasted category
    max_cat_idx = q5_counts.index(max(q5_counts)) if q5_counts and max(q5_counts) > 0 else -1
    if max_cat_idx != -1:
        top_cat = q5_labels[max_cat_idx]
        top_cat_pct = round((q5_counts[max_cat_idx] / total_responses * 100), 1)
        dynamic_findings.append(f"Among the {total_responses} surveyed households, the most commonly reported food-waste category was '{top_cat}' ({top_cat_pct}% of respondents).")

    # 2. Top reason
    max_reason_idx = q6_counts.index(max(q6_counts)) if q6_counts and max(q6_counts) > 0 else -1
    if max_reason_idx != -1:
        top_reason = q6_labels[max_reason_idx]
        top_reason_pct = q6_percentages[max_reason_idx]
        dynamic_findings.append(f"The most frequently cited reason for household food wastage was '{top_reason}' (reported by {top_reason_pct}% of households).")

    # 3. Expiry check regularity
    always_often_expiry = sum(r['check_expiry_freq'] in ['Always', 'Often'] for r in rows)
    expiry_check_pct = round((always_often_expiry / total_responses * 100), 1)
    dynamic_findings.append(f"{expiry_check_pct}% of respondents report checking food expiry dates regularly (Always or Often).")

    # 4. Digital tool readiness
    yes_digital = sum(r['digital_tool_interest'] == 'Yes' for r in rows)
    digital_interest_pct = round((yes_digital / total_responses * 100), 1)
    dynamic_findings.append(f"{digital_interest_pct}% of surveyed households explicitly expressed willingness to use a digital tool to reduce household food waste.")

    # 5. Top feature demand
    max_feat_idx = q14_counts.index(max(q14_counts)) if q14_counts and max(q14_counts) > 0 else -1
    if max_feat_idx != -1:
        top_feat = q14_labels[max_feat_idx]
        top_feat_pct = q14_percentages[max_feat_idx]
        dynamic_findings.append(f"The most demanded digital intervention feature is '{top_feat}' (desired by {top_feat_pct}% of respondents).")

    survey_analytics = {
        'q1_labels': q1_labels, 'q1_counts': q1_counts,
        'q2_labels': q2_labels, 'q2_counts': q2_counts,
        'q3_labels': q3_labels, 'q3_counts': q3_counts,
        'q4_labels': q4_labels, 'q4_counts': q4_counts,
        'q5_labels': q5_labels, 'q5_counts': q5_counts,
        'q6_labels': q6_labels, 'q6_percentages': q6_percentages,
        'q7_labels': q7_labels, 'q7_counts': q7_counts,
        'q8_labels': q8_labels, 'q8_counts': q8_counts,
        'q9_labels': q9_labels, 'q9_counts': q9_counts,
        'q10_labels': q10_labels, 'q10_counts': q10_counts,
        'q11_labels': q11_labels, 'q11_counts': q11_counts,
        'q12_labels': q12_labels, 'q12_percentages': q12_percentages,
        'q13_labels': q13_labels, 'q13_counts': q13_counts,
        'q14_labels': q14_labels, 'q14_percentages': q14_percentages,
        'q15_labels': q15_labels, 'q15_counts': q15_counts,
    }

    qualitative_responses = [
        {'biggest_challenge': r['biggest_challenge'], 'improvement_suggestions': r['improvement_suggestions']}
        for r in rows
    ]

    return render_template(
        'survey_results.html',
        active_page='survey_results',
        total_responses=total_responses,
        dynamic_findings=dynamic_findings,
        survey_analytics=survey_analytics,
        qualitative_responses=qualitative_responses
    )


# ==============================================================================
# 10. Awareness & Tips Page
# ==============================================================================
@app.route('/awareness')
def awareness():
    return render_template('awareness.html', active_page='awareness')


# ==============================================================================
# 11. Community Impact & CEP Report Page
# ==============================================================================
@app.route('/community-impact')
def community_impact():
    db = get_db()
    rows = db.execute("SELECT * FROM survey_responses").fetchall()
    total_survey_responses = len(rows)

    dynamic_findings = []
    if total_survey_responses > 0:
        yes_digital = sum(r['digital_tool_interest'] == 'Yes' for r in rows)
        digital_interest_pct = round((yes_digital / total_survey_responses * 100), 1)
        dynamic_findings.append(f"{digital_interest_pct}% of households surveyed indicated interest in digital tracking tools.")
        
        always_often_expiry = sum(r['check_expiry_freq'] in ['Always', 'Often'] for r in rows)
        expiry_check_pct = round((always_often_expiry / total_survey_responses * 100), 1)
        dynamic_findings.append(f"{expiry_check_pct}% regularly check food expiry dates.")

    return render_template(
        'community_impact.html',
        active_page='community_impact',
        total_survey_responses=total_survey_responses,
        dynamic_findings=dynamic_findings
    )


# ==============================================================================
# 12. About Project Page
# ==============================================================================
@app.route('/about')
def about():
    return render_template('about.html', active_page='about')


# ==============================================================================
# 13. Error Handlers
# ==============================================================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', active_page=''), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', active_page=''), 500


# ==============================================================================
# Main Entrypoint
# ==============================================================================
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
