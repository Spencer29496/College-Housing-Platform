"""
# Database Configuration
# This file will:
# - Set up database connection
# - Configure connection pool
# - Handle database errors
""" 

import psycopg2
from .configuration import DB_PARAMS

def create_properties_table():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        price TEXT,
        location TEXT,
        url TEXT NOT NULL UNIQUE,
        bedrooms INTEGER,
        image_url TEXT,
        map_image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def truncate_properties_table():
    """Truncate the properties table before starting a new scrape."""
    conn = None # Initialize conn to None
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("Truncating properties table...")
        cur.execute('TRUNCATE TABLE properties RESTART IDENTITY CASCADE;')
        conn.commit()
        print("Properties table truncated.")
    except Exception as e:
        print(f"Error truncating properties table: {e}")
        if conn:
            conn.rollback() # Rollback if error occurs
    finally:
        if conn:
            cur.close()
            conn.close()

def save_to_database(listings):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    for listing in listings:
        try:
            cur.execute('''
            INSERT INTO properties (title, price, location, url, bedrooms, image_url, map_image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE 
            SET title = EXCLUDED.title,
                price = EXCLUDED.price,
                location = EXCLUDED.location,
                bedrooms = EXCLUDED.bedrooms,
                image_url = EXCLUDED.image_url,
                map_image_url = EXCLUDED.map_image_url
            ''', (
                listing['title'],
                listing['price'],
                listing['location'],
                listing['url'],
                listing['bedrooms'],
                listing.get('image_url'),
                listing.get('map_image_url')
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error saving {listing['title']}: {e}")
    cur.close()
    conn.close()

def delete_listing_by_title(title):
    """Delete a listing from the database by its title"""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    try:
        cur.execute('''
        DELETE FROM properties
        WHERE title = %s
        ''', (title,))
        deleted_count = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted_count} listings with title '{title}'")
        return deleted_count
    except Exception as e:
        conn.rollback()
        print(f"Error deleting listing with title '{title}': {e}")
        return 0
    finally:
        cur.close()
        conn.close()
