from flask import Flask, send_from_directory, render_template, jsonify, request
from flask_cors import CORS
import os
from config.db import create_properties_table

def create_app():
    app = Flask(__name__, static_folder='static')
    CORS(app)
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Create static images directory if it doesn't exist
    static_images_dir = os.path.join(os.path.dirname(__file__), 'static', 'images')
    if not os.path.exists(static_images_dir):
        os.makedirs(static_images_dir)
    
    # Ensure static map directory exists
    maps_dir = os.path.join(static_images_dir, 'maps')
    if not os.path.exists(maps_dir):
        os.makedirs(maps_dir)
    
    # Create simple routes instead of using blueprints
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/listings')
    def listings():
        return render_template('listings.html')
    
    @app.route('/api/properties')
    def get_properties():
        import psycopg2
        from config.db import DB_PARAMS
        
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cursor = conn.cursor()
            
            # Execute query to fetch all properties
            cursor.execute("SELECT * FROM properties")
            
            # Fetch all rows and convert to list of dictionaries
            columns = [desc[0] for desc in cursor.description]
            properties = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return jsonify(properties)
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(app.static_folder, filename)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000) 