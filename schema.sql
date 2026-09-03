-- Schema for Digital Food Waste Reduction and Awareness System for Households (CEP)

DROP TABLE IF EXISTS food_items;
DROP TABLE IF EXISTS meal_plans;
DROP TABLE IF EXISTS leftovers;
DROP TABLE IF EXISTS waste_records;
DROP TABLE IF EXISTS survey_responses;
DROP TABLE IF EXISTS post_intervention_evaluations;

-- Food Inventory Table
CREATE TABLE food_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit TEXT NOT NULL,
    purchase_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    storage_type TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Meal Planner Table
CREATE TABLE meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_name TEXT NOT NULL,
    ingredients TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    meal_date TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leftovers Management Table
CREATE TABLE leftovers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_name TEXT NOT NULL,
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit TEXT NOT NULL,
    date_prepared TEXT NOT NULL,
    storage_method TEXT NOT NULL,
    consume_before TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Waste Tracking Table
CREATE TABLE waste_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_item TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity_wasted REAL NOT NULL CHECK(quantity_wasted > 0),
    unit TEXT NOT NULL,
    waste_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    estimated_value REAL NOT NULL DEFAULT 0.0 CHECK(estimated_value >= 0),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Community Survey Responses Table (17 Questions from official Google Form)
CREATE TABLE survey_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_timestamp TEXT,
    household_size TEXT NOT NULL,
    food_manager TEXT NOT NULL,
    waste_frequency TEXT NOT NULL,
    weekly_waste_amount TEXT NOT NULL,
    common_waste_category TEXT NOT NULL,
    waste_reasons TEXT NOT NULL, -- JSON array of selected reasons
    check_expiry_freq TEXT NOT NULL,
    meal_planning_freq TEXT NOT NULL,
    leftover_practice TEXT NOT NULL,
    storage_location TEXT NOT NULL,
    impact_awareness TEXT NOT NULL,
    current_practices TEXT NOT NULL, -- JSON array of reduction practices
    digital_tool_interest TEXT NOT NULL,
    useful_features TEXT NOT NULL, -- JSON array of preferred features
    biggest_problem_to_solve TEXT NOT NULL,
    biggest_challenge TEXT NOT NULL,
    improvement_suggestions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional Post-Intervention Table (Strict Data Integrity: remains empty until real post-intervention data is entered)
CREATE TABLE post_intervention_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_identifier TEXT NOT NULL,
    waste_reduced_percentage REAL,
    reported_habits_improved TEXT,
    feedback_notes TEXT,
    evaluation_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
