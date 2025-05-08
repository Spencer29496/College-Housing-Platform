"""
Database initialization script to create all required tables
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# Database connection parameters for development
DEV_DB_PARAMS = {
    'host': os.environ.get('POSTGRES_HOST', 'host.docker.internal'),  # Use environment variable or fallback
    'database': 'postgres',  # Default database
    'user': os.environ.get('POSTGRES_USER', 'postgres'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'team13')  # Use environment variable or fallback
}

# Database connection parameters for production (Docker)
PROD_DB_PARAMS = {
    'host': 'database',
    'database': 'test_db',
    'user': 'postgres',
    'password': 'team13'
}

# Choose parameters based on environment
DB_PARAMS = DEV_DB_PARAMS if os.environ.get('FLASK_ENV') != 'production' else PROD_DB_PARAMS

def init_db():
    """Initialize the database with required tables"""
    conn = None
    cur = None
    try:
        # Create the database if it doesn't exist (for development)
        if DB_PARAMS['host'] == 'host.docker.internal' or DB_PARAMS['host'] == 'localhost':
            temp_conn = psycopg2.connect(
                host=DB_PARAMS['host'],
                database='postgres',
                user=DB_PARAMS['user'],
                password=DB_PARAMS['password']
            )
            temp_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            temp_cur = temp_conn.cursor()
            
            # Check if the database exists
            temp_cur.execute("SELECT 1 FROM pg_database WHERE datname = 'test_db'")
            exists = temp_cur.fetchone()
            
            if not exists:
                temp_cur.execute('CREATE DATABASE test_db')
                print("Database 'test_db' created successfully")
            
            temp_cur.close()
            temp_conn.close()
        
        # Connect to the database
        conn_params = dict(DB_PARAMS)
        if DB_PARAMS['host'] == 'host.docker.internal' or DB_PARAMS['host'] == 'localhost':
            conn_params['database'] = 'test_db'
            
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Create properties table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS properties (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            price TEXT,
            location TEXT,
            url TEXT NOT NULL UNIQUE,
            bedrooms INTEGER,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create student table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS student (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            major VARCHAR(100),
            gpa DECIMAL(3,2),
            enrollment_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create users table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')
        
        # Create students table for the student login system
        cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            student_id VARCHAR(50) UNIQUE NOT NULL,
            year INTEGER NOT NULL,
            major VARCHAR(100),
            is_verified BOOLEAN DEFAULT FALSE,
            verification_token VARCHAR(100),
            verification_token_expires TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')
        
        # Create saved_listings table to store properties saved by students
        cur.execute('''
        CREATE TABLE IF NOT EXISTS saved_listings (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            property_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
            UNIQUE (student_id, property_id)
        )
        ''')
        
        print("All tables created successfully")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db() 