"""
# Main entry point for the Flask server
# This file will:
# - Set up the Flask application
# - Connect to the database
# - Configure middleware
# - Import and use routes
# - Start the server listening on a specified port
""" 
import os
from flask import Flask, jsonify, request, render_template, session, redirect
from flask_cors import CORS
import psycopg2
import psycopg2.extras

try:
    from scraper import main as run_scraper
    SCRAPER_AVAILABLE = True
except ImportError:
    print("Warning: Scraper module not available. Refresh functionality will be disabled.")
    SCRAPER_AVAILABLE = False

from server_ui.students.routes.student_routes import student_bp
from server_ui.students.routes.page_routes import page_bp
from server_ui.routes.housing import housing_bp
# Database connection parameters
hostname = 'database'  # Use the service name from docker-compose.yml
database = 'test_db'
username = 'postgres'
password = 'team13'

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from scraper import main as run_scraper


app = Flask(__name__, template_folder='server_ui/templates',static_folder='server_ui/static')
CORS(app)

# Database connection parameters
DB_CONFIG = {
    'host': hostname,
    'dbname': database,
    'user': username,
    'password': password
}

# Configure session
app.secret_key = 'team13-secret-key'  # Replace with a real secret key in production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = '/flask_session'


def get_db_connection():
    """Create a connection to the database"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


# Add the function to app config for use in blueprints
app.config['get_db_connection'] = get_db_connection

# Register blueprints
app.register_blueprint(student_bp)
app.register_blueprint(page_bp)
app.register_blueprint(housing_bp, url_prefix='/housing')

@app.route('/', methods=['GET'])
def index():
    """Root route - redirects to home page"""
    return redirect('/housing/')

@app.route('/properties', methods=['GET'])
def get_properties():
    """Get all properties or filter by bedrooms"""
    bedrooms = request.args.get('bedrooms')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if bedrooms:
        if bedrooms == '4':
            cur.execute("SELECT * FROM properties WHERE bedrooms >= %s ORDER BY id", (bedrooms,))
        else:
            cur.execute("SELECT * FROM properties WHERE bedrooms = %s ORDER BY id", (bedrooms,))
    else:
        cur.execute("SELECT * FROM properties ORDER BY id")
    
    properties = cur.fetchall()
    cur.close()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for prop in properties:
        result.append(dict(prop))
    
    return jsonify(result)

@app.route('/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    """Get a specific property by ID"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute("SELECT * FROM properties WHERE id = %s", (property_id,))
    property = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if property:
        return jsonify(dict(property))
    else:
        return jsonify({"error": "Property not found"}), 404

@app.route('/refresh', methods=['POST'])
def refresh_data():
    """Trigger a refresh of the property data"""
    if not SCRAPER_AVAILABLE:
        return jsonify({"error": "Scraper module not available"}), 503
        
    try:
        run_scraper()
        return jsonify({"message": "Data refresh completed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.after_request
def add_header(response):
    """Add headers to prevent caching and ensure CORS"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == '__main__':
    # Run the initial scraping if the properties table is empty
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'properties'")
    table_exists = cur.fetchone()[0]
    
    if table_exists:
        cur.execute("SELECT COUNT(*) FROM properties")
        count = cur.fetchone()[0]
        if count == 0:
            cur.close()
            conn.close()
            # Initial scraping if no properties exist
            try:
                run_scraper()
            except Exception as e:
                print(f"Error during initial scraping: {e}")
    
    cur.close()
    conn.close()
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, debug=True) 