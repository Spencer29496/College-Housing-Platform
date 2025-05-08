"""
Database seeding script to insert sample data into tables
"""

import psycopg2
from datetime import date, datetime
from werkzeug.security import generate_password_hash

# Database connection parameters
DB_PARAMS = {
    'host': 'database',
    'database': 'test_db',
    'user': 'postgres',
    'password': 'team13'
}

def seed_db():
    """Seed the database with sample data"""
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        
        cur.execute("SELECT COUNT(*) FROM student")
        student_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        
        if student_count == 0:
            # Sample student data
            students = [
                ('Alice Johnson', 'Computer Science', 3.85, date(2023, 9, 1)),
                ('Mike Brown', 'Engineering', 3.92, date(2023, 9, 1)),
                ('Sarah Davis', 'Mathematics', 3.78, date(2023, 9, 1))
            ]
            
            cur.executemany('''
            INSERT INTO student (name, major, gpa, enrollment_date)
            VALUES (%s, %s, %s, %s)
            ''', students)
            print("Student data seeded successfully")
        
        if user_count == 0:
            # Sample user data
            users = [
                ('user1', 'user1@example.com', generate_password_hash('password123')),
                ('user2', 'user2@example.com', generate_password_hash('password456')),
                ('user3', 'user3@example.com', generate_password_hash('password789'))
            ]
            
            cur.executemany('''
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            ''', users)
            print("User data seeded successfully")
        
        conn.commit()
        print("Database seeding completed")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    seed_db() 