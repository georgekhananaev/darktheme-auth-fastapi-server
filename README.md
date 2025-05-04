darktheme-auth-fastapi-server
=============================

darktheme-auth-fastapi-server is a robust and versatile template FastAPI server, designed to be easily integrated into any backend project. It provides a secure, scalable, and efficient framework that simplifies the process of setting up and maintaining API services. This template includes essential features such as authentication-protected endpoints, optional caching with Redis, comprehensive logging, and a custom dark theme for API documentation, offering both aesthetics and functionality.

By leveraging this template, you can focus on developing your unique application features without worrying about the underlying infrastructure. The custom dark theme for the documentation not only enhances the visual appeal but also ensures a consistent and professional look across your development and production environments. For those who dislike the strain of staring at a bright white screen all day, this dark-themed documentation provides a much-needed visual relief, making the development process more comfortable and enjoyable.

--------

- **Authentication & Security**: Includes token-based authentication for securing API endpoints and HTTP Basic authentication for accessing documentation.
- **Protected Documentation**: Custom dark-themed Swagger UI and ReDoc documentation, accessible only after authentication.
- **Optional Redis Caching**: Utilizes Redis for caching to improve performance and reduce load on backend services. Can be disabled for simpler deployments.
- **SQLite Log Storage**: Efficient logging system using SQLite database for storage and retrieval, with API endpoints for access.
- **Log Viewer API**: Access logs through the API with filtering, pagination and search capabilities.
- **Comprehensive Test Suite**: Includes unit tests, API tests, benchmark tests, and stability tests.
- **Environment Configuration**: Uses environment variables for configuration, ensuring sensitive information is kept secure.
- **YAML Configuration**: Uses a config.yaml file for application settings, making it easy to customize the server behavior.

Getting Started
---------------

### Prerequisites

- **Docker** and **Docker Compose**: To run the application and Redis server in containers.
- **Python 3.13.3**: The application runs on Python 3.13.3 (slim).
- **pip-tools**: For managing dependencies (optional).

### Installation

#### Using Docker (Recommended)

1. **Clone the repository:**

   ```
   git clone https://github.com/georgekhananaev/darktheme-auth-fastapi-server.git
   cd darktheme-auth-fastapi-server
   ```

2. **Create a `.env` file** with the necessary environment variables:

   ```
   BEARER_SECRET_KEY=your_secret_key
   FASTAPI_UI_USERNAME=your_ui_username
   FASTAPI_UI_PASSWORD=your_ui_password
   ```

3. **Customize `config.yaml`** (optional):

   The `config.yaml` file contains various configuration options for the server. You can modify it to suit your needs:

   ```yaml
   # Redis Configuration
   redis:
     enabled: true  # Set to false to disable Redis
     hosts:
       - localhost
       - redis
       - 0.0.0.0
     port: 6379
   ```

4. **Build and start the Docker containers:**

   With Redis enabled (default):
   ```bash
   docker-compose --profile redis up --build
   ```

   Without Redis:
   ```bash
   docker-compose up --build
   ```

   This command builds the Docker images and starts the containers for the application and optionally Redis.

   ![accessibility text](/screenshots/running_server.png)

#### Running Locally

1. **Clone the repository:**

   ```
   git clone https://github.com/georgekhananaev/darktheme-auth-fastapi-server.git
   cd darktheme-auth-fastapi-server
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** with the necessary environment variables:

   ```
   BEARER_SECRET_KEY=your_secret_key
   FASTAPI_UI_USERNAME=your_ui_username
   FASTAPI_UI_PASSWORD=your_ui_password
   ```

4. **Customize `config.yaml`** (optional):

   If running locally without Redis, set `enabled: false` in the Redis section of the config.yaml file:

   ```yaml
   # Redis Configuration
   redis:
     enabled: false
   ```

5. **Run the server:**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

Usage
-----

- **Access the API**: The FastAPI server runs on `http://localhost:8000`. You can use tools like `curl` or Postman to interact with the API endpoints.

- **Documentation**: The API documentation is available at:
    - Swagger UI: `http://localhost:8000/docs`
    - ReDoc: `http://localhost:8000/redoc`

  These pages require HTTP Basic authentication using the username and password set in the `.env` file.

- **Log Access API**: Access application logs via the API:
    - Get log counts: `GET /api/v1/logs/counts`
    - Access logs: `GET /api/v1/logs/access`
    - Security logs: `GET /api/v1/logs/security`
    - System logs: `GET /api/v1/logs/system`

  All log endpoints support query parameters for filtering:
  - `limit`: Maximum number of logs to return (default: 100)
  - `offset`: Number of logs to skip (pagination)
  - `level`: Filter by log level (INFO, WARNING, ERROR, etc.)
  - `start_date`: Filter logs after this date (YYYY-MM-DD)
  - `end_date`: Filter logs before this date (YYYY-MM-DD)
  - `search`: Search term in log messages

Project Structure
-----------------

- **`main.py`**: The main entry point for the FastAPI application.
- **`config.yaml`**: Configuration file for the application settings.
- **`db/`**: Contains database clients (Redis and SQLite).
- **`auth/`**: Includes authentication-related functions and security settings.
- **`routers/`**: Contains route definitions and API logic.
- **`modules/`**: Houses shared modules like logging utilities, middleware, and configuration handling.
- **`logs/`**: Directory where logs and log database are stored.
- **`tests/`**: Comprehensive test suite including unit, API, benchmark, and stability tests.

Testing
-------

The application includes a comprehensive test suite to verify functionality, performance, and stability:

### Running Tests

```bash
# Run the test runner script
./tests/run_tests.py [unit|api|benchmark|stability|all]

# Options:
# -v, --verbose: Show verbose output
# --junit: Generate JUnit XML reports
# --report-dir DIR: Specify report directory (default: test_reports)
```

### Test Categories

- **Unit Tests**: Test individual components and functions.
- **API Tests**: Test API endpoints and integration.
- **Benchmark Tests**: Measure performance metrics of endpoints.
- **Stability Tests**: Test application behavior under prolonged load.

### Test Reports

Tests generate detailed reports including:
- Response time histograms
- Percentile distributions
- Performance summaries
- Memory usage tracking

Logging System
-------------

The application implements a robust logging system that stores logs in both a SQLite database and provides API access:

- **Log Types**:
  - **Access Logs**: Track API usage and HTTP requests
  - **Security Logs**: Track authentication attempts and security events
  - **System Logs**: Track application lifecycle and system events

- **SQLite Storage**: All logs are stored in a SQLite database in the logs directory
- **API Access**: Logs can be queried through the API with filtering and pagination

Customization
-------------

- **Dark Theme for Docs**: The Swagger UI documentation uses a custom dark theme located in the `/static` directory. You can customize this by modifying the CSS files.

- **Environment Variables**: Modify the `.env` file to change the application's configuration, such as security keys and credentials.

- **Configuration**: The `config.yaml` file allows you to customize various aspects of the server. A sample configuration file with detailed comments is provided as `config.sample.yaml`.

### Configuration Reference

The `config.yaml` file consists of several sections that control different aspects of the server:

#### Server Configuration

```yaml
server:
  title: "Dark Theme FastAPI Server"  # Application title
  version: "v1.0.0"                   # API version
  description: "API server..."        # Application description
  host: "0.0.0.0"                     # Host address to bind to
  port: 8000                          # Port to listen on
  reload: true                        # Enable auto-reload for development
```

#### Redis Configuration

```yaml
redis:
  enabled: false                      # Enable/disable Redis functionality
  hosts:                              # List of possible Redis hosts to try
    - localhost
    - redis                           # Docker service name
    - 0.0.0.0
  port: 6379                          # Redis port
  db: 0                               # Redis database number
  decode_responses: true              # Automatically decode responses
  timeout: 5                          # Connection timeout in seconds
```

#### CORS Configuration

```yaml
cors:
  origins:                            # Allowed origins for CORS
    - "*"                             # Allow any origin (not recommended for production)
    - "http://localhost"
    - "http://localhost:3000"
  allow_credentials: true             # Allow credentials (cookies, auth headers)
  allow_methods:                      # Allowed HTTP methods
    - "GET"
    - "POST"
    - "PUT"
    - "PATCH"
    - "DELETE"
  allow_headers:                      # Allowed HTTP headers
    - "*"                             # Allow all headers
  expose_headers:                     # Headers exposed to the browser
    - "Content-Disposition"
```

#### API Configuration

```yaml
api:
  prefix: "/api/v1"                   # API route prefix for all endpoints
  rate_limit:                         # Rate limiting settings
    enabled: true
    limit: 100                        # Requests per minute
    window_seconds: 60
```

#### Logging Configuration

```yaml
logging:
  directory: "./logs"                 # Root directory for log files/database
  max_records: 10000                  # Max records for query pagination
  use_sqlite: true                    # Enable SQLite database logging
  sqlite_db: "app_logs.db"            # SQLite database filename
  
  # Access log configuration (HTTP requests)
  access:
    enabled: true
    level: "INFO"                     # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: "[%(asctime)s] [%(levelname)s] [%(client_ip)s] [%(username)s] %(message)s"
    retention_days: 30                # How long to keep logs
  
  # Security log configuration
  security:
    enabled: true
    level: "INFO"
    format: "[%(asctime)s] [%(levelname)s] [%(client_ip)s] [%(username)s] %(message)s"
    retention_days: 90                # Keep security logs longer
  
  # System log configuration
  system:
    enabled: true
    level: "INFO"
    format: "[%(asctime)s] [%(levelname)s] [%(module)s] [%(funcName)s] %(message)s"
    retention_days: 15
```

#### Documentation Configuration

```yaml
docs:
  enabled: true                       # Enable/disable API documentation
  dark_theme: true                    # Use dark theme for documentation
  title: "Dark Theme FastAPI API"     # Documentation title
  custom_css: "swagger_ui_dark.min.css" # Custom CSS file
  swagger_path: "/docs"               # Documentation route paths
  redoc_path: "/redoc"
```

#### Security Configuration

```yaml
security:
  https:
    enabled: false                    # Enable for production
    cert_file: "./certs/server.crt"
    key_file: "./certs/server.key"
  
  api_key:
    enabled: false
    header_name: "X-API-Key"
    # Actual keys should be stored in environment variables
```

### Configuration Tips

1. **Development vs. Production**:
   - For development, set `server.reload: true` and `redis.enabled: false`
   - For production, disable auto-reload and consider enabling Redis for better performance

2. **Security Best Practices**:
   - In production, set `cors.origins` to specific domains, not `"*"`
   - Enable HTTPS in production by setting `security.https.enabled: true`
   - Store sensitive data in environment variables, not in the config file

3. **Performance Tuning**:
   - Adjust `logging.max_records` based on your application's logging volume
   - Set appropriate `logging.retention_days` to manage storage growth
   - Configure Redis connection pooling according to your load requirements

Contributing
------------

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

License
-------

This project is licensed under the MIT License. See the LICENSE file for details.