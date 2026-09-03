# Digital Food Waste Reduction and Awareness System for Households

**B.Sc. Computer Science &bull; Community Engagement Project (CEP)**

---

## 1. Project Overview

* **Project Title:** Digital Food Waste Reduction and Awareness System for Households
* **Project Topic:** Food Waste Reduction in Households
* **Project Purpose:** To study household food-waste practices among local families, identify primary drivers of preventable kitchen food waste, foster community awareness regarding responsible food management (FIFO, proper storage hygiene, portioning), and provide a practical digital application for inventory tracking, expiry monitoring, meal scheduling, leftover repurposing, and research analytics.

---

## 2. Key Features

1. **Dynamic Dashboard:**
   * Live count of total items, urgent expiry alerts (1–3 days), active leftovers, and discard incidents.
   * Real-time Chart.js visualizations for discards by category, wastage reasons, and monthly estimated loss.
   * Clean empty-state messaging when no records have been added yet.

2. **Food Inventory Management:**
   * Full CRUD (Add, Edit, Delete, View) with parameterized SQL safety.
   * Real-time expiry timeline calculation relative to current date.
   * Multi-criteria live search, category filter, storage filter, and sorting.

3. **Expiry Tracker & Alerts:**
   * Categorization into `Fresh`, `Expiring Soon (1–3 days)`, `Expiring Today`, and `Expired`.
   * One-click action shortcuts to incorporate expiring items into meal plans or log expired goods into waste records.

4. **Weekly Meal Planner:**
   * Plan Breakfast, Lunch, Dinner, and Snacks across days of the week.
   * Algorithmic suggestions prioritizing active inventory items nearing their expiry dates.

5. **Leftover Management:**
   * Track cooked leftovers with target consume-before horizons.
   * Contextual culinary reuse ideas (e.g. fried rice, croutons, soup bases, missi roti).
   * Clear food safety advisory banners reminding users to inspect sensory freshness.

6. **Waste Tracking & Valuation:**
   * Quantify discarded items, units, categories, and reasons (overcooking, spoilage, expiry, excess).
   * Calculates total estimated weight (kg) and monetary loss (₹) dynamically.

7. **Official CEP Survey Module (17 Questions):**
   * Designed specifically for the 17-question Google Form distributed to 10–20 real households.
   * Manual data entry form with full input validation and JSON serialization for multi-select options.
   * Batch CSV import engine with column verification and error reporting.

8. **Live Survey Analytics & Dynamic Interpretations:**
   * 100% dynamic calculations for all single-choice and multi-select questions.
   * Automatically generated statistical text statements (e.g. *"Among the X surveyed households..."*).
   * Interactive Chart.js charts (Doughnut, Horizontal Bar, Line).

9. **Awareness & CEP Impact Pages:**
   * 10 structured, actionable food preservation guidelines.
   * Full CEP academic documentation including baseline findings and post-intervention evaluation frameworks.

---

## 3. Technology Stack

* **Backend:** Python 3.10+ &bull; Flask 3.0+ &bull; Werkzeug
* **Database:** SQLite3 (parameterized queries, relational tables)
* **Frontend:** HTML5 &bull; CSS3 &bull; JavaScript (ES6+) &bull; Bootstrap 5.3 &bull; Bootstrap Icons &bull; Chart.js v4

---

## 4. Project Structure

```
c:/yash/cep_project/
├── app.py                      # Core Flask application, route handlers, DB aggregations
├── schema.sql                  # SQLite DDL database schema
├── requirements.txt            # Python dependencies
├── README.md                   # Complete CEP documentation and guide
│
├── templates/
│   ├── base.html               # Master layout with navbar, alerts, footer
│   ├── index.html              # Home landing page with hero, features & tips
│   ├── dashboard.html          # Dynamic dashboard metrics and charts
│   ├── inventory.html          # Food inventory CRUD and live filters
│   ├── expiry_tracker.html     # Dedicated expiry timeline board
│   ├── meal_planner.html       # Weekly meal planner with dynamic suggestions
│   ├── leftovers.html          # Leftovers tracker with culinary reuse ideas
│   ├── waste_tracking.html     # Waste logger and loss valuation
│   ├── awareness.html          # 10 food-waste reduction guidelines
│   ├── survey_data.html        # Team survey entry form & CSV importer
│   ├── survey_results.html     # Dynamic survey analytics and text findings
│   ├── community_impact.html   # CEP documentation & methodology
│   ├── about.html              # Academic CEP details and scope
│   ├── 404.html                # Custom error page
│   └── partials/
│       └── expiry_table.html   # Reusable expiry table component
│
└── static/
    ├── css/
    │   └── style.css           # Eco-Modern custom styling
    └── js/
        └── script.js           # Client-side filtering and Chart.js helpers
```

---

## 5. Installation & Setup Guide (Windows / VS Code)

### Step 1: Open the Project in VS Code
Open VS Code and navigate to `c:\yash\cep_project`.

### Step 2: Create a Python Virtual Environment
Open a terminal (PowerShell or Command Prompt) in VS Code:
```powershell
python -m venv venv
```

### Step 3: Activate the Virtual Environment
```powershell
# In PowerShell:
.\venv\Scripts\Activate.ps1

# Or in Command Prompt (cmd):
.\venv\Scripts\activate.bat
```

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Run the Flask Application
```powershell
python app.py
```

### Step 6: Access the Web Application
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```
*(The SQLite database `database.db` is initialized automatically from `schema.sql` on the first run).*

---

## 6. Official Survey Collection & Data Entry Workflow

1. **Google Form Distribution:** The project team circulates the 17-question Google Form to 10–20 real households.
2. **Manual Entry:** Navigate to **CEP Research &rarr; Survey Data Entry & Import** (`/survey/data`) and fill in each submitted response.
3. **CSV Import:** Alternatively, download responses from Google Sheets as a `.csv` file, verify header names using the downloadable template, and upload via the CSV Import tab.
4. **View Live Analytics:** Navigate to **CEP Research &rarr; Survey Results & Analysis** (`/survey/results`) to view real-time charts, percentage breakdowns, and automatically generated text findings.

---

## 7. Data Integrity & Ethical Standards

* **Zero Fake Data:** No synthetic survey responses or invented statistics are seeded in the database.
* **Informative Empty States:** When no food items or survey responses exist, all modules render clean empty-state banners.
* **Anonymous Collection:** No personally identifiable information (PII) is stored.
* **Responsible Food Safety Claims:** The system compares dates relative to user-entered consume-before values and encourages visual/olfactory hygiene checks.

---

## 8. Academic Scope & Limitations

* **Sample Group:** Tailored for an exploratory study sample of 10–20 local households.
* **Estimations:** Discarded weights and monetary losses represent self-reported household figures.
* **Future Scope:** Potential integration with barcode/receipt scanning, automated mobile push reminders, and neighborhood surplus donation portals.
