"""
# Student Model
# This file defines:
# - Student database schema
# - Methods for student data operations
"""

import psycopg2
import psycopg2.extras
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Student:
    def __init__(self, conn=None):
        self.conn = conn
    
    def set_connection(self, conn):
        self.conn = conn
    
    def create_student(self, name, email, password, year, major, student_id, verification_token=None, verification_token_expires=None):
        """Create a new student record"""
        try:
            cur = self.conn.cursor()
            password_hash = generate_password_hash(password)
            
            query = """
                INSERT INTO students 
                (name, email, password_hash, year, major, student_id, verification_token, verification_token_expires) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            cur.execute(query, (name, email, password_hash, year, major, student_id, verification_token, verification_token_expires))
            student_id = cur.fetchone()[0]
            self.conn.commit()
            cur.close()
            return student_id
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def get_student_by_email(self, email):
        """Get student by email"""
        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM students WHERE email = %s", (email,))
            student = cur.fetchone()
            cur.close()
            return dict(student) if student else None
        except Exception as e:
            raise e
    
    def get_student_by_id(self, student_id):
        """Get student by ID"""
        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM students WHERE id = %s", (student_id,))
            student = cur.fetchone()
            cur.close()
            return dict(student) if student else None
        except Exception as e:
            raise e
    
    def verify_password(self, email, password):
        """Verify student password"""
        student = self.get_student_by_email(email)
        if not student:
            return False
        return check_password_hash(student['password_hash'], password)
    
    def get_all_students(self, filters=None):
        """Get all students with optional filters"""
        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            base_query = "SELECT * FROM students"
            query_parts = []
            params = []
            
            if filters:
                if 'year' in filters and filters['year']:
                    query_parts.append("year = %s")
                    params.append(filters['year'])
                
                if 'major' in filters and filters['major']:
                    query_parts.append("major = %s")
                    params.append(filters['major'])
            
            if query_parts:
                base_query += " WHERE " + " AND ".join(query_parts)
            
            base_query += " ORDER BY name"
            
            cur.execute(base_query, params)
            students = cur.fetchall()
            cur.close()
            
            result = []
            for student in students:
                student_dict = dict(student)
                # Remove sensitive information
                if 'password_hash' in student_dict:
                    del student_dict['password_hash']
                result.append(student_dict)
            
            return result
        except Exception as e:
            raise e
            
    def get_student_by_verification_token(self, token):
        """Get student by verification token"""
        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM students WHERE verification_token = %s", (token,))
            student = cur.fetchone()
            cur.close()
            return dict(student) if student else None
        except Exception as e:
            raise e
    
    def verify_email(self, token):
        """Mark student email as verified using token"""
        try:
            # Get the current timestamp
            now = datetime.datetime.now()
            
            # Get student by token
            student = self.get_student_by_verification_token(token)
            if not student:
                return False, "Invalid verification token"
            
            # Check if token is expired
            if student['verification_token_expires'] < now:
                return False, "Verification token has expired"
            
            # Mark as verified
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE students SET is_verified = TRUE, verification_token = NULL, verification_token_expires = NULL WHERE id = %s",
                (student['id'],)
            )
            self.conn.commit()
            cur.close()
            return True, "Email verified successfully"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def update_verification_token(self, email, token, expiry):
        """Update verification token for a student"""
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE students SET verification_token = %s, verification_token_expires = %s WHERE email = %s",
                (token, expiry, email)
            )
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            self.conn.rollback()
            return False 