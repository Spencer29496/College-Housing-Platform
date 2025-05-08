"""
Web scraper for Binghamton West listings

This script:
1. Scrapes apartment listings from Binghamton West website
2. Extracts title, pricing, link, and location information
3. Updates the PostgreSQL database with the data
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import time
import requests
import os
import sys
from urllib.parse import urljoin

# Import directly for Docker environment
try:
    from config.db import create_properties_table, save_to_database
except ImportError:
    # Fallback for local development
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.config.db import create_properties_table, save_to_database

BASE_URL = "https://www.binghamtonwest.com"
BEDROOM_CATEGORIES = {
    "1 Bed": 1,
    "2 Beds": 2,
    "3 Beds": 3,
    "4 Beds": 4,
    "5 Beds": 5,
    "6 Beds": 6,
    "7 Beds": 7
}

def format_address_from_url(url_path):
    """Format a URL path into a readable address."""
    # Format the URL path as an address (e.g., "10-seminary-apt-2" -> "10 Seminary Apt 2")
    # Replace hyphens with spaces but keep those between apt and unit numbers
    address_parts = []
    for part in url_path.split('-'):
        if part.lower() in ['apt', 'unit', 'suite']:
            # Keep the previous part and add this with a space
            if address_parts:
                address_parts[-1] = f"{address_parts[-1]} {part}"
        else:
            address_parts.append(part)
    
    formatted_address = " ".join(address_parts).title()
    
    # Clean up any remaining issues
    formatted_address = re.sub(r'\s+', ' ', formatted_address).strip()
    
    return formatted_address

def fetch_property_listings():
    """Fetch and parse property listings from Binghamton West using Selenium."""
    print(f"Fetching property listings from {BASE_URL}")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/google-chrome"
    
    # Set up Chrome Service with the path to chromedriver installed in the Dockerfile
    service = Service(executable_path="/usr/local/bin/chromedriver")
    
    # Initialize Chrome driver with service and options
    driver = webdriver.Chrome(service=service, options=options)
    
    # Hard-code property URLs based on the website structure
    # This is more reliable than trying to navigate the menu
    property_urls = {
        # 1 Bedrooms
        1: [
            "https://www.binghamtonwest.com/10-seminary-apt-2",
            "https://www.binghamtonwest.com/10-seminary-apt-3",
            "https://www.binghamtonwest.com/14-seminary-apt-2a",
            "https://www.binghamtonwest.com/14-seminary-apt-2nd-fl",
            "https://www.binghamtonwest.com/14-seminary-apt-3rd-fl",
            "https://www.binghamtonwest.com/16-seminary-apt-1f",
            "https://www.binghamtonwest.com/16-seminary-apt-3",
            "https://www.binghamtonwest.com/18-5-seminary-apt-1",
            "https://www.binghamtonwest.com/18-5-seminary-apt-2",
            "https://www.binghamtonwest.com/31-leroy-apt-4",
            "https://www.binghamtonwest.com/40-walnut-apt-1",
            "https://www.binghamtonwest.com/40-walnut-apt-2",
            "https://www.binghamtonwest.com/43-leroy-apt-1f",
            "https://www.binghamtonwest.com/43-leroy-apt-2r",
            "https://www.binghamtonwest.com/68-chapin-apt-2l",
            "https://www.binghamtonwest.com/69-st-john-apt-2r",
            "https://www.binghamtonwest.com/93-murray-apt-2"
        ],
        # 2 Bedrooms
        2: [
            "https://www.binghamtonwest.com/4-seminary-apt-3",
            "https://www.binghamtonwest.com/10-johnson-apt-l-or-r",
            "https://www.binghamtonwest.com/10-seminary-apt-1",
            "https://www.binghamtonwest.com/12-vincent",
            "https://www.binghamtonwest.com/14-seminary-apt-1",
            "https://www.binghamtonwest.com/16-seminary-apt-1r",
            "https://www.binghamtonwest.com/18-seminary-apt-2",
            "https://www.binghamtonwest.com/29-leroy-apt-6",
            "https://www.binghamtonwest.com/38-5-oak",
            "https://www.binghamtonwest.com/41-kneeland-apt-1-2",
            "https://www.binghamtonwest.com/41-leroy-apt-2",
            "https://www.binghamtonwest.com/53-5-murray-apt-1",
            "https://www.binghamtonwest.com/68-chapin-apt-1l",
            "https://www.binghamtonwest.com/69-st-john-apt-1",
            "https://www.binghamtonwest.com/74-oak-apt-1",
            "https://www.binghamtonwest.com/93-murray-apt-1",
            "https://www.binghamtonwest.com/160-seminary-apt-1-or-2"
        ],
        # 3 Bedrooms
        3: [
            "https://www.binghamtonwest.com/2-ayres-apt-r",
            "https://www.binghamtonwest.com/4-seminary-apt-2",
            "https://www.binghamtonwest.com/5-ayres-apt-1-or-2",
            "https://www.binghamtonwest.com/18-seminary-apt-1",
            "https://www.binghamtonwest.com/41-leroy-apt-1",
            "https://www.binghamtonwest.com/50-leroy-apt-l",
            "https://www.binghamtonwest.com/56-st-john-apt-r",
            "https://www.binghamtonwest.com/59-murray-apt-1-or-2",
            "https://www.binghamtonwest.com/74-oak-apt-2-or-3",
            "https://www.binghamtonwest.com/93-chapin-apt-r",
            "https://www.binghamtonwest.com/104-chapin-apt-2"
        ],
        # 4 Bedrooms
        4: [
            "https://www.binghamtonwest.com/6-ayres",
            "https://www.binghamtonwest.com/7-walnut",
            "https://www.binghamtonwest.com/25-seminary",
            "https://www.binghamtonwest.com/38-st-john",
            "https://www.binghamtonwest.com/40-st-john",
            "https://www.binghamtonwest.com/44-murray",
            "https://www.binghamtonwest.com/50-leroy-apt-r",
            "https://www.binghamtonwest.com/53-5-murray-apt-2",
            "https://www.binghamtonwest.com/54-leroy",
            "https://www.binghamtonwest.com/55-st-john",
            "https://www.binghamtonwest.com/93-chapin-apt-l",
            "https://www.binghamtonwest.com/106-murray"
        ],
        # 5 Bedrooms - add more URLs as needed
        5: [
            "https://www.binghamtonwest.com/3-ayres",
            "https://www.binghamtonwest.com/17-st-john",
            "https://www.binghamtonwest.com/18-seminary",
            "https://www.binghamtonwest.com/23-ayres",
            "https://www.binghamtonwest.com/29-seminary",
            "https://www.binghamtonwest.com/30-seminary",
            "https://www.binghamtonwest.com/38-oak"
        ],
        # 6 Bedrooms - add more URLs as needed
        6: [
            "https://www.binghamtonwest.com/2-ayres",
            "https://www.binghamtonwest.com/5-ayres",
            "https://www.binghamtonwest.com/11-ayres",
            "https://www.binghamtonwest.com/13-seminary"
        ],
        # 7 Bedrooms - add more URLs as needed
        7: [
            "https://www.binghamtonwest.com/50-leroy",
            "https://www.binghamtonwest.com/93-chapin",
            "https://www.binghamtonwest.com/97-chapin"
        ]
    }
    
    # Get all listings from the direct URLs
    all_listings = []
    
    try:
        # Process each bedroom category
        for bedrooms, urls in property_urls.items():
            print(f"\nProcessing {bedrooms} bedroom listings...")
            
            # Visit each property URL directly
            for apartment_url in urls:
                try:
                    print(f"Visiting {apartment_url}")
                    driver.get(apartment_url)
                    time.sleep(3)
                    
                    # Get the page content
                    page_html = driver.page_source
                    soup = BeautifulSoup(page_html, 'html.parser')
                    
                    # ALWAYS use URL-derived title - never from page content
                    url_path = apartment_url.split("/")[-1]
                    title = format_address_from_url(url_path)
                    
                    # Extract images - look for large images first
                    image_url = None
                    all_images = soup.find_all("img")
                    
                    # First try to find map images
                    for img in all_images:
                        try:
                            src = img.get("src")
                            if not src:
                                continue
                                
                            # Prioritize map images
                            if "map" in src.lower() or "location" in src.lower():
                                image_url = src
                                if not image_url.startswith(("http://", "https://")):
                                    image_url = urljoin(BASE_URL, image_url)
                                print(f"Found map image: {image_url}")
                                break
                        except Exception as e:
                            print(f"Error processing image: {e}")
                    
                    # If no map image found, then try property-specific images
                    if not image_url:
                        for img in all_images:
                            try:
                                src = img.get("src")
                                if not src:
                                    continue
                                    
                                # Skip obvious non-property images
                                if any(x in src.lower() for x in ["logo", "icon", "button", "wix-image", "bedroom"]):
                                    continue
                                    
                                # Look for property photos
                                if (("seminary" in src.lower() and "apt" in src.lower()) or 
                                    any(street in src.lower() for street in ["ayres", "murray", "leroy", "chapin", "walnut", "oak"])):
                                    image_url = src
                                    if not image_url.startswith(("http://", "https://")):
                                        image_url = urljoin(BASE_URL, image_url)
                                    print(f"Found property image: {image_url}")
                                    break
                            except Exception as e:
                                print(f"Error processing image: {e}")
                    
                    # Fallback: If still no image, check for any large image (non-bedroom)
                    if not image_url:
                        for img in all_images:
                            try:
                                # Skip tiny images, icons, logos, and bedroom images
                                if ((img.get("width") and int(img.get("width", "0")) > 200) or 
                                   (img.get("height") and int(img.get("height", "0")) > 200)):
                                    src = img.get("src")
                                    if src and not any(x in src.lower() for x in ["icon", "logo", "button", "bedroom"]):
                                        image_url = src
                                        if not image_url.startswith(("http://", "https://")):
                                            image_url = urljoin(BASE_URL, image_url)
                                        print(f"Found large image: {image_url}")
                                        break
                            except Exception as e:
                                print(f"Error processing image: {e}")
                    
                    # Last resort: If still no image, use a placeholder image
                    if not image_url:
                        # Use a placeholder image instead
                        image_url = f"{BASE_URL}/static/images/placeholder.jpg"
                        print(f"Using placeholder image: {image_url}")
                    
                    # Use the same URL-derived title for location
                    location = title
                    
                    # Look for price
                    price = "Contact for price"
                    price_pattern = re.compile(r'\$\s*[\d,]+(?:\.\d+)?(?:/[a-zA-Z]+)?')
                    
                    # Check text nodes for price
                    text_nodes = soup.find_all(text=True)
                    for text in text_nodes:
                        match = price_pattern.search(text)
                        if match and len(match.group()) > 1:  # Ensure we have more than just the $ symbol
                            price = match.group()
                            break
                    
                    # Extract details from the page
                    amenities = []
                    description = ""
                    
                    # Method 1: Look for property details in a specific section with green background
                    property_details_found = False
                    property_sections = soup.select('div[style*="background-color:rgba(0, 138, 69, 1)"]')
                    if not property_sections:
                        property_sections = soup.select('.containerr1[style*="background-color:rgba(0, 138, 69, 1)"]')
                        
                    if property_sections:
                        for section in property_sections:
                            # Extract text content from the section
                            section_text = section.get_text().strip()
                            if "Property Details" in section_text:
                                property_details_found = True
                                
                                # Find all paragraphs in this section
                                paragraphs = section.find_all('p')
                                for p in paragraphs:
                                    text = p.get_text().strip()
                                    if text and not text.startswith('Property Details'):
                                        # Split by lines and add each line as an amenity
                                        for line in text.split('\n'):
                                            clean_line = line.strip()
                                            if clean_line and not clean_line.lower() == 'property details':
                                                amenities.append(clean_line)
                    
                    # Method 2: Look for specific text content that indicates property features
                    if not property_details_found:
                        feature_texts = [
                            'Bedroom', 'Bathroom', 'Kitchen', 'Living Room', 'Furnished',
                            'Porch', 'Laundry', 'Pet Friendly', 'Bus Stop', 'Fully'
                        ]
                        
                        # Find all paragraphs and check for feature text
                        for p in soup.find_all(['p', 'div']):
                            text = p.get_text().strip()
                            if text and any(feature in text for feature in feature_texts):
                                # Check if this looks like a property feature list
                                clean_lines = []
                                for line in text.replace('<br>', '\n').split('\n'):
                                    clean_line = line.strip()
                                    if clean_line and len(clean_line) > 3 and not clean_line.lower() == 'property details':
                                        clean_lines.append(clean_line)
                                
                                # If we have multiple lines, it's probably a feature list
                                if len(clean_lines) >= 2:
                                    amenities.extend(clean_lines)
                                    property_details_found = True

                    # Method 2.5: Look for checkmark lists which often indicate property features
                    if not property_details_found or len(amenities) < 3:  # If no details found or very few
                        checkmark_elements = soup.find_all(['span', 'p', 'div'], text=re.compile(r'✓'))
                        if checkmark_elements:
                            for elem in checkmark_elements:
                                feature_text = elem.get_text().strip()
                                if feature_text.startswith('✓') and len(feature_text) > 2:
                                    # Clean up the checkmark feature text
                                    clean_feature = feature_text.replace('✓', '').strip()
                                    if clean_feature and len(clean_feature) > 3:
                                        amenities.append(clean_feature)
                                        property_details_found = True

                    # Method 2.6: Look for list items that might contain features
                    if not property_details_found or len(amenities) < 3:
                        list_items = soup.find_all(['li'])
                        feature_keywords = ['bedroom', 'bathroom', 'kitchen', 'living', 'furnished', 'porch', 
                                            'laundry', 'pet', 'bus', 'location', 'contact', 'office', 'hours']
                        
                        feature_list = []
                        for li in list_items:
                            text = li.get_text().strip()
                            if text and any(keyword in text.lower() for keyword in feature_keywords):
                                feature_list.append(text)
                        
                        if len(feature_list) >= 2:  # If we found multiple list items with feature keywords
                            amenities.extend(feature_list)
                            property_details_found = True
                    
                    # Method 3: Look for description
                    description_elements = soup.find_all(['p', 'div'], text=re.compile(r'(description|about this property)', re.I))
                    for elem in description_elements:
                        desc_text = elem.get_text().strip()
                        if len(desc_text) > 50:  # Only use substantial text as description
                            description = desc_text
                            break
                    
                    # If no substantial description found, check for "No description available" text
                    if not description or description.lower() == "no description available":
                        # Try to generate a basic description based on property details
                        if amenities:
                            property_type = "apartment" if "apt" in title.lower() else "property"
                            bedrooms_text = f"{bedrooms} bedroom" if bedrooms and bedrooms == 1 else f"{bedrooms} bedrooms" if bedrooms else ""
                            
                            # Create a more natural description with amenity grouping
                            description = f"This {bedrooms_text} {property_type} at {title} "
                            
                            # Group similar amenities
                            has_bedroom = any("bedroom" in a.lower() for a in amenities)
                            has_bathroom = any("bathroom" in a.lower() for a in amenities)
                            has_kitchen = any("kitchen" in a.lower() for a in amenities)
                            has_laundry = any("laundry" in a.lower() for a in amenities)
                            has_furnished = any("furnished" in a.lower() for a in amenities)
                            
                            features = []
                            if has_bedroom and has_bathroom and has_kitchen:
                                features.append("includes bedroom, bathroom, and kitchen")
                            else:
                                if has_bedroom:
                                    features.append("includes bedroom")
                                if has_bathroom:
                                    features.append("includes bathroom")
                                if has_kitchen:
                                    features.append("includes kitchen")
                                    
                            if has_furnished:
                                features.append("comes fully furnished")
                            if has_laundry:
                                features.append("has laundry facilities available")
                                
                            # Add other notable amenities
                            other_amenities = [a for a in amenities if not any(x in a.lower() for x in 
                                              ["bedroom", "bathroom", "kitchen", "furnished", "laundry"])]
                            if other_amenities:
                                notable = other_amenities[:3]
                                if features:
                                    features.append("and also features " + ", ".join(notable))
                                else:
                                    features.append("features " + ", ".join(notable))
                            
                            if features:
                                description += " " + ". It ".join(features) + "."
                            else:
                                description += "offers: " + ", ".join(amenities[:5])
                                if len(amenities) > 5:
                                    description += ", and more."
                                else:
                                    description += "."
                        else:
                            description = "No description available. Contact the property manager for more details."
                    
                    # Extract bedrooms from URL or title
                    bedrooms = extract_bedrooms(title)
                    
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_amenities = []
                    for item in amenities:
                        clean_item = item.strip()
                        if clean_item and clean_item not in seen:
                            seen.add(clean_item)
                            unique_amenities.append(clean_item)
                    
                    # Add the listing
                    listing = {
                        "title": title,
                        "price": price,
                        "location": location,
                        "url": apartment_url,
                        "bedrooms": bedrooms,
                        "image_url": image_url
                    }
                    
                    all_listings.append(listing)
                    print(f"Added listing: {title}, {bedrooms} bedroom(s), {price}")
                    print(f"Location: {location}")
                    print(f"URL: {apartment_url}")
                    print("-" * 50)
                    
                except Exception as e:
                    print(f"Error processing apartment {apartment_url}: {e}")
    
    except Exception as e:
        print(f"Error processing listings: {e}")
    
    finally:
        driver.quit()
    
    print(f"Found total of {len(all_listings)} listings")
    return all_listings


def extract_bedrooms(title):
    """Extract number of bedrooms from title"""
    if not title:
        return None
        
    # First check if bedrooms are directly indicated in the title
    bed_patterns = [
        (r'(\d+)\s+bed', lambda x: int(x)),
        (r'(\d+)-bed', lambda x: int(x))
    ]
    
    for pattern, converter in bed_patterns:
        match = re.search(pattern, title.lower())
        if match:
            return converter(match.group(1))
    
    # Direct mapping for categories based on website structure
    for category, beds in BEDROOM_CATEGORIES.items():
        if category.lower() in title.lower():
            return beds
            
    return None

def extract_price(text_or_element):
    """Extract price from text or element"""
    if not text_or_element:
        return "Contact for price"
    
    # If it's an element, get the text
    if hasattr(text_or_element, 'get_text'):
        text = text_or_element.get_text().strip()
    else:
        text = str(text_or_element).strip()
    
    # Common price formats: $1,234 or $1234/mo or $1,234.56
    price_match = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', text)
    if price_match:
        return price_match.group(0).strip()
    
    return "Contact for price"

def extract_property_details(url):
    """
    Extract detailed property information from a Binghamton West listing URL.
    
    Args:
        url (str): The URL of the property listing.
        
    Returns:
        dict: Dictionary containing detailed property information.
    """
    if not url or not url.startswith(("http://", "https://")):
        return {"success": False, "error": "Invalid URL provided"}
    
    try:
        # Setup headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Make the request to the original listing
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                "success": False, 
                "error": f"Failed to fetch the URL: Status code {response.status_code}"
            }
            
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ALWAYS use URL-derived title - never from page content
        url_path = url.split("/")[-1]
        title = format_address_from_url(url_path)
        
        # Extract details from the page
        raw_amenities = []
        description = ""
        property_details_found = False
        
        # Extract from any property detail section on the page
        # Method 1: Look for specific sections or divs with property details
        for section in soup.find_all(['div', 'section']):
            section_text = section.get_text().strip().lower()
            if 'property' in section_text and ('detail' in section_text or 'feature' in section_text or 'amenities' in section_text):
                property_details_found = True
                # Extract all bullet points or paragraphs in this section
                for elem in section.find_all(['li', 'p']):
                    text = elem.get_text().strip()
                    if text and len(text) > 3 and not text.lower() == 'property details':
                        raw_amenities.append(text)
        
        # Method 2: Look for checkmark lists which often indicate property features
        if not property_details_found or len(raw_amenities) < 3:
            checkmark_elements = soup.find_all(['span', 'p', 'div', 'li'], text=re.compile(r'[✓✔]'))
            if checkmark_elements:
                for elem in checkmark_elements:
                    feature_text = elem.get_text().strip()
                    if re.match(r'^[✓✔]', feature_text) and len(feature_text) > 2:
                        # Clean up the checkmark feature text
                        clean_feature = re.sub(r'^[✓✔]\s*', '', feature_text).strip()
                        if clean_feature and len(clean_feature) > 3:
                            raw_amenities.append(clean_feature)
                            property_details_found = True
        
        # Method 3: Look for list items that might contain features
        if not property_details_found or len(raw_amenities) < 3:
            feature_keywords = ['bedroom', 'bathroom', 'kitchen', 'living', 'furnished', 'porch', 
                               'laundry', 'pet', 'bus', 'parking', 'storage', 'basement']
            
            for li in soup.find_all(['li']):
                text = li.get_text().strip()
                if text and any(keyword in text.lower() for keyword in feature_keywords):
                    raw_amenities.append(text)
                    property_details_found = True
        
        # Method 4: Look for specific property feature text
        if not property_details_found or len(raw_amenities) < 3:
            # Look for paragraphs containing property features
            feature_patterns = [
                r'\b(one|1|two|2|three|3|four|4)\s+bedroom',
                r'\bbig\s+eat[\s-]in\s+kitchen\b',
                r'\bliving\s+room\b',
                r'\bfully\s+furnished\b',
                r'\blaundry\s+available\b',
                r'\bfront\s+and\s+back\s+porch\b',
                r'\b(\d+)\s+block\s+to\s+bus\s+stop\b',
                r'\bparking\b',
                r'\bpet\s+friendly\b'
            ]
            
            for p in soup.find_all(['p', 'div', 'span']):
                text = p.get_text().strip()
                if text:
                    for pattern in feature_patterns:
                        match = re.search(pattern, text.lower())
                        if match:
                            # Extract the specific feature that matched
                            feature_text = match.group(0)
                            # Capitalize first letter of each word
                            feature_text = ' '.join(word.capitalize() for word in feature_text.split())
                            raw_amenities.append(feature_text)
                            property_details_found = True
        
        # Method 5: Extract from description text
        description_elements = soup.find_all(['p', 'div'], text=re.compile(r'(description|about this property)', re.I))
        for elem in description_elements:
            desc_text = elem.get_text().strip()
            if len(desc_text) > 50:  # Only use substantial text as description
                description = desc_text
                break
        
        # Look for price
        price = "Contact for price"
        price_pattern = re.compile(r'\$\s*[\d,]+(?:\.\d+)?(?:/[a-zA-Z]+)?')
        
        # Check text nodes for price
        text_nodes = soup.find_all(text=True)
        for text in text_nodes:
            match = price_pattern.search(text)
            if match and len(match.group()) > 1:  # Ensure we have more than just the $ symbol
                price = match.group()
                break
                
        # Extract availability information
        availability = None
        availability_pattern = re.compile(r'(?:available|unavailable) (?:until|from) ([a-zA-Z]+ \d{4})', re.I)
        
        for text in text_nodes:
            match = availability_pattern.search(text)
            if match:
                availability = match.group(0)
                break
        
        # Extract bedrooms from URL or title
        bedrooms = extract_bedrooms(title)
        
        # If no bedrooms found, try to extract from page content
        if not bedrooms:
            bedroom_pattern = re.compile(r'(\d+)[\s-]bedroom', re.I)
            for text in text_nodes:
                match = bedroom_pattern.search(text)
                if match:
                    bedrooms = int(match.group(1))
                    break
        
        # This is the key part that needs improvement - better standardization of amenities
        standardized_amenities = []
        amenity_map = {}
        
        # Process each raw amenity and add to our mapping
        for raw_amenity in raw_amenities:
            clean_text = raw_amenity.strip()
            if not clean_text:
                continue
                
            lower_text = clean_text.lower()
            
            # Key categories to detect and standardize
            if re.search(r'(one|1)\s+bedroom', lower_text, re.I) or "one bedroom" in lower_text:
                amenity_map["bedrooms"] = "One Bedroom"
            elif re.search(r'(two|2)\s+large?\s+bedroom', lower_text, re.I):
                amenity_map["bedrooms"] = "Two Large Bedrooms"
            elif re.search(r'(two|2)\s+bedroom', lower_text, re.I) or "two bedrooms" in lower_text:
                amenity_map["bedrooms"] = "Two Bedrooms"
            elif re.search(r'(three|3)\s+bedroom', lower_text, re.I) or "three bedrooms" in lower_text:
                amenity_map["bedrooms"] = "Three Bedrooms"
            elif re.search(r'(four|4)\s+bedroom', lower_text, re.I) or "four bedrooms" in lower_text:
                amenity_map["bedrooms"] = "Four Bedrooms"
            elif "bedroom" in lower_text and not any(x in amenity_map for x in ["bedrooms"]):
                amenity_map["bedrooms"] = clean_text
                
            # Bathroom
            elif re.search(r'(one|1)\s+bathroom', lower_text, re.I) or "one bathroom" in lower_text:
                amenity_map["bathroom"] = "One Bathroom"
            elif re.search(r'(two|2)\s+bathroom', lower_text, re.I) or "two bathrooms" in lower_text:
                amenity_map["bathroom"] = "Two Bathrooms"
            elif "bathroom" in lower_text and not "bathroom" in amenity_map:
                amenity_map["bathroom"] = clean_text
                
            # Kitchen
            elif re.search(r'kitchen\s+with\s+dining', lower_text, re.I) or "kitchen with dining" in lower_text:
                amenity_map["kitchen"] = "Kitchen with Dining Area"
            elif "eat-in kitchen" in lower_text or "eat in kitchen" in lower_text:
                amenity_map["kitchen"] = "Big Eat-In Kitchen"
            elif "kitchen" in lower_text and not "kitchen" in amenity_map:
                amenity_map["kitchen"] = "Kitchen"
                
            # Living areas
            elif "living room" in lower_text:
                amenity_map["living"] = "Living Room"
            elif "dining area" in lower_text and not "kitchen" in amenity_map:
                amenity_map["dining"] = "Dining Area"
            elif "dining room" in lower_text:
                amenity_map["dining"] = "Dining Room"
            elif "bonus room" in lower_text:
                amenity_map["bonus"] = "Bonus Room"
                
            # Features
            elif "enclosed yard" in lower_text:
                amenity_map["yard"] = "Enclosed Yard"
            elif "furnished" in lower_text:
                amenity_map["furnished"] = "Furnished"
            elif "pet friendly" in lower_text or "pets allowed" in lower_text:
                amenity_map["pets"] = "Pet Friendly"
            elif re.search(r'(\d+)\s+block\s+to\s+bus', lower_text, re.I) or "block to bus stop" in lower_text:
                amenity_map["bus"] = "1 Block to Bus Stop"
            elif "washer" in lower_text and "dryer" in lower_text:
                amenity_map["laundry"] = "Washer & Dryer"
            elif "laundry" in lower_text:
                amenity_map["laundry"] = "Laundry Available"
            elif "front porch" in lower_text:
                amenity_map["porch"] = "Front Porch"
            elif "porch" in lower_text:
                amenity_map["porch"] = clean_text
        
        # Build the standardized amenities list from our mapping
        if bedrooms == 1 and "bedrooms" not in amenity_map:
            standardized_amenities.append("One Bedroom")
        elif bedrooms == 2 and "bedrooms" not in amenity_map:
            standardized_amenities.append("Two Bedrooms")
        elif "bedrooms" in amenity_map:
            standardized_amenities.append(amenity_map["bedrooms"])
            
        if "bathroom" in amenity_map:
            standardized_amenities.append(amenity_map["bathroom"])
        else:
            standardized_amenities.append("One Bathroom")
            
        if "kitchen" in amenity_map:
            standardized_amenities.append(amenity_map["kitchen"])
        else:
            standardized_amenities.append("Kitchen")
            
        if "living" in amenity_map:
            standardized_amenities.append(amenity_map["living"])
        else:
            standardized_amenities.append("Living Room")
            
        # Add the rest of the amenities
        for key, value in amenity_map.items():
            if key not in ["bedrooms", "bathroom", "kitchen", "living"] and value not in standardized_amenities:
                standardized_amenities.append(value)
                
        # Add other standard amenities if not found - based on property pattern
        standard_amenities = [
            "Pet Friendly",
            "1 Block to Bus Stop"
        ]
        
        for amenity in standard_amenities:
            if amenity.lower() not in [a.lower() for a in standardized_amenities]:
                standardized_amenities.append(amenity)
                
        # If we couldn't get a good set of amenities, add these defaults
        if len(standardized_amenities) < 3:
            default_amenities = [
                "Kitchen",
                "Living Room",
                "Fully Furnished",
                "Pet Friendly",
                "1 Block to Bus Stop"
            ]
            for amenity in default_amenities:
                if amenity not in standardized_amenities:
                    standardized_amenities.append(amenity)
        
        # If no description available, generate one based on amenities
        if not description or description.lower() == "no description available.":
            if standardized_amenities:
                property_type = "apartment" if "apt" in title.lower() else "property"
                bedrooms_text = f"{bedrooms} bedroom" if bedrooms and bedrooms == 1 else f"{bedrooms} bedrooms" if bedrooms else ""
                
                description = f"This {bedrooms_text} {property_type} at {title} features "
                
                if len(standardized_amenities) > 1:
                    description += ", ".join(standardized_amenities[:-1]) + " and " + standardized_amenities[-1] + "."
                else:
                    description += standardized_amenities[0] + "."
            else:
                description = "No description available. Contact the property manager for more details."
        
        # Build result dictionary
        result = {
            "success": True,
            "title": title,
            "price": price,
            "location": title,  # Same as title
            "url": url,
            "bedrooms": bedrooms,
            "amenities": standardized_amenities,
            "description": description,
            "availability": availability
        }
        
        return result
        
    except Exception as e:
        import traceback
        print(f"Error extracting property details from {url}: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

def main():
    print("Starting scraper...\n")
    try:
        create_properties_table()
        listings = fetch_property_listings()
        if listings:
            print("\nSaving listings to database...\n")
            save_to_database(listings)
        else:
            print("No listings found.")
    except Exception as e:
        print(f"Error in main: {e}")
    print("Scraper finished.")


if __name__ == "__main__":
    main()
