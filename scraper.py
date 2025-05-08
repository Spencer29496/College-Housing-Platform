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
    from config.db import create_properties_table, save_to_database, truncate_properties_table
except ImportError:
    # Fallback for local development
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.config.db import create_properties_table, save_to_database, truncate_properties_table

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

# Define property URLs by bedroom count
property_urls = {
    1: [
        "10-seminary-apt-1",
        "14-seminary-apt-1",
        "16-seminary-apt-1f",
        "16-seminary-apt-1r",
        "18-5-seminary-apt-1",
        "18-seminary-apt-1",
        "4-seminary-apt-1",
        "40-walnut-apt-1",
        "41-leroy-apt-1",
        "43-leroy-apt-1f",
        "53-5-murray-apt-1",
        "68-chapin-apt-1l",
        "69-st-john-apt-1",
        "74-oak-apt-1",
        "93-murray-apt-1"
    ],
    2: [
        "10-seminary-apt-2",
        "12-vincent",
        "14-seminary-apt-2a",
        "14-seminary-apt-2nd-fl",
        "18-5-seminary-apt-2",
        "18-seminary-apt-2",
        "29-leroy-apt-4",
        "29-leroy-apt-6",
        "38-5-oak",
        "4-seminary-apt-2",
        "40-st-john",
        "40-walnut-apt-2",
        "41-kneeland-apt-1-2",
        "41-leroy-apt-2",
        "43-leroy-apt-2r",
        "53-5-murray-apt-2",
        "56-st-john-apt-r",
        "68-chapin-apt-2l",
        "69-st-john-apt-2r",
        "74-oak-apt-2-or-3",
        "93-murray-apt-2",
        "104-chapin-apt-2",
        "160-seminary-apt-1-or-2"
    ],
    3: [
        "10-seminary-apt-3",
        "13-seminary",
        "14-seminary-apt-3rd-fl",
        "16-seminary-apt-3",
        "2-ayres",
        "23-ayres",
        "3-ayres",
        "4-seminary-apt-3",
        "11-ayres",
        "42-front",
        "44-murray",
        "50-leroy-apt-l",
        "50-leroy-apt-r",
        "54-leroy",
        "59-murray",
        "93-chapin-apt-l",
        "93-chapin-apt-r",
        "97-chapin"
    ],
    4: [
        "5-ayres",
        "6-ayres",
        "25-seminary",
        "29-seminary",
        "30-seminary"
    ],
    5: [
        "7-walnut",
        "17-chapin"
    ]
}

def get_lazy_image_src(driver, img):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", img)
    time.sleep(0.3)
    src = img.get_attribute("src")
    if src and not src.startswith("data:"):
        return src
    for attr in ("data-src", "data-srcset"):
        src = (img.get_attribute(attr) or "").split()[0]
        if src and not src.startswith("data:"):
            return src
    return None

def is_phone_number(text):
    """Check if text is a phone number in any common format."""
    if not text:
        return False
    # Match formats like 607-221-6592, (607) 221-6592, 607.221.6592, 6072216592
    phone_patterns = [
        r'^\d{3}-\d{3}-\d{4}$',
        r'^\(\d{3}\)\s*\d{3}-\d{4}$',
        r'^\d{3}\.\d{3}\.\d{4}$',
        r'^\d{10}$'
    ]
    return any(re.match(pattern, text.strip()) for pattern in phone_patterns)

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

def is_generic_listing(title, url_path):
    """Check if this is a generic listing that should be filtered out"""
    # Simplified check - only check for extremely short URL paths
    if len(url_path.split('-')) <= 1:
        return True
        
    return False

def generate_listing_url(title):
    """Generate a URL for a specific listing based on its title."""
    # Format the title into a URL-friendly string
    # E.g., "10 Seminary Apt 2" -> "10-seminary-apt-2"
    if not title:
        return None
        
    url_path = title.lower().strip()
    url_path = re.sub(r'\s+', '-', url_path)  # Replace spaces with hyphens
    url_path = re.sub(r'[^\w\-]', '', url_path)  # Remove non-alphanumeric chars except hyphens
    
    # Create the full URL
    return urljoin(BASE_URL, url_path)

def url_exists(url):
    """Check if a URL exists and doesn't return a 404 (Simple Check)."""
    # Keep a basic check for None/empty URLs if needed elsewhere, 
    # but the main validation will happen in Selenium.
    if not url:
        return False
    try:
        # Quick HEAD request just to see if server responds ok
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

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
    
    # NEW APPROACH: Go directly to each bedroom category page
    all_listings = []
    bedroom_categories = [
        {"url": "https://www.binghamtonwest.com/1-bedroom", "bedrooms": 1},
        {"url": "https://www.binghamtonwest.com/2-beds", "bedrooms": 2},
        {"url": "https://www.binghamtonwest.com/3-beds", "bedrooms": 3},
        {"url": "https://www.binghamtonwest.com/4-beds", "bedrooms": 4},
        {"url": "https://www.binghamtonwest.com/5-beds", "bedrooms": 5},
        {"url": "https://www.binghamtonwest.com/6-beds", "bedrooms": 6},
        {"url": "https://www.binghamtonwest.com/7-beds", "bedrooms": 7}
    ]
    
    for category in bedroom_categories:
        try:
            print(f"\nProcessing {category['bedrooms']} bedroom listings...")
            driver.get(category["url"])
            time.sleep(4) # Allow page to load
            
            # --- Add temporary code to print HTML structure of the first container --- 
            try:
                print("\n--- Attempting to print HTML of first listing container ---")
                container_selector = "div[data-testid='mesh-container-content'] > div[id^='comp-'][id*='__item-']"
                first_container = driver.find_element(By.CSS_SELECTOR, container_selector)
                print(f"\n--- Container Outer HTML: ---")
                try:
                   print(first_container.get_attribute('outerHTML'))
                except Exception as inner_ex:
                   print(f"Error getting outerHTML for container: {inner_ex}")
                print("---------------------------")
            except Exception as html_ex:
                print(f"Could not get HTML structure for selector '{container_selector}': {html_ex}")
            
            print("\nExiting forcefully after printing structure for analysis.")
            driver.quit()
            sys.exit(0) # Force exit
            # --- End temporary code ---

            # Find all listing containers based on observed ID pattern
            listing_containers = driver.find_elements(By.CSS_SELECTOR, container_selector) # Reuse selector
            print(f"Found {len(listing_containers)} potential listing containers on category page.")

            if not listing_containers:
                print(f"No listing containers found for {category['bedrooms']} beds. Skipping category.")
                continue

            # Loop through each container instead of h2
            for container in listing_containers:
                try:
                    # --- Extract data relative to the container --- 
                    title_element = container.find_element(By.CSS_SELECTOR, "h2")
                    property_title = title_element.text.strip()
                    
                    # Skip empty/irrelevant titles (reuse existing checks)
                    if not property_title or property_title.upper() == "BINGHAMTON WEST":
                        continue
                    if "BEDROOM" in property_title.upper():
                         continue
                    if not any(char.isdigit() for char in property_title):
                         continue
                         
                    title = property_title # Use the extracted title
                    print(f"\n--- Processing listing ---")
                    print(f"Title: '{title}'")

                    # Extract Listing URL from the container's link
                    try:
                        link_element = container.find_element(By.TAG_NAME, "a") 
                        listing_url = link_element.get_attribute('href')
                        if listing_url and not listing_url.startswith(("http://", "https://")):
                            listing_url = urljoin(BASE_URL, listing_url)
                        print(f"Extracted Listing URL: {listing_url}")
                    except Exception as link_ex:
                        print(f"Could not find listing URL link for '{title}': {link_ex}. Skipping.")
                        continue
                    
                    if not listing_url:
                        print(f"Empty listing URL found for '{title}'. Skipping.")
                        continue

                    # Extract Image URL from the container's image
                    try:
                        img_element = container.find_element(By.TAG_NAME, "img")
                        image_url = get_lazy_image_src(driver, img_element)
                        # Wix images seem fully qualified, but check just in case
                        if image_url and not image_url.startswith(("http://", "https://")):
                            image_url = urljoin(BASE_URL, image_url)
                        print(f"Extracted Image URL: {image_url}")
                    except Exception as img_ex:
                        print(f"Could not find listing image for '{title}': {img_ex}. Skipping.")
                        continue
                        
                    if not image_url:
                        print(f"Empty image URL found for '{title}'. Skipping.")
                        continue
                        
                    # Extract Price (relative to container now)
                    price = "Contact for price"
                    try:
                        # Look for price text within the container
                        price_elements = container.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                        if price_elements:
                            price_text = price_elements[0].text
                            price_match = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', price_text)
                            if price_match:
                                price = price_match.group(0).strip()
                    except Exception as price_ex:
                        print(f"Could not extract price for '{title}': {price_ex}")
                    print(f"Price: {price}")

                    # --- Validation using Selenium (using extracted URLs) --- 
                    map_image_url = None # Reset for each listing
                    map_image_found = False
                    images_validated = False 
                    try:
                        # ... (Keep the existing block that opens new tab, visits extracted listing_url)
                        driver.execute_script("window.open('');")
                        driver.switch_to.window(driver.window_handles[1])
                        driver.get(listing_url) # USE EXTRACTED URL
                        time.sleep(2) 
                        page_title = driver.title
                        print(f"Visiting {listing_url} - Title: '{page_title}'")
                        if "404" in page_title or "not found" in page_title.lower() or "isn\'t available" in page_title.lower():
                            # ... (rest of the validation logic: find map image, check images with JS) ...
                            # IMPORTANT: The JS check should use the *extracted* image_url from the container
                            # Check main image_url (extracted from container)
                            # ... 
                            main_img_valid = driver.execute_script(
                                js_check_image, image_url, known_placeholder_url)
                            # ... (check map_img_valid)
                            # ... (skip if validation fails) ...
# ... (rest of the script remains largely the same, ensuring validated & extracted data is stored) ...
                            print(f"Skipping listing {title}: Page title indicates error or 404.")
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue # Skip to next container
                        
                        # Look for map image on detail page (existing logic)
                        detail_images = driver.find_elements(By.TAG_NAME, "img")
                        for img in detail_images:
                             src = img.get_attribute("src")
                             if src and ("map" in src.lower() or "location" in src.lower()):
                                 map_image_url = src
                                 if not map_image_url.startswith(("http://", "https://")):
                                     map_image_url = urljoin(BASE_URL, map_image_url)
                                 map_image_found = True
                                 print(f"Found map image: {map_image_url}")
                                 break
                        thumbnail_url = image_url or map_image_url
                        if not thumbnail_url:
                            print(f"No usable image for {title}; skipping.")
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue   # jump to the next listing
                        # ... (fallback logic for finding map image if needed) ...
                        
                        # Define the JS check function (ensure it's still defined)
                        js_check_image = """ 
                            var img = document.createElement('img');
                            var srcToCheck = arguments[0];
                            var knownPlaceholder = arguments[1]; 
                            img.src = srcToCheck;
                            if (knownPlaceholder && srcToCheck === knownPlaceholder) { return false; }
                            var isLoaded = img.complete && 
                                           (typeof img.naturalWidth === 'undefined' || img.naturalWidth > 0) &&
                                           (typeof img.offsetWidth === 'undefined' || img.offsetWidth > 0); 
                            return isLoaded;
                            """
                        known_placeholder_url = "https://www.binghamtonwest.com/static/images/placeholder.jpg"
                             
                        # Validate extracted main image URL
                        if not image_url:
                             print(f"Skipping listing {title}: Main image URL was missing before validation.")
                             driver.close()
                             driver.switch_to.window(driver.window_handles[0])
                             continue
                        main_img_valid = driver.execute_script(js_check_image, image_url, known_placeholder_url)

                        # Validate found map image URL
                        if not map_image_found or not map_image_url:
                            print(f"Skipping listing {title}: Map image not found or URL empty.")
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue
                        map_img_valid = driver.execute_script(js_check_image, map_image_url, None)

                        if not main_img_valid:
                            print(f"Skipping listing {title}: Main image URL failed validation or is placeholder: {image_url}")
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue
                            
                        if not map_img_valid:
                            print(f"Skipping listing {title}: Map image URL failed validation: {map_image_url}")
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue
                            
                        images_validated = True # Both validated

                        # Close tab and switch back
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        
                        # This redundant check might be removable now 
                        if not map_image_found or not images_validated:
                             print(f"Skipping listing {title} due to missing map or failed validation (redundant check).")
                             continue
                            
                    except Exception as e:
                        print(f"Error during Selenium detail page visit/validation for {title}: {e}")
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                        continue 
                    
                    # --- Store the data --- 
                    listing = {
                        "title": title,
                        "price": price,
                        "location": title,  # Keep using title for now
                        "url": listing_url,  # Use EXTRACTED URL
                        "bedrooms": category["bedrooms"],
                        "image_url": thumbnail_url, # Use EXTRATED URL
                    }
                    
                    all_listings.append(listing)
                    print(f"Added listing: {title}, {category['bedrooms']} bedroom(s), {price}")
                
                except Exception as e:
                    # Catch errors processing a specific container
                    current_url = driver.current_url
                    print(f"Error processing a listing container on {current_url}: {e}")
                    # Optionally add more details about the container causing the error

        except Exception as e:
            print(f"Error processing category {category['url']}: {e}")
    
    driver.quit()
    print(f"\nFound total of {len(all_listings)} valid listings")
    return all_listings


def extract_bedrooms(title):
    """Extract number of bedrooms from title"""
    if not title:
        return None
        
    # First check if bedrooms are directly indicated in the title
    bed_patterns = [
        (r'(\d+)\s+bed', lambda x: int(x)),
        (r'(\d+)-bed', lambda x: int(x)),
        (r'(\d+)\s*br', lambda x: int(x)),
        (r'(\d+)\s*bedroom', lambda x: int(x))
    ]
    
    for pattern, converter in bed_patterns:
        match = re.search(pattern, title.lower())
        if match:
            return converter(match.group(1))
    
    # Direct mapping for categories based on website structure
    for category, beds in BEDROOM_CATEGORIES.items():
        if category.lower() in title.lower():
            return beds
            
    # Try to determine from property_urls mapping
    for bed_count, urls in property_urls.items():
        for url in urls:
            property_name = url.split('/')[-1]
            formatted_name = format_address_from_url(property_name)
            if formatted_name.lower() == title.lower():
                return bed_count
                
    # Extract bedrooms from common address patterns
    # Look for apartment numbers that typically indicate bedroom count
    if "Seminary" in title or "Leroy" in title or "Murray" in title or "Chapin" in title or "Walnut" in title or "Oak" in title or "Vincent" in title or "St John" in title:
        # Check for apartment or unit numbers which often correlate with bedroom count
        apt_pattern = re.search(r'apt\s+(\d+)', title.lower())
        if apt_pattern:
            apt_num = int(apt_pattern.group(1))
            # In many buildings, apt 1 = 1BR, apt 2 = 2BR, apt 3 = 3BR, etc.
            if apt_num <= 7:  # Reasonable bedroom count limit
                return apt_num
                
    # Map specific properties based on common patterns observed in the data
    property_bedroom_map = {
        "38 5 Oak": 2,
        "18 Seminary Apt 2": 2,
        "29 Leroy Apt 6": 2,
        "12 Vincent": 2,
        "13 Seminary": 3,
        "50 Leroy": 3,
        "93 Chapin": 3,
        "104 Chapin": 2,
        "93 Murray": 2,
        "106 Murray": 2,
        "4 Seminary": 1,
        "10 Seminary": 1,
        "14 Seminary": 1,
        "16 Seminary": 1,
        "18 5 Seminary": 1,
        "69 St John": 1,
        "55 St John": 2,
        "56 St John": 2,
        "38 St John": 2,
        "40 St John": 2,
        "40 Walnut": 2,
        "42 Front": 3,
        "5 Ayres": 4,
        "6 Ayres": 4,
        "2 Ayres": 3,
        "3 Ayres": 3,
        "11 Ayres": 3,
        "17 Chapin": 5,
        "25 Seminary": 4,
        "30 Seminary": 4,
        "41 Leroy": 2,
        "43 Leroy": 2,
        "44 Murray": 3,
        "54 Leroy": 3,
        "59 Murray": 3,
        "68 Chapin": 2,
        "74 Oak": 2,
        "7 Walnut": 5,
        "41 Kneeland": 2,
        "53 5 Murray": 2,
        # Adding missing properties from logs
        "10 Seminary Apt 2": 2,
        "10 Seminary Apt 3": 3,
        "14 Seminary Apt 1": 1,
        "14 Seminary Apt 2A": 2,
        "14 Seminary Apt 2Nd Fl": 2,
        "14 Seminary Apt 3Rd Fl": 3,
        "16 Seminary Apt 1F": 1,
        "16 Seminary Apt 1R": 1,
        "16 Seminary Apt 3": 3,
        "18 5 Seminary Apt 1": 1,
        "18 5 Seminary Apt 2": 2,
        "18 Seminary Apt 1": 1,
        "18 Seminary Apt 2": 2,
        "23 Ayres": 3,
        "29 Leroy Apt 4": 2,
        "29 Leroy Apt 6": 2,
        "29 Seminary": 4,
        "3 Ayres": 3,
        "30 Seminary": 4,
        "38 5 Oak": 2,
        "4 Seminary Apt 2": 2,
        "4 Seminary Apt 3": 3,
        "41 Kneeland Apt 1 2": 2,
        "41 Leroy Apt 1": 1, 
        "41 Leroy Apt 2": 2,
        "43 Leroy Apt 1F": 1,
        "43 Leroy Apt 2R": 2,
        "50 Leroy Apt L": 3,
        "50 Leroy Apt R": 3,
        "53 5 Murray Apt 1": 1,
        "53 5 Murray Apt 2": 2,
        "56 St John Apt R": 2,
        "68 Chapin Apt 1L": 1,
        "68 Chapin Apt 2L": 2,
        "69 St John Apt 1": 1,
        "69 St John Apt 2R": 2,
        "74 Oak Apt 1": 1,
        "74 Oak Apt 2 Or 3": 2,
        "93 Chapin Apt L": 3,
        "93 Chapin Apt R": 3,
        "93 Murray Apt 1": 1,
        "93 Murray Apt 2": 2,
        "97 Chapin": 3,
        "160 Seminary Apt 1 Or 2": 2,
    }
    
    # Check for match in specific property map
    for prop_name, bedroom_count in property_bedroom_map.items():
        if prop_name in title:
            return bedroom_count
    
    # Return 1 as a fallback for "Apt 1" patterns if nothing else matched
    if re.search(r'apt\s+1\b', title.lower()):
        return 1
    if re.search(r'apt\s+2\b', title.lower()):
        return 2
    if re.search(r'apt\s+3\b', title.lower()):
        return 3
            
    # Final fallback - return 1 for most small properties as a safe default
    if any(word in title.lower() for word in ["apt", "apartment", "studio"]):
        return 1
        
    # For unknown properties without any bedroom hints, return 2 as a reasonable default
    return 2

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


def main():
    print("Starting scraper...\n")
    try:
        # Truncate table first
        truncate_properties_table()
        # Then ensure table exists
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
