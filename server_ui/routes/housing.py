"""
# Housing Routes
# This file defines:
# - Routes for housing-related pages
# - Logic for rendering housing templates
"""

from flask import Blueprint, render_template, request, current_app, jsonify
import psycopg2
import psycopg2.extras
import os

housing_bp = Blueprint('housing', __name__)

# Database configuration - direct connection
DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'database'),
    'database': os.environ.get('POSTGRES_DB', 'test_db'),
    'user': os.environ.get('POSTGRES_USER', 'postgres'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'team13')
}

@housing_bp.route('/', methods=['GET'])
def home_page():
    """Render the home page"""
    return render_template('housing/home.html')

@housing_bp.route('/listings', methods=['GET'])
def listings_page():
    """Render the main listings page"""
    return render_template('housing/listings.html')

@housing_bp.route('/listings/<string:bedrooms>', methods=['GET'])
def filtered_listings_page(bedrooms):
    """Render listings filtered by number of bedrooms"""
    return render_template('housing/listings.html', bedrooms=bedrooms)

@housing_bp.route('/property/<int:property_id>', methods=['GET'])
def property_detail_page(property_id):
    """Render the property detail page"""
    return render_template('housing/property_detail.html', property_id=property_id)

@housing_bp.route('/api/update-map-images', methods=['GET'])
def update_map_images():
    """Utility endpoint to update map images for all properties"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Update all properties with a static map image URL
        map_image_url = "https://raw.githubusercontent.com/username/repo/main/map.png"
        
        # For this example, we'll use a real static map from Google Maps
        cur.execute("""
        UPDATE properties 
        SET map_image = 'https://cdn.prod.website-files.com/6064923dcbc7b0adfe854e06/6064923dcbc7b0f7f2854ee9_Small-white-icon.svg'
        WHERE title LIKE '%Seminary%';
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Map images updated successfully"})
    except Exception as e:
        print(f"Error updating map images: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    """API endpoint to get a specific property by ID"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT * FROM properties WHERE id = %s", (property_id,))
        property = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if property:
            return jsonify(dict(property))
        else:
            return jsonify({"error": "Property not found"}), 404
    except Exception as e:
        print(f"Error in /api/properties/{property_id}: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/listings', methods=['GET'])
def get_listings():
    """API endpoint to get listings data"""
    bedrooms = request.args.get('bedrooms')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    sort = request.args.get('sort', 'id_asc')  # Default sort by ID ascending
    show_with_price_only = request.args.get('with_price_only', 'false').lower() == 'true'
    
    print(f"API Request for listings: bedrooms={bedrooms}, min_price={min_price}, max_price={max_price}, sort={sort}")
    
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Build query based on sort parameter
        sort_clause = "ORDER BY id ASC"  # Default sort
        if sort == 'price_asc':
            sort_clause = "ORDER BY price ASC, id ASC"
        elif sort == 'price_desc':
            sort_clause = "ORDER BY price DESC, id ASC"
        elif sort == 'id_desc':
            sort_clause = "ORDER BY id DESC"
        
        # Start building the query and parameters
        query_conditions = []
        query_params = []
        
        if bedrooms:
            if bedrooms == '4':
                query_conditions.append("bedrooms >= %s")
            else:
                query_conditions.append("bedrooms = %s")
            query_params.append(bedrooms)
        
        # Build base query
        if query_conditions:
            query = f"SELECT * FROM properties WHERE {' AND '.join(query_conditions)} {sort_clause}"
        else:
            query = f"SELECT * FROM properties {sort_clause}"
        
        print(f"Executing query: {query} with params: {query_params}")
        
        cur.execute(query, query_params)
        properties = cur.fetchall()
        
        print(f"Fetched {len(properties)} properties from database")
        
        # Convert to list of dictionaries
        all_properties = []
        for row in properties:
            property_dict = dict(row)
            all_properties.append(property_dict)
        
        # If price filters are set but all properties have "No price",
        # return a special flag to inform the frontend
        if (min_price or max_price) and all(prop['price'] == 'No price' or not prop['price'] or prop['price'] == 'Contact for price' for prop in all_properties):
            cur.close()
            conn.close()
            
            # Return a special response with the listings but also a flag
            print("All properties have 'No price'")
            return jsonify({
                "all_no_price": True,
                "message": "All properties have no price information. Price filters cannot be applied.",
                "properties": all_properties
            })
            
        # Apply price filters in Python
        # This is needed because price is stored as TEXT in the database
        result = []
        for property_dict in all_properties:
            # Skip properties with no price or "No price" if min_price, max_price is set, or if show_with_price_only is true
            if ((min_price or max_price or show_with_price_only) and 
                (not property_dict['price'] or property_dict['price'] == 'No price' or property_dict['price'] == 'Contact for price')):
                continue
                
            # Extract numeric value from price for filtering
            # Example: Convert "$1,200" to 1200 for comparison
            if property_dict['price'] and property_dict['price'] != 'No price' and property_dict['price'] != 'Contact for price':
                # Extract numbers from the price string
                price_value = ''.join(c for c in property_dict['price'] if c.isdigit())
                if price_value:
                    numeric_price = int(price_value)
                    
                    # Apply min_price filter
                    if min_price and numeric_price < int(min_price):
                        continue
                        
                    # Apply max_price filter
                    if max_price and numeric_price > int(max_price):
                        continue
            
            result.append(property_dict)
        
        cur.close()
        conn.close()
        
        print(f"Returning {len(result)} filtered properties")
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Error in /api/listings: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500 