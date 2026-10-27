-- ====================================================================
-- Hostel Management System - Complete Database Schema
-- Compatible with PostgreSQL / Supabase and SQLite
-- ====================================================================

-- 1. Owners Table
CREATE TABLE IF NOT EXISTS owners (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    pin VARCHAR(50) NOT NULL
);

-- 2. Managers Table
CREATE TABLE IF NOT EXISTS managers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    pin VARCHAR(50) NOT NULL
);

-- 3. Residents Table
CREATE TABLE IF NOT EXISTS residents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    pin VARCHAR(50) NOT NULL,
    room_no INTEGER DEFAULT 0,
    room_type VARCHAR(100) DEFAULT 'None',
    expenditures NUMERIC(10, 2) DEFAULT 0.00
);

-- 4. Rooms Table
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    type_room VARCHAR(100) UNIQUE NOT NULL,
    price_room NUMERIC(10, 2) NOT NULL,
    total_rooms INTEGER NOT NULL,
    book_rooms INTEGER DEFAULT 0,
    starting_room INTEGER NOT NULL
);

-- 5. Foods / Canteen Menu Table
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    quantity INTEGER NOT NULL
);

-- 6. Staff / Workers Table
CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    job VARCHAR(100) NOT NULL,
    salary NUMERIC(10, 2) NOT NULL
);

-- 7. Messages Table (Owner <-> Manager)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    sender VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Complaints Table (Resident -> Manager)
CREATE TABLE IF NOT EXISTS complaints (
    id SERIAL PRIMARY KEY,
    complain TEXT NOT NULL,
    resident_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Residence Applications Table
CREATE TABLE IF NOT EXISTS residence_requests (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    pin VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Job Applications Table
CREATE TABLE IF NOT EXISTS job_requests (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    job VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Food Orders Table
CREATE TABLE IF NOT EXISTS ordered_foods (
    id SERIAL PRIMARY KEY,
    food_name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    resident_name VARCHAR(100) NOT NULL,
    pin VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
