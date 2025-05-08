# College Housing Platform

## Overview
The College Housing Platform is designed to help students find suitable housing options near their college campus. This platform provides a user-friendly interface to browse, search, and filter housing listings, making it easier for students to find their ideal living arrangements.

## Features
- Property listings with detailed information
- Search and filter capabilities
- User authentication system
- Scraper to collect housing data
- Mobile-responsive design

## Technology Stack
* **Backend**: Flask (Python)
* **Database**: PostgreSQL
* **Frontend**: HTML, CSS, JavaScript
* **Containerization**: Docker
* **Data Collection**: BeautifulSoup4, Requests

## Getting Started

### Prerequisites
* [Docker](https://www.docker.com/)
* [Docker Compose](https://docs.docker.com/compose/)

### Installation
1. Clone the repository
```
git clone https://github.com/Spencer29496/College-Housing-Platform.git
cd College-Housing-Platform
```

2. Build and start the Docker containers
```
docker-compose up -d
```

3. Access the application
   - Web interface: http://localhost:5000
   - API: http://localhost:5000/api
   - Database admin: http://localhost:8080

## API Endpoints
- `GET /properties` - Get all properties
- `GET /properties?bedrooms=1` - Filter properties by number of bedrooms
- `GET /properties/<id>` - Get a specific property by ID
- `POST /refresh` - Trigger a new data scrape to refresh the database

## Development

### Running Locally Without Docker
1. Create and activate a virtual environment
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies
```
pip install -r requirements.txt
```

3. Run the application
```
python app.py
```

## License
This project is licensed under the MIT License - see the [LICENSE.txt](./LICENSE.txt) file for details.

## Contributors
* Spencer Mines
