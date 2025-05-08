# configuration.py

DB_PARAMS = {
    'host': 'database',  # Using container name in Docker network
    'database': 'test_db',
    'user': 'postgres',
    'password': 'team13'
}

BASE_URL = 'https://www.binghamtonwest.com'
TARGET_URL = f'{BASE_URL}/school/binghamton-university'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
