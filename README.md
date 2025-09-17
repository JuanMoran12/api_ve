# Currency Exchange Rate API

A FastAPI-based REST API that provides real-time and historical currency exchange rates, with a focus on USD and EUR to VES (Venezuelan Bolívar). The API also provides bank exchange rate information from various Venezuelan financial institutions.

## 🚀 Features

- Real-time and historical exchange rates for USD and EUR
- Bank exchange rate information from multiple Venezuelan financial institutions
- Clean, RESTful API design
- Built with FastAPI for high performance
- PostgreSQL database for reliable data storage
- Containerized with Docker for easy deployment
- Environment variable configuration
- Comprehensive error handling
- Rate limiting (to be implemented)
- API key authentication (to be implemented)

## 📦 Prerequisites

- Python 3.8+
- PostgreSQL 10.5+
- Docker (optional)
- Docker Compose (optional)

## 🛠️ Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/currency-api.git
   cd currency-api
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```env
   # Database
   DB_HOST=localhost
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=currency_api
   
   # Server
   DEBUG=True
   PORT=8000
   
   # CORS (comma-separated list of allowed origins, or * for all)
   CORS_ORIGINS=*
   ```

5. Initialize the database:
   ```bash
   python -c "from bd import crear_tablas; import mariadb; conn = mariadb.connect(host='localhost', user='your_db_user', password='your_db_password', database='currency_api'); crear_tablas(conn)"
   ```

### Docker Setup

1. Create a `.env` file as shown above

2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

The API will be available at `http://localhost:8000`

## 🚀 API Endpoints

### Exchange Rates

#### Get USD Exchange Rate
```
GET /api/v1/usd
```

**Query Parameters:**
- `fuente` (optional): Data source (default: bcv)
- `fecha` (optional): Date in YYYY-MM-DD format (default: today)

#### Get EUR Exchange Rate
```
GET /api/v1/eur
```

**Query Parameters:**
- `fuente` (optional): Data source (default: bcv)
- `fecha` (optional): Date in YYYY-MM-DD format (default: today)

### Bank Exchange Rates

#### Get Bank Exchange Rates
```
GET /api/v1/tasa
```

**Query Parameters:**
- `fecha` (optional): Date in YYYY-MM-DD format (default: today)
- `banco` (optional): Filter by bank name

## 📝 Response Format

### Successful Response
```json
{
  "success": true,
  "data": {
    "currency": "USD",
    "price": 30.5,
    "date": "2025-09-15",
    "source": "bcv",
    "trend": "increased",
    "difference": 0.5,
    "previous_price": 30.0,
    "previous_date": "2025-09-14"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "not_found",
    "message": "No data found for the specified date",
    "details": "No exchange rate data available for 2025-09-15"
  }
}
```

## 🔒 Authentication (Planned)

The API will implement API key authentication in a future update. All endpoints will require a valid API key.

## 📊 Rate Limiting (Planned)

Rate limiting will be implemented to ensure fair usage of the API:
- Free tier: 100 requests/hour
- Paid tiers: TBD

## 🤝 Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker](https://www.docker.com/)


