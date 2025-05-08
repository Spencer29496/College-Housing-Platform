"""
# Housing Routes
# This file defines:
# - Routes for housing-related pages
# - Logic for rendering housing templates
"""

from flask import Blueprint, render_template, request, current_app, jsonify, session
import psycopg2
import psycopg2.extras
import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Import our scraper function
try:
    from scraper import extract_property_details
except ImportError:
    # Alternative import path for Docker environment
    from src.scraper import extract_property_details

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
            property_dict = dict(property)
            
            # Fix price formatting
            if not property_dict['price'] or property_dict['price'] == 'No price' or property_dict['price'] == '$,' or property_dict['price'] == '$':
                property_dict['price'] = 'Contact for price'
            
            # Calculate distance to Binghamton University if location exists
            if property_dict.get('location'):
                try:
                    # Binghamton University coordinates
                    bu_coords = {"lat": 42.0896, "lng": -75.9672}
                    
                    # Use the existing location to calculate an approximate distance
                    # Since we don't have geocoding in place, we'll use a static value if it exists
                    # or calculate a rough estimate based on address patterns
                    
                    # Check if there's already a distance field in the database
                    if property_dict.get('distance'):
                        # Convert to string with miles unit
                        property_dict['distance_to_bu'] = f"{property_dict['distance']} miles"
                    else:
                        # Rough distance estimate based on the location
                        location = property_dict['location'].lower()
                        
                        # Example distance mapping - in a real app this would use geocoding
                        if 'seminary' in location:
                            distance = 0.8
                        elif 'murray' in location:
                            distance = 1.2
                        elif 'leroy' in location:
                            distance = 0.9
                        elif 'front' in location:
                            distance = 0.5
                        elif 'walnut' in location:
                            distance = 1.3
                        elif 'chapin' in location:
                            distance = 1.8
                        elif 'ayres' in location:
                            distance = 1.5
                        else:
                            # Default distance estimate
                            distance = 1.0
                            
                        property_dict['distance_to_bu'] = f"{distance} miles"
                except Exception as e:
                    print(f"Error calculating distance: {e}")
                    property_dict['distance_to_bu'] = "Distance information unavailable"
            else:
                property_dict['distance_to_bu'] = "Location not provided"
            
            # If this is a Binghamton West property, fetch updated details from source
            if property_dict['url'] and 'binghamtonwest.com' in property_dict['url']:
                try:
                    # Use the extract_property_details function to get fresh data
                    updated_details = extract_property_details(property_dict['url'])
                    
                    # If successful, update the property details
                    if updated_details and updated_details.get('success'):
                        # Update bedrooms if available in the fresh data
                        if updated_details.get('bedrooms'):
                            property_dict['bedrooms'] = updated_details['bedrooms']
                            
                        # Update amenities if available
                        if updated_details.get('amenities'):
                            property_dict['amenities'] = updated_details['amenities']
                        
                        # Update description if available
                        if updated_details.get('description'):
                            property_dict['description'] = updated_details['description']
                            
                        # Update price if available
                        if updated_details.get('price'):
                            # Ensure it's not just "$" or "$,"
                            price = updated_details['price']
                            if price and price not in ['$', '$,', 'No price']:
                                property_dict['price'] = price
                            else:
                                property_dict['price'] = 'Contact for price'
                except Exception as e:
                    print(f"Error fetching updated property details: {e}")
                    # Continue with existing data if update fails
            
            return jsonify(property_dict)
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
    max_distance = request.args.get('distance')  # Add support for distance filter
    sort = request.args.get('sort', 'id_asc')  # Default sort by ID ascending
    show_with_price_only = request.args.get('with_price_only', 'false').lower() == 'true'
    include_all = request.args.get('include_all', 'false').lower() == 'true'  # New parameter to optionally include all properties
    
    print(f"API Request for listings: bedrooms={bedrooms}, min_price={min_price}, max_price={max_price}, max_distance={max_distance}, sort={sort}")
    
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
        
        # Add Binghamton West filter unless include_all=true
        if not include_all:
            query_conditions.append("url LIKE %s")
            query_params.append('%binghamtonwest.com%')
        
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
            
            # Fix price formatting
            if not property_dict['price'] or property_dict['price'] == 'No price' or property_dict['price'] == '$,' or property_dict['price'] == '$':
                property_dict['price'] = 'Contact for price'
            
            # Ensure bedrooms is a valid value
            if property_dict['bedrooms'] is None or property_dict['bedrooms'] == '':
                # Try to extract bedrooms from title
                title = property_dict.get('title', '')
                try:
                    # Look for patterns like "2 Bedroom" or "2 BR" or "2-Bedroom" or "Apt 2" or ending with 2
                    import re
                    
                    # First, check for explicit bedroom mentions
                    bedroom_match = re.search(r'(\d+)[\s-]*(bed|br|bedroom)', title.lower())
                    if bedroom_match:
                        property_dict['bedrooms'] = int(bedroom_match.group(1))
                    
                    # If no match, check for "Apt X" pattern
                    elif re.search(r'apt\s+(\d+)', title.lower()):
                        apt_match = re.search(r'apt\s+(\d+)', title.lower())
                        property_dict['bedrooms'] = int(apt_match.group(1))
                    
                    # If still no match, check if property address ends with a number
                    elif re.search(r'\s(\d+)$', title.strip()):
                        end_match = re.search(r'\s(\d+)$', title.strip())
                        property_dict['bedrooms'] = int(end_match.group(1))
                    
                    # Look for apartment number after the suffix like 1L, 2R, etc.
                    elif re.search(r'apt\s+\d+[a-zA-Z]', title.lower()):
                        # Extract the digit part in patterns like "Apt 2L"
                        apt_letter_match = re.search(r'apt\s+(\d+)[a-zA-Z]', title.lower())
                        if apt_letter_match:
                            property_dict['bedrooms'] = int(apt_letter_match.group(1))
                    
                    # Extract from title like "10 Seminary Apt 2"
                    elif "Seminary Apt" in title:
                        seminary_match = re.search(r'Seminary\s+Apt\s+(\d+)', title)
                        if seminary_match:
                            property_dict['bedrooms'] = int(seminary_match.group(1))
                    
                    else:
                        property_dict['bedrooms'] = None
                except Exception as e:
                    print(f"Error extracting bedrooms from title '{title}': {str(e)}")
                    property_dict['bedrooms'] = None
                
            # Ensure distance is set for all properties
            if property_dict.get('distance') is None:
                # Estimate distance based on address patterns if location is available
                if property_dict.get('location'):
                    location = property_dict['location'].lower()
                    # Example distance mapping - in a real app this would use geocoding
                    if 'seminary' in location:
                        property_dict['distance'] = 0.8
                    elif 'murray' in location:
                        property_dict['distance'] = 1.2
                    elif 'leroy' in location:
                        property_dict['distance'] = 0.9
                    elif 'front' in location:
                        property_dict['distance'] = 0.5
                    elif 'walnut' in location:
                        property_dict['distance'] = 1.3
                    elif 'chapin' in location:
                        property_dict['distance'] = 1.8
                    elif 'ayres' in location:
                        property_dict['distance'] = 1.5
                    else:
                        # Default distance estimate
                        property_dict['distance'] = 1.0
                else:
                    # If no location, use a default
                    property_dict['distance'] = 1.5
            
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
            
            # Apply distance filter
            if max_distance and property_dict.get('distance'):
                if float(property_dict['distance']) > float(max_distance):
                    continue
            
            result.append(property_dict)
        
        # Apply sorting
        if sort == 'distance_asc':
            # Sort by distance if available, then by ID
            result.sort(key=lambda p: (float(p.get('distance', 999)), p['id']) if p.get('distance') else (999, p['id']))
        
        cur.close()
        conn.close()
        
        print(f"Returning {len(result)} filtered properties")
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Error in /api/listings: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/diagnose-images', methods=['GET'])
def diagnose_images():
    """Utility endpoint to diagnose image issues"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get all properties with their image URLs
        cur.execute("""
        SELECT id, title, image_url, map_image_url, map_image 
        FROM properties
        """)
        
        properties = cur.fetchall()
        
        # Convert to list of dictionaries
        results = []
        for prop in properties:
            results.append({
                'id': prop['id'],
                'title': prop['title'],
                'image_url': prop['image_url'],
                'map_image_url': prop['map_image_url'],
                'map_image': prop.get('map_image')  # Use get() since this column might not exist
            })
        
        cur.close()
        conn.close()
        
        return jsonify(results)
    except Exception as e:
        print(f"Error diagnosing images: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/fix-map-images', methods=['GET'])
def fix_map_images():
    """Utility endpoint to fix map images for all properties"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get API key parameter, if provided
        api_key = request.args.get('api_key')
        
        # Count of affected rows
        fixed_count = 0
        
        if api_key:
            # Update with a new API key
            cur.execute("""
            UPDATE properties 
            SET map_image_url = REPLACE(map_image_url, 
                'AIzaSyBXQROV5YMCERGIIuwxrmaZbBl_Wm4Dy5U', 
                %s)
            WHERE map_image_url LIKE '%%AIzaSyBXQROV5YMCERGIIuwxrmaZbBl_Wm4Dy5U%%'
            """, [api_key])
            fixed_count = cur.rowcount
            
            # Also update map_image field if it exists
            try:
                cur.execute("""
                UPDATE properties 
                SET map_image = REPLACE(map_image, 
                    'AIzaSyBXQROV5YMCERGIIuwxrmaZbBl_Wm4Dy5U', 
                    %s)
                WHERE map_image LIKE '%%AIzaSyBXQROV5YMCERGIIuwxrmaZbBl_Wm4Dy5U%%'
                """, [api_key])
                fixed_count += cur.rowcount
            except Exception as e:
                print(f"Error updating map_image (might not exist): {str(e)}")
        else:
            # If no API key provided, just clear the map image URLs
            cur.execute("""
            UPDATE properties 
            SET map_image_url = NULL
            WHERE map_image_url LIKE '%%maps.googleapis.com%%'
            """)
            fixed_count = cur.rowcount
            
            # Also update map_image field if it exists
            try:
                cur.execute("""
                UPDATE properties 
                SET map_image = NULL
                WHERE map_image LIKE '%%maps.googleapis.com%%'
                """)
                fixed_count += cur.rowcount
            except Exception as e:
                print(f"Error updating map_image (might not exist): {str(e)}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Map images updated successfully. Fixed {fixed_count} records.",
            "fixed_count": fixed_count
        })
    except Exception as e:
        print(f"Error fixing map images: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/filter-binghamton-west', methods=['GET'])
def filter_binghamton_west():
    """Filter to show only Binghamton West properties and delete others"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # First, check how many properties we have from non-Binghamton West sources
        cur.execute("""
        SELECT COUNT(*) 
        FROM properties 
        WHERE url NOT LIKE '%%binghamtonwest.com%%'
        """)
        non_bw_count = cur.fetchone()[0]
        
        # Delete non-Binghamton West properties if the delete parameter is provided
        deleted_count = 0
        if request.args.get('delete', 'false').lower() == 'true':
            cur.execute("""
            DELETE FROM properties 
            WHERE url NOT LIKE '%%binghamtonwest.com%%'
            """)
            deleted_count = cur.rowcount
            conn.commit()
        
        # Get count of remaining Binghamton West properties
        cur.execute("""
        SELECT COUNT(*) 
        FROM properties 
        WHERE url LIKE '%%binghamtonwest.com%%'
        """)
        bw_count = cur.fetchone()[0]
        
        # Now get listings from Binghamton West only
        cur.execute("""
        SELECT * 
        FROM properties 
        WHERE url LIKE '%%binghamtonwest.com%%'
        ORDER BY id ASC
        """)
        
        properties = cur.fetchall()
        
        # Convert to list of dictionaries
        results = []
        for row in properties:
            property_dict = dict(row)
            results.append(property_dict)
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Found {bw_count} Binghamton West properties, {non_bw_count} other properties found" + 
                      (f", {deleted_count} non-Binghamton West properties deleted" if deleted_count > 0 else ""),
            "binghamton_west_count": bw_count,
            "other_count": non_bw_count,
            "deleted_count": deleted_count,
            "properties": results
        })
    except Exception as e:
        print(f"Error filtering Binghamton West properties: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/analyze-sources', methods=['GET'])
def analyze_sources():
    """Analyze the sources of all properties in the database"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get distinct domains from URLs
        cur.execute("""
        SELECT 
            SUBSTRING(url FROM '(?:https?://)?(?:www\.)?([^/]+)') AS domain,
            COUNT(*) as count
        FROM properties
        GROUP BY domain
        ORDER BY count DESC
        """)
        
        sources = cur.fetchall()
        
        # Convert to list of dictionaries
        results = []
        for row in sources:
            source_dict = dict(row)
            results.append(source_dict)
        
        # Count all properties
        cur.execute("SELECT COUNT(*) FROM properties")
        total_count = cur.fetchone()[0]
        
        # Count properties with binghamtonwest.com in URL
        cur.execute("SELECT COUNT(*) FROM properties WHERE url LIKE '%%binghamtonwest.com%%'")
        bw_count = cur.fetchone()[0]
        
        # Generate a summary of non-Binghamton West properties
        cur.execute("""
        SELECT id, title, url
        FROM properties
        WHERE url NOT LIKE '%%binghamtonwest.com%%'
        ORDER BY id ASC
        """)
        
        other_properties = []
        for row in cur.fetchall():
            other_properties.append(dict(row))
        
        cur.close()
        conn.close()
        
        return jsonify({
            "summary": {
                "total_properties": total_count,
                "binghamton_west_properties": bw_count,
                "other_properties": total_count - bw_count,
                "percentage_binghamton_west": f"{(bw_count / total_count) * 100:.1f}%" if total_count > 0 else "0%"
            },
            "sources": results,
            "non_binghamton_west_properties": other_properties
        })
    except Exception as e:
        print(f"Error analyzing property sources: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/clean-404-images', methods=['GET'])
def clean_404_images():
    """Identify and optionally delete listings with 404 image URLs"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get all property IDs and image URLs
        cur.execute("""
        SELECT id, title, image_url 
        FROM properties
        """)
        
        properties = cur.fetchall()
        
        # Find properties with missing or 404 image URLs
        problematic_properties = []
        for prop in properties:
            if not prop['image_url']:
                problematic_properties.append({
                    'id': prop['id'],
                    'title': prop['title'],
                    'image_url': None,
                    'issue': 'Missing image URL'
                })
                continue
                
            # Check if the image URL is a local path that doesn't exist
            if prop['image_url'].startswith('/static/'):
                local_path = os.path.join(os.path.dirname(__file__), '..', prop['image_url'].lstrip('/'))
                if not os.path.exists(local_path):
                    problematic_properties.append({
                        'id': prop['id'],
                        'title': prop['title'],
                        'image_url': prop['image_url'],
                        'issue': 'Missing local file'
                    })
        
        # Delete problematic properties if requested
        deleted_count = 0
        if request.args.get('delete', 'false').lower() == 'true':
            for prop in problematic_properties:
                cur.execute("DELETE FROM properties WHERE id = %s", (prop['id'],))
                deleted_count += 1
            conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Found {len(problematic_properties)} properties with image issues" + 
                      (f", {deleted_count} properties deleted" if deleted_count > 0 else ""),
            "problematic_properties": problematic_properties,
            "deleted_count": deleted_count
        })
    except Exception as e:
        print(f"Error cleaning 404 images: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/clean-404-urls', methods=['GET'])
def clean_404_urls():
    """Identify and optionally delete listings whose URLs return 404"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get all property IDs and URLs
        cur.execute("""
        SELECT id, title, url 
        FROM properties
        WHERE url LIKE '%%binghamtonwest.com%%'
        """)
        
        properties = cur.fetchall()
        
        # Setup for requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Check each URL for 404 errors
        invalid_properties = []
        for prop in properties:
            try:
                # Skip if URL is empty
                if not prop['url']:
                    continue
                    
                # Ensure URL is properly formatted
                url = prop['url']
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url.lstrip('/')
                
                # Make request with timeout - use GET instead of HEAD to get content
                response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
                
                # Check for 404 indicators in the content
                is_404 = False
                
                # Check HTTP status code
                if response.status_code == 404:
                    is_404 = True
                
                # Check for 404 text patterns in the HTML
                content = response.text.lower()
                if (
                    'error: page not found' in content or 
                    '<h1' in content and '404' in content or
                    "this page isn't available" in content or
                    'data-hook="error-code">404<' in content
                ):
                    is_404 = True
                    
                if is_404:
                    invalid_properties.append({
                        'id': prop['id'],
                        'title': prop['title'],
                        'url': prop['url'],
                        'status_code': response.status_code,
                        'reason': 'Page not found (404)'
                    })
                    print(f"404 URL found: {prop['url']}")
            except Exception as e:
                # Count connection errors as invalid too
                print(f"Error checking URL {prop['url']}: {str(e)}")
                invalid_properties.append({
                    'id': prop['id'],
                    'title': prop['title'],
                    'url': prop['url'],
                    'error': str(e)
                })
        
        # Delete invalid properties if requested
        deleted_count = 0
        if request.args.get('delete', 'false').lower() == 'true':
            for prop in invalid_properties:
                cur.execute("DELETE FROM properties WHERE id = %s", (prop['id'],))
                deleted_count += 1
            conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Found {len(invalid_properties)} properties with 404 URLs" + 
                      (f", {deleted_count} properties deleted" if deleted_count > 0 else ""),
            "invalid_properties": invalid_properties,
            "deleted_count": deleted_count
        })
    except Exception as e:
        print(f"Error cleaning 404 URLs: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/force-clean-bad-listings', methods=['GET'])
def force_clean_bad_listings():
    """Directly remove all listings with placeholder or missing images"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # First, delete any listings missing image_url
        cur.execute("""
        DELETE FROM properties
        WHERE image_url IS NULL OR image_url = ''
        RETURNING id, title
        """)
        missing_images = cur.fetchall()
        missing_image_count = len(missing_images)
        conn.commit()
        
        # Now identify and delete all listings with placeholder images (600x400)
        cur.execute("""
        SELECT id, title, url, image_url
        FROM properties
        WHERE url LIKE '%binghamtonwest.com%'
        AND (
            image_url = '/static/images/placeholder.jpg'
            OR image_url LIKE '%600x400%'
            OR image_url LIKE '%placeholder%'
        )
        """)
        placeholder_listings = [dict(row) for row in cur.fetchall()]
        
        # Delete all the placeholder listings by default
        placeholder_deleted = 0
        for listing in placeholder_listings:
            cur.execute("DELETE FROM properties WHERE id = %s", (listing['id'],))
            placeholder_deleted += 1
        
        conn.commit()
        
        # Let's also check for any invalid image URLs (ones that can't be loaded)
        # First get all remaining listings
        cur.execute("""
        SELECT id, title, url, image_url
        FROM properties
        WHERE url LIKE '%binghamtonwest.com%'
        """)
        
        remaining_listings = cur.fetchall()
        
        # See if there are any more suspect listings left
        suspect_listings = []
        for prop in remaining_listings:
            image_url = prop['image_url']
            if not image_url:
                continue
                
            # Check for patterns that might indicate problematic images
            if any(pattern in image_url.lower() for pattern in [
                'placeholder', 'default', 'no-image', 'noimage',
                'missing', '404', 'error', 'not-found', 'notfound'
            ]):
                suspect_listings.append(dict(prop))
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Cleaned up listings: {missing_image_count} with missing images, {placeholder_deleted} with placeholder images",
            "missing_images": [dict(row) for row in missing_images],
            "placeholder_listings": placeholder_listings,
            "suspect_listings": suspect_listings
        })
    except Exception as e:
        print(f"Error force cleaning listings: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/remove-specific-listings', methods=['GET'])
def remove_specific_listings():
    """Remove specific listings identified in the screenshots"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # List of specific listings to remove (by title/pattern)
        specific_listings = [
            # Listings with generic bedroom photos
            "4 Seminary Apt 3",
            "14 Seminary Apt 1",
            "18 Seminary Apt 1",
            # The one with just "BINGHAMTON WEST" title
            "BINGHAMTON WEST"
        ]
        
        # Track the deleted items
        deleted_items = []
        
        # Delete each specific listing
        for listing_title in specific_listings:
            # First get the details so we can return what was deleted
            cur.execute("""
            SELECT id, title, url 
            FROM properties 
            WHERE title = %s
            """, (listing_title,))
            
            items = cur.fetchall()
            for item in items:
                deleted_items.append(dict(item))
            
            # Then delete it
            cur.execute("""
            DELETE FROM properties 
            WHERE title = %s
            """, (listing_title,))
        
        # Commit the changes
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Successfully removed {len(deleted_items)} specific listings",
            "deleted_listings": deleted_items
        })
    except Exception as e:
        print(f"Error removing specific listings: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500

@housing_bp.route('/api/scrape-listing-details', methods=['GET'])
def scrape_listing_details():
    """API endpoint to scrape details from original listing URLs"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400
    
    try:
        # Use the extract_property_details function from scraper.py
        result = extract_property_details(url)
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"Error scraping listing details from {url}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "url": url
        }), 500

# Saved listings API routes
@housing_bp.route('/api/saved-listings/save', methods=['POST'])
def save_listing():
    """API endpoint to save a property listing for a student"""
    # Check if student is logged in via session
    student_id = session.get('student_id')
    if not student_id:
        print("Error: No student_id in session")
        return jsonify({"error": "You must be logged in to save listings"}), 401
    
    try:
        data = request.get_json()
        if not data or 'property_id' not in data:
            return jsonify({"error": "Property ID is required"}), 400
        
        property_id = data['property_id']
        print(f"Attempting to save property {property_id} for student {student_id}")
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if the property exists
        cur.execute("SELECT id FROM properties WHERE id = %s", (property_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            print(f"Error: Property {property_id} not found")
            return jsonify({"error": "Property not found"}), 404
        
        # Check if already saved (to avoid duplicate entries)
        cur.execute(
            "SELECT id FROM saved_listings WHERE student_id = %s AND property_id = %s",
            (student_id, property_id)
        )
        
        if cur.fetchone():
            # Already saved, return success
            cur.close()
            conn.close()
            print(f"Property {property_id} already saved for student {student_id}")
            return jsonify({"message": "Property already saved"})
        
        # Save the property for this student
        try:
            cur.execute(
                "INSERT INTO saved_listings (student_id, property_id) VALUES (%s, %s)",
                (student_id, property_id)
            )
            conn.commit()
            print(f"Successfully saved property {property_id} for student {student_id}")
        except Exception as db_error:
            conn.rollback()
            print(f"Database error while saving: {str(db_error)}")
            return jsonify({"error": f"Database error: {str(db_error)}"}), 500
        finally:
            cur.close()
            conn.close()
        
        return jsonify({"message": "Property saved successfully"})
    except Exception as e:
        print(f"Error saving listing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@housing_bp.route('/api/saved-listings/unsave', methods=['POST'])
def unsave_listing():
    """API endpoint to unsave a property listing for a student"""
    # Check if student is logged in via session
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({"error": "You must be logged in to manage saved listings"}), 401
    
    try:
        data = request.get_json()
        if not data or 'property_id' not in data:
            return jsonify({"error": "Property ID is required"}), 400
        
        property_id = data['property_id']
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Delete the saved listing
        cur.execute(
            "DELETE FROM saved_listings WHERE student_id = %s AND property_id = %s",
            (student_id, property_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Property removed from saved listings"})
    except Exception as e:
        print(f"Error unsaving listing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@housing_bp.route('/api/saved-listings/check', methods=['GET'])
def check_saved_listing():
    """API endpoint to check if a property is saved for the current student"""
    # Check if student is logged in via session
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({"is_saved": False})
    
    try:
        property_id = request.args.get('property_id')
        if not property_id:
            return jsonify({"error": "Property ID is required"}), 400
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if property is saved
        cur.execute(
            "SELECT id FROM saved_listings WHERE student_id = %s AND property_id = %s",
            (student_id, property_id)
        )
        
        is_saved = cur.fetchone() is not None
        
        cur.close()
        conn.close()
        
        return jsonify({"is_saved": is_saved})
    except Exception as e:
        print(f"Error checking saved listing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@housing_bp.route('/api/saved-listings', methods=['GET'])
def get_saved_listings():
    """API endpoint to get all saved listings for the current student"""
    # Check if student is logged in via session
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({"error": "You must be logged in to view saved listings"}), 401
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get all saved listings for this student with property details
        cur.execute("""
            SELECT p.*, sl.created_at as saved_at
            FROM saved_listings sl
            JOIN properties p ON sl.property_id = p.id
            WHERE sl.student_id = %s
            ORDER BY sl.created_at DESC
        """, (student_id,))
        
        saved_listings = cur.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for row in saved_listings:
            property_dict = dict(row)
            
            # Fix price formatting
            if not property_dict['price'] or property_dict['price'] == 'No price' or property_dict['price'] == '$,' or property_dict['price'] == '$':
                property_dict['price'] = 'Contact for price'
            
            # Process bedrooms field if it's null or empty
            if property_dict['bedrooms'] is None or property_dict['bedrooms'] == '':
                # Try to extract bedrooms from title
                title = property_dict.get('title', '')
                try:
                    # Look for patterns like "2 Bedroom" or "2 BR" or "2-Bedroom" or "Apt 2" or ending with 2
                    import re
                    
                    # First, check for explicit bedroom mentions
                    bedroom_match = re.search(r'(\d+)[\s-]*(bed|br|bedroom)', title.lower())
                    if bedroom_match:
                        property_dict['bedrooms'] = int(bedroom_match.group(1))
                    
                    # If no match, check for "Apt X" pattern
                    elif re.search(r'apt\s+(\d+)', title.lower()):
                        apt_match = re.search(r'apt\s+(\d+)', title.lower())
                        property_dict['bedrooms'] = int(apt_match.group(1))
                    
                    # If still no match, check if property address ends with a number
                    elif re.search(r'\s(\d+)$', title.strip()):
                        end_match = re.search(r'\s(\d+)$', title.strip())
                        property_dict['bedrooms'] = int(end_match.group(1))
                    
                    # Look for apartment number after the suffix like 1L, 2R, etc.
                    elif re.search(r'apt\s+\d+[a-zA-Z]', title.lower()):
                        # Extract the digit part in patterns like "Apt 2L"
                        apt_letter_match = re.search(r'apt\s+(\d+)[a-zA-Z]', title.lower())
                        if apt_letter_match:
                            property_dict['bedrooms'] = int(apt_letter_match.group(1))
                    
                    # Extract from title like "10 Seminary Apt 2"
                    elif "Seminary Apt" in title:
                        seminary_match = re.search(r'Seminary\s+Apt\s+(\d+)', title)
                        if seminary_match:
                            property_dict['bedrooms'] = int(seminary_match.group(1))
                    
                    else:
                        property_dict['bedrooms'] = None
                except Exception as e:
                    print(f"Error extracting bedrooms from title '{title}': {str(e)}")
                    property_dict['bedrooms'] = None
                
            result.append(property_dict)
        
        cur.close()
        conn.close()
        
        return jsonify(result)
    except Exception as e:
        print(f"Error getting saved listings: {str(e)}")
        return jsonify({"error": str(e)}), 500

@housing_bp.route('/api/update-property-database', methods=['GET'])
def update_property_database():
    """Update the database with correct property details from original sources"""
    try:
        # Direct database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # First, check how many properties need updating
        cur.execute("""
        SELECT id, title, url, price, bedrooms 
        FROM properties 
        WHERE url LIKE '%%binghamtonwest.com%%'
        """)
        
        properties = cur.fetchall()
        total_count = len(properties)
        updated_count = 0
        errors = []
        
        for prop in properties:
            try:
                if prop['url']:
                    print(f"Updating property {prop['id']}: {prop['title']}")
                    
                    # Attempt to extract bedrooms from title if not already set
                    extracted_bedrooms = None
                    if not prop['bedrooms']:
                        title = prop['title']
                        try:
                            # Look for patterns like "2 Bedroom" or "2 BR" or "2-Bedroom" or "Apt 2" or ending with 2
                            import re
                            
                            # First, check for explicit bedroom mentions
                            bedroom_match = re.search(r'(\d+)[\s-]*(bed|br|bedroom)', title.lower())
                            if bedroom_match:
                                extracted_bedrooms = int(bedroom_match.group(1))
                            
                            # If no match, check for "Apt X" pattern
                            elif re.search(r'apt\s+(\d+)', title.lower()):
                                apt_match = re.search(r'apt\s+(\d+)', title.lower())
                                extracted_bedrooms = int(apt_match.group(1))
                            
                            # If still no match, check if property address ends with a number
                            elif re.search(r'\s(\d+)$', title.strip()):
                                end_match = re.search(r'\s(\d+)$', title.strip())
                                extracted_bedrooms = int(end_match.group(1))
                            
                            # Look for apartment number after the suffix like 1L, 2R, etc.
                            elif re.search(r'apt\s+\d+[a-zA-Z]', title.lower()):
                                # Extract the digit part in patterns like "Apt 2L"
                                apt_letter_match = re.search(r'apt\s+(\d+)[a-zA-Z]', title.lower())
                                if apt_letter_match:
                                    extracted_bedrooms = int(apt_letter_match.group(1))
                            
                            # Extract from title like "10 Seminary Apt 2"
                            elif "Seminary Apt" in title:
                                seminary_match = re.search(r'Seminary\s+Apt\s+(\d+)', title)
                                if seminary_match:
                                    extracted_bedrooms = int(seminary_match.group(1))
                                
                        except Exception as e:
                            print(f"Error extracting bedrooms from title '{title}': {str(e)}")
                    
                    # If we successfully extracted bedrooms from the title, update immediately
                    if extracted_bedrooms is not None:
                        cur.execute(
                            "UPDATE properties SET bedrooms = %s WHERE id = %s",
                            (extracted_bedrooms, prop['id'])
                        )
                        updated_count += 1
                        print(f"Updated property {prop['id']} with extracted bedrooms: {extracted_bedrooms}")
                        continue
                    
                    # Use the extract_property_details function to get fresh data from URL
                    updated_details = extract_property_details(prop['url'])
                    
                    # If successful, update the property details
                    if updated_details and updated_details.get('success'):
                        updates = []
                        params = []
                        
                        # Update bedrooms if available and not already set
                        if updated_details.get('bedrooms') and (not prop['bedrooms'] or prop['bedrooms'] == ''):
                            updates.append("bedrooms = %s")
                            params.append(updated_details['bedrooms'])
                        
                        # Update price if available and current is just "$" or "$,"
                        if updated_details.get('price'):
                            price = updated_details['price']
                            if price and price not in ['$', '$,', 'No price'] and (not prop['price'] or prop['price'] in ['$', '$,', 'No price']):
                                updates.append("price = %s")
                                params.append(price)
                        
                        # Only update if we have changes to make
                        if updates:
                            params.append(prop['id'])
                            update_query = f"UPDATE properties SET {', '.join(updates)} WHERE id = %s"
                            cur.execute(update_query, params)
                            updated_count += 1
            except Exception as e:
                error_msg = f"Error updating property {prop['id']}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Database update complete. Updated {updated_count} of {total_count} properties.",
            "updated_count": updated_count,
            "total_count": total_count,
            "errors": errors
        })
    except Exception as e:
        print(f"Error updating property database: {str(e)}")
        return jsonify({"error": str(e), "message": "Database error occurred"}), 500 