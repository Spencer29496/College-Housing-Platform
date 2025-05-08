[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/vfKrPwQS)
# Binghamton Housing

## CS 445 Final Project
### Spring 2025

### Team: Team 13
* Andy Luna
* Sergio Soria
* Spencer Mines

## Getting Started
This project scrapes property data from Amicus Properties website, focusing on 1-bedroom listings for Binghamton University students. It extracts title, pricing, location, and link information and stores it in a PostgreSQL database. The data is then accessible via a RESTful API built with Flask.

### Roadmap
- [ ] Add user authentication for API endpoints
- [ ] Implement a frontend interface to display property data
- [ ] Add filters for additional property features (utilities, amenities, etc.)
- [ ] Implement scheduled scraping to keep data updated
- [ ] Add email notifications for new listings
  
## SRS
https://docs.google.com/document/d/1P_lsExu2DCcdzXVe-p1d0KUV1bhqFS2ONDamPqfjyyM/edit?tab=t.0
  
### Prerequisites
* [Docker](https://www.docker.com/)
* [Docker Compose](https://docs.docker.com/compose/)

### Installing
1. Clone the repository
```
git clone <repository-url>
cd <repository-directory>
```

2. Build and start the Docker containers
```
docker-compose up -d
```

3. The API will be available at http://localhost:8000
4. You can also access the database admin interface at http://localhost:8080

### API Endpoints
- `GET /properties` - Get all properties
- `GET /properties?bedrooms=1` - Get properties filtered by number of bedrooms
- `GET /properties/<id>` - Get a specific property by ID
- `POST /refresh` - Trigger a new data scrape to refresh the database

## Running manually
To run the scraper manually:
```
docker exec -it <container_id> python run_scraper.py
```

## Built With
* [Flask](https://flask.palletsprojects.com/) - Web framework
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
* [Requests](https://docs.python-requests.org/) - HTTP requests
* [PostgreSQL](https://www.postgresql.org/) - Database
* [Psycopg2](https://www.psycopg.org/) - PostgreSQL adapter for Python
* [Docker](https://www.docker.com/) - Containerization

## License
This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details

MIT License

Copyright (c) 2025 Binghamton Housing - Team 13 by Andy Luna, Sergio Soria, and Spencer Mines

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


## Acknowledgments
* Amicus Properties for providing housing options for students
* Binghamton University Housing Resources
