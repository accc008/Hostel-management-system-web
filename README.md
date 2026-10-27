# 🏨 Hostel Management System (HMS)

> A modern, multi-role web platform for comprehensive student accommodation, automated room allotment, canteen food ordering, staff payroll, and student grievance tracking.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20Supabase%20PostgreSQL-green.svg)](https://supabase.com/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel%20Serverless-white.svg)](https://vercel.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 🌟 Executive Summary

The **Hostel Management System (HMS)** is a full-stack, enterprise-grade educational web application designed to eliminate paper-based hostel administration. It unites four distinct user archetypes into a single unified platform:

1. **Hostel Owner / Trustee**: Executive financial oversight, hostel occupancy tracking, staff payroll aggregation, and confidential communications with management.
2. **Operations Managers / Wardens**: Day-to-day administrative operations, student registration, room category configuration, food menu management, staff records, complaint resolution, and admission applications.
3. **Resident Students**: Self-service portal for room allocation, digital canteen meal ordering, billing and dues calculation (in Indian Rupees ₹), and direct complaint lodging.
4. **Prospective Applicants & Public**: Public-facing portal to view hostel amenities, submit admission requests, and apply for employment vacancies.

---

## 🏗️ Architectural Highlights

- **Dual-Mode Database Engine (`db.py`)**: Seamlessly operates in zero-configuration local mode (SQLite) or production cloud mode (Supabase PostgreSQL) via environment variable autodetection (`DATABASE_URL`).
- **Serverless-Ready on Vercel**: Fully configured with `vercel.json` and `api/index.py` using `@vercel/python` serverless WSGI runtime.
- **Stateless Secure Sessions**: Browser-stored encrypted cookie sessions (`Flask session`) eliminating serverless memory concurrency leaks.
- **Pre-Seeded Real-World Dataset**: Populated with 1 Owner, 2 Managers, 16 Resident Students, 4 Room tiers, 10 Indian Canteen items, and 5 Staff Workers. All currency formatted in Indian Rupees (₹).

---

## 🔑 Pre-Seeded Accounts & Demo Credentials

All accounts are pre-configured and ready to explore in `users_credentials.json`:

### 👑 Owner & Trustee
| Name | Email Address | Password / PIN | Role / Access Level |
| :--- | :--- | :--- | :--- |
| **Rajesh Sharma** | `rajesh.sharma@hostel.in` | `12345` | Complete Financial & Operational Oversight |

### 🛡️ Operations Managers
| Name | Email Address | Password / PIN | Role / Access Level |
| :--- | :--- | :--- | :--- |
| **Vikram Patel** | `vikram.patel@hostel.in` | `1111` | Chief Operations Manager |
| **Priya Nair** | `priya.nair@hostel.in` | `2222` | Warden & Resident Welfare Manager |

### 🎓 Resident Students (Sample 8 of 16)
| Name | Email Address | Password / PIN | Room Allotted | Expenditures |
| :--- | :--- | :--- | :--- | :--- |
| **Aarav Mehta** | `aarav.mehta@student.in` | `1001` | Room 101 (Single Deluxe) | ₹12,000 |
| **Ananya Gupta** | `ananya.gupta@student.in` | `1002` | Room 102 (Single Deluxe) | ₹12,450 |
| **Rohan Verma** | `rohan.verma@student.in` | `1003` | Room 201 (Double Sharing) | ₹8,200 |
| **Sneha Iyer** | `sneha.iyer@student.in` | `1004` | Room 201 (Double Sharing) | ₹8,150 |
| **Aditya Sharma** | `aditya.sharma@student.in` | `1005` | Room 202 (Double Sharing) | ₹8,350 |
| **Pooja Nair** | `pooja.nair@student.in` | `1006` | Room 202 (Double Sharing) | ₹8,000 |
| **Ishaan Joshi** | `ishaan.joshi@student.in` | `1007` | Room 301 (Triple Sharing) | ₹5,850 |
| **Siddharth Malhotra** | `siddharth.m@student.in` | `1011` | Room 401 (Four Sharing) | ₹4,250 |

*(For the complete list of all 16 resident accounts, open [`users_credentials.json`](users_credentials.json)).*

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.8 or higher installed (`python --version`)
- Git installed (`git --version`)

### 2. Run the Application
```bash
# Clone or navigate to the repository
cd Hostel-Web-Demo

# Install dependencies
pip install -r requirements.txt

# Start the local development server
python app.py
```

### 3. Open in Browser
Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** to explore all portals.

---

## ☁️ Deploying to Vercel with Supabase (Production)

### Step 1: Push Repository to GitHub
```bash
git add .
git commit -m "feat: production-ready Vercel and Supabase configuration"
git push origin main
```

### Step 2: Deploy on Vercel
1. Log in to [vercel.com](https://vercel.com) and click **"Add New Project"**.
2. Select your `Hostel-Web` GitHub repository.
3. Vercel will automatically detect `vercel.json` and `@vercel/python`.
4. Click **Deploy**.

### Step 3: Configure Supabase PostgreSQL (Mandatory for Vercel Production)
Production deployment on Vercel requires authoritative persistent cloud PostgreSQL to ensure data is permanently preserved across serverless cold starts. Silent fallback to ephemeral `/tmp/hostel.db` is strictly disabled.
1. Create a free project at [supabase.com](https://supabase.com).
2. Go to **Project Settings** -> **Database** and copy your **Connection String (URI)**:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```
3. In your Vercel Project Dashboard:
   - Navigate to **Settings** -> **Environment Variables**.
   - Add Key: `DATABASE_URL`
   - Add Value: `postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres`
4. Deploy or Redeploy in Vercel.
5. The application will connect to Supabase, create all relational tables, and idempotently seed the Indian dataset with hashed credentials on first startup!

---

## 🧪 Automated Testing Suite

The repository includes a comprehensive `pytest` test suite covering registration, public applications, atomic room allocations, food ordering, and auth security guards:

```bash
# Run the complete automated test suite
python -m pytest tests/test_hostel.py -v
```

All 8 tests execute against isolated temporary test fixtures:
- **Test A**: Manager resident registration and immediate resident login.
- **Test B**: Public residence application, manager review, and transactional account creation.
- **Test C**: Atomic room allocation with capacity limits and rollback protection.
- **Test D**: Atomic food ordering with inventory stock validation and rollback protection.
- **Test E**: Role-based authentication guards and session isolation.
- **Test F**: Werkzeug password hashing and automatic legacy plain-text password upgrade.
- **Test G**: Idempotent seeding preserving user modifications.
- **Test H**: Production database failure mode (Vercel without DATABASE_URL raises RuntimeError).

---

## 📁 Repository Structure

```text
├── api/
│   └── index.py               # Vercel Serverless Function entry point
├── data/
│   ├── data.txt               # Flat-file backup: Residents
│   ├── dataManager.txt        # Flat-file backup: Managers
│   ├── dataOwner.txt          # Flat-file backup: Owner
│   ├── rooms.txt              # Flat-file backup: Room inventory
│   ├── foods.txt              # Flat-file backup: Canteen food menu
│   ├── workers.txt            # Flat-file backup: Staff & salaries
│   ├── messages.txt           # Flat-file backup: Owner-Manager messages
│   ├── complains.txt          # Flat-file backup: Resident grievances
│   └── hostel.db              # Auto-generated local SQLite database
├── static/
│   ├── css/                   # SB Admin 2 custom stylesheets
│   ├── js/                    # Form validation and dynamic DOM scripts
│   └── vendor/                # Bootstrap 4, FontAwesome 5, DataTables
├── templates/                 # Jinja2 server-rendered views
│   ├── mainLoginPage.html     # Multi-role landing portal
│   ├── people.html            # Public amenities showcase
│   ├── ApplyJob.html          # Employment application form
│   ├── ResidenceApply.html    # Admission application form
│   ├── Owner/                 # Executive dashboard & analytics
│   ├── Manager/               # Administrative operations & CRUD
│   └── Resident/              # Student room, food, & billing portal
├── app.py                     # Core Flask web server & route controllers
├── db.py                      # Dual-mode Database Engine (PostgreSQL / SQLite)
├── schema.sql                 # Pure SQL schema definition for Supabase
├── users_credentials.json     # Machine-readable demo credentials catalog
├── vercel.json                # Vercel serverless routing & build specifications
├── requirements.txt           # Production Python dependencies
├── ARCHITECTURE.md            # In-depth OOP architecture & design patterns
├── DATABASE.md                # Relational schema & entity-relationship spec
└── VIVA_PRESENTATION_GUIDE.md # College viva exam & viva evaluation guide
```

---

## 📜 Academic Integrity & Attribution
This project was originally conceived as an academic term project for Object Oriented Programming (CS 142) by Tajammal Maqbool at the University of Engineering & Technology (UET), Lahore. It has been refactored, modernized with dual-mode cloud database capabilities, serverless Vercel runtime adaptation, and an authentic Indian dataset. UI components powered by Start Bootstrap (SB Admin 2 - MIT License).
