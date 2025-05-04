darktheme-auth-fastapi-server
=============================

darktheme-auth-fastapi-server is a robust and versatile template FastAPI server, designed to be easily integrated into any backend project. It provides a secure, scalable, and efficient framework that simplifies the process of setting up and maintaining API services. This template includes essential features such as authentication-protected endpoints, optional caching with Redis, comprehensive logging, and a custom dark theme for API documentation, offering both aesthetics and functionality.

By leveraging this template, you can focus on developing your unique application features without worrying about the underlying infrastructure. The custom dark theme for the documentation not only enhances the visual appeal but also ensures a consistent and professional look across your development and production environments. For those who dislike the strain of staring at a bright white screen all day, this dark-themed documentation provides a much-needed visual relief, making the development process more comfortable and enjoyable.

## Screenshots

<p align="center">
  <img src="/screenshots/swagger-ui-docs.png" alt="Dark Theme Swagger UI" width="900">
  <br><em>Dark Theme Swagger UI Documentation</em>
</p>

<table>
  <tr>
    <td width="50%"><img src="/screenshots/running_server.png" alt="Running Server" width="100%"><br><em>Server running in terminal</em></td>
    <td width="50%"><img src="/screenshots/docs-protected.png" alt="Protected Documentation" width="100%"><br><em>Authentication-protected documentation</em></td>
  </tr>
  <tr>
    <td width="50%"><img src="/screenshots/access-with-api-key.png" alt="API Key Authentication" width="100%"><br><em>API key authentication</em></td>
    <td width="50%"><img src="/screenshots/logs-db-stracture.png" alt="Logs Database Structure" width="100%"><br><em>SQLite logs database structure</em></td>
  </tr>
</table>

--------

- **Authentication & Security**: Includes token-based authentication for securing API endpoints and HTTP Basic authentication for accessing documentation.
- **Multiple Authentication Methods**: Support for Bearer tokens and API key authentication, with configuration options for each.
- **Enhanced HTTP Security**: Offers HTTP disabling, HTTP-to-HTTPS redirection, and Let's Encrypt integration for comprehensive security.
- **Protected Documentation**: Custom dark-themed Swagger UI and ReDoc documentation, accessible only after authentication.
- **Optional Redis Caching**: Utilizes Redis for caching to improve performance and reduce load on backend services. Can be disabled for simpler deployments.
- **SQLite Log Storage**: Efficient logging system using SQLite database for storage and retrieval, with API endpoints for access.
- **Log Viewer API**: Access logs through the API with filtering, pagination and search capabilities.
- **Let's Encrypt Integration**: Built-in support for Let's Encrypt, providing automatic SSL/TLS certificate issuance and renewal.
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

Authentication System
-------------------

The application supports multiple authentication methods to provide flexible security options:

### Authentication Methods

1. **Bearer Token Authentication**: 
   - JWT-based authentication for API endpoints
   - Configured with the `BEARER_SECRET_KEY` environment variable
   - Default option for securing all API endpoints

2. **API Key Authentication**:
   - Simple API key-based authentication as an alternative to tokens
   - Configured through `API_KEY` environment variable and enabled in config.yaml
   - API keys are passed in the HTTP header specified in configuration (default: `X-API-Key`)

3. **HTTP Basic Authentication**:
   - Used for accessing documentation (Swagger UI and ReDoc)
   - Configured with `FASTAPI_UI_USERNAME` and `FASTAPI_UI_PASSWORD` environment variables

### Configuration

The `config.yaml` file determines whether API key authentication is enabled:

```yaml
security:
  api_key:
    enabled: true                    # Set to false to disable API key authentication
    header_name: "X-API-Key"         # Customize the header name if needed
```

API keys and bearer tokens are stored in environment variables:

```
BEARER_SECRET_KEY=your_secret_key
API_KEY=your_api_key
```

### Authentication Flow

1. **Request Processing**:
   - Middleware examines incoming requests for authentication credentials
   - Checks for Bearer token in Authorization header
   - If API key authentication is enabled, checks for API key in configured header

2. **Multiple Authentication Options**:
   - Endpoints can be configured to accept either Bearer token or API key
   - If both are provided, Bearer token takes precedence
   - Authentication methods can be selected based on security requirements

### Testing Authentication

The test suite includes comprehensive tests for both authentication methods:

1. **Configuration-Aware Tests**:
   - Tests automatically adapt based on the API key configuration
   - If API keys are disabled in config.yaml, API key tests are skipped
   - Bearer token tests always run since that authentication is always available

2. **Auth Client Fixtures**:
   - `auth_client`: A test client with a pre-configured Bearer token
   - `api_key_client`: A test client with a pre-configured API key

3. **Authentication Override**:
   - Tests use a special fixture to override authentication during testing
   - This allows testing without requiring real secrets or tokens

Project Structure
-----------------

- **`main.py`**: The main entry point for the FastAPI application.
- **`config.yaml`**: Configuration file for the application settings.
- **`db/`**: Contains database clients (Redis and SQLite).
- **`auth/`**: Includes authentication-related functions and security settings.
  - **`fastapi_auth.py`**: Core authentication functionality for Bearer tokens and API keys.
- **`routers/`**: Contains route definitions and API logic.
  - **`certificates.py`**: Let's Encrypt certificate management endpoints.
  - **`logs.py`**: Log access and retrieval endpoints.
  - **`system.py`**: System health and information endpoints.
- **`modules/`**: Houses shared modules like logging utilities, middleware, and configuration handling.
  - **`certificate_manager.py`**: Let's Encrypt certificate management module.
  - **`config.py`**: Configuration handling module.
  - **`logger.py`**: Logging utilities.
  - **`middleware.py`**: FastAPI middleware components.
- **`certs/`**: Directory where SSL/TLS certificates are stored.
- **`logs/`**: Directory where logs and log database are stored.
- **`tests/`**: Comprehensive test suite including unit, API, benchmark, and stability tests.
  - **`api/`**: Tests for API endpoints and authentication.
  - **`benchmark/`**: Performance testing for API endpoints.
  - **`stability/`**: Long-running stability tests.
  - **`unit/`**: Unit tests for individual modules.

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

You can also run tests using pytest directly:

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/api/  # API tests
python -m pytest tests/unit/  # Unit tests

# Run specific test files
python -m pytest tests/api/test_logs_router.py

# Run with verbose output
python -m pytest -v
```

### Testing Prerequisites

Before running tests, ensure the following:

1. **API Key Authentication**: For API tests, API key authentication should be disabled in config.yaml:
   ```yaml
   security:
     api_key:
       enabled: false
   ```

2. **Benchmark and Stability Tests**: For these tests, the API server must be running:
   ```bash
   # Start server in one terminal
   uvicorn main:app --host 0.0.0.0 --port 8000
   
   # Then run tests in another terminal
   python -m pytest tests/benchmark/
   python -m pytest tests/stability/
   ```

### Test Categories

- **Unit Tests**: Test individual components and functions.
  - Located in `tests/unit/`
  - Focus on specific functionality of modules
  - Mock external dependencies for isolation

- **API Tests**: Test API endpoints and integration.
  - Located in `tests/api/`
  - Test authentication, error handling, and data processing
  - Configuration-aware tests that respect settings in config.yaml
  - Includes tests for HTTP security, logs, certificates, and system information
  
- **Benchmark Tests**: Measure performance metrics of endpoints.
  - Located in `tests/benchmark/`
  - **Require a running server instance on localhost:8000**
  - Measure response times, throughput, and error rates
  - Generate performance reports
  - Must be run separately after starting the server

- **Stability Tests**: Test application behavior under prolonged load.
  - Located in `tests/stability/`
  - **Require a running server instance on localhost:8000**
  - Run long-duration tests to identify memory leaks or performance degradation
  - Simulate realistic usage patterns
  - Must be run separately after starting the server

### Test Design Features

1. **Configuration-Aware Testing**:
   - Tests automatically adapt based on configuration settings
   - Skip tests for features that are disabled (e.g., API key authentication)
   - Verify that disabled features are actually inaccessible

2. **Custom Test Fixtures**:
   - `auth_client`: Pre-authenticated test client with Bearer token
   - `api_key_client`: Test client using API key authentication
   - `client_with_http_disabled`: Test client for HTTP disabled tests
   - `mock_redis`: Mock Redis client for testing without a real Redis server
   - `mock_logger`: Mock logging functionality for test isolation

3. **Advanced Mocking**:
   - Mock asynchronous functions properly
   - Simulate errors and edge cases
   - Provide controlled test environments for reproducible results

4. **Direct Test Endpoints**:
   - Custom endpoints in test app to bypass routers for more reliable testing
   - Avoid reliance on mock assertions which can be brittle
   - Test actual behavior rather than implementation details

### Test Reports

Tests generate detailed reports including:
- Response time histograms
- Percentile distributions
- Performance summaries
- Memory usage tracking
- Error logs and tracebacks

Logging System
-------------

The application implements a robust logging system that stores logs in both a SQLite database and provides API access:

- **Log Types**:
  - **Access Logs**: Track API usage and HTTP requests
  - **Security Logs**: Track authentication attempts and security events
  - **System Logs**: Track application lifecycle and system events

- **SQLite Storage**: All logs are stored in a SQLite database in the logs directory
- **API Access**: Logs can be queried through the API with filtering and pagination

Enhanced HTTP Security
-----------------

The application offers multiple ways to enhance HTTP security:

- **HTTP Disabling**: You can completely disable HTTP, allowing only HTTPS connections
- **HTTP to HTTPS Redirection**: Automatically redirect HTTP requests to HTTPS
- **Let's Encrypt Integration**: Automate SSL/TLS certificate issuance and renewal
- **Flexible Configuration**: Configure security settings via config.yaml
- **Testing Support**: Comprehensive test suite for all security features

### HTTP Security Configuration

1. **Disable HTTP Entirely** (maximum security):
   ```yaml
   security:
     http:
       enabled: false  # Disable HTTP entirely
     https:
       enabled: true   # HTTPS must be enabled when HTTP is disabled
   ```

2. **Redirect HTTP to HTTPS** (user-friendly):
   ```yaml
   security:
     http:
       enabled: true   # Keep HTTP enabled for redirection
     https:
       enabled: true
       redirect_http: true  # Redirect all HTTP requests to HTTPS
   ```

3. **HTTP and HTTPS Side-by-Side**:
   ```yaml
   security:
     http:
       enabled: true
     https:
       enabled: true
       redirect_http: false  # No redirection
   ```

### HTTP Security Implementation Details

HTTP security is implemented through FastAPI middleware components:

1. **HTTPDisableMiddleware**: Completely blocks HTTP requests when HTTP is disabled
   - Checks the X-Forwarded-Proto header to determine if the request is HTTP or HTTPS
   - Returns a 400 Bad Request response for HTTP requests when HTTP is disabled
   - Configuration-driven through the config.yaml file

2. **HTTPSRedirectMiddleware**: Redirects HTTP requests to HTTPS when redirection is enabled
   - Preserves the original request path and query parameters
   - Returns a 307 Temporary Redirect response with the HTTPS URL
   - Only active when both HTTP and HTTPS are enabled, and redirect_http is true

### Testing HTTP Security

The application includes comprehensive tests for HTTP security features:

1. **Middleware Tests**: Verify that middleware components correctly handle requests
   - Test HTTP disabling when configured
   - Test HTTP to HTTPS redirection when enabled
   - Test proper handling of HTTP requests when allowed

2. **Configuration-Aware Tests**: Tests are designed to respect the current configuration
   - Tests adapt to whether HTTP disabling is enabled or not
   - Tests check for appropriate status codes based on configuration

3. **Certificate Management Tests**: Verify Let's Encrypt certificate functionality
   - Test certificate issuance, renewal, and status checking
   - Mock Let's Encrypt services to avoid real API calls during testing

Let's Encrypt Integration
------------------------

The application includes built-in support for Let's Encrypt, providing automatic SSL/TLS certificate issuance and renewal:

- **Easy Configuration**: Enable Let's Encrypt via config.yaml
- **Automatic Renewal**: Certificates are automatically renewed before expiry
- **API Endpoints**: Manage certificates through API endpoints
- **No External Dependencies**: All certificate management is handled internally

### Let's Encrypt Configuration

To enable Let's Encrypt:

1. Update the `config.yaml` file:

```yaml
security:
  https:
    enabled: true                     # Must be true to enable HTTPS
    mode: "letsencrypt"               # Set mode to "letsencrypt"
  
  letsencrypt:
    enabled: true                     # Enable Let's Encrypt
    email: "your-email@example.com"   # Required for registration
    domains:                          # List of domains to secure
      - "yourdomain.com"
      - "www.yourdomain.com"
    staging: true                     # Use staging server for testing (set to false for production)
    cert_dir: "./certs"               # Directory to store certificates
    challenge_type: "http-01"         # HTTP-01 validation method
    auto_renew: true                  # Enable automatic renewal
    renew_before_days: 30             # Renew certificates 30 days before expiry
```

2. Start the server with `run_local.sh` or Docker Compose.

3. Use the certificate management API endpoints for manual operations:

   - Get certificate info: `GET /api/v1/certificates/info`
   - Issue new certificate: `POST /api/v1/certificates/issue`
   - Renew certificate: `POST /api/v1/certificates/renew`
   - Check certificate status: `GET /api/v1/certificates/status`

### Certificate Management Workflow

1. **First Run**: If Let's Encrypt is enabled but no certificates exist, the server will start without HTTPS.
2. **Certificate Issuance**: Issue a certificate using the API endpoint.
3. **Restart**: After certificate issuance, restart the server to enable HTTPS.
4. **Automatic Renewal**: The server will automatically renew certificates before they expire.

### How It Works

The certificate management module (`modules/certificate_manager.py`) handles the entire lifecycle of SSL/TLS certificates:

1. **Initialization**: When the server starts, it checks for existing certificates and initializes the certificate manager.
2. **Automatic Scheduler**: Uses APScheduler to create a background task for certificate renewal checks.
3. **Certificate Issuance**: When requested, it obtains new certificates from Let's Encrypt via ACME protocol.
4. **Certificate Storage**: Stores certificates and private keys securely in the configured directory.
5. **Renewal Checks**: Periodically checks certificate expiration dates and automatically renews when needed.
6. **Challenge Handling**: Supports HTTP-01 challenges for domain validation.

### Configuring DNS Challenges

By default, the system uses HTTP-01 challenges for domain validation. For wildcard certificates or domains behind firewalls, you can use DNS-01 challenges:

```yaml
letsencrypt:
  challenge_type: "dns-01"
  dns_provider: "cloudflare"  # Supported: cloudflare, route53, etc.
  dns_credentials:
    api_token: "your_api_token"  # Store this in environment variables instead
```

### Testing in Local Environments

For local testing without a public domain, you can:

1. Use the Let's Encrypt staging environment (`staging: true`)
2. Use a tool like ngrok to expose your local server publicly
3. Configure the domains in your config.yaml to match your ngrok URL

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
  http:
    enabled: true                      # Enable HTTP (set to false to disable HTTP entirely)
  
  https:
    enabled: false                     # Enable for production
    mode: "custom"                     # Options: "custom", "letsencrypt"
    cert_file: "./certs/server.crt"    # Used when mode is "custom"
    key_file: "./certs/server.key"     # Used when mode is "custom"
    redirect_http: false               # Redirect HTTP to HTTPS (when both HTTP and HTTPS are enabled)
  
  letsencrypt:
    enabled: false                     # Enable Let's Encrypt certificates
    email: ""                          # Required for Let's Encrypt registration
    domains: []                        # List of domains for the certificate
    staging: true                      # Use staging server for testing (set to false for production)
    cert_dir: "./certs"                # Directory to store certificates
    challenge_type: "http-01"          # Challenge type (http-01 or dns-01)
    auto_renew: true                   # Enable automatic certificate renewal
    renew_before_days: 30              # Number of days before expiry to renew
  
  api_key:
    enabled: false                     # Set to true to enable API key authentication
    header_name: "X-API-Key"           # The HTTP header name to use for API key
    # Actual keys should be stored in environment variables (.env file)
    # Add API_KEY=your_api_key_here to your .env file
```

### Configuration Tips

1. **Development vs. Production**:
   - For development, set `server.reload: true` and `redis.enabled: false`
   - For production, disable auto-reload and consider enabling Redis for better performance

2. **Security Best Practices**:
   - In production, set `cors.origins` to specific domains, not `"*"`
   - Enable HTTPS in production by setting `security.https.enabled: true`
   - Store sensitive data in environment variables, not in the config file
   - You can selectively enable API key authentication with `security.api_key.enabled: true`
   - Different endpoints can use different authentication methods:
     - Bearer token only
     - API key only
     - Either Bearer token or API key
     - No authentication
   - For maximum security in production, disable HTTP entirely and use HTTPS only:
     ```yaml
     security:
       http:
         enabled: false  # Disable HTTP entirely
       https:
         enabled: true
         mode: "custom"  # or "letsencrypt"
     ```
   - Alternatively, enable automatic HTTP to HTTPS redirection:
     ```yaml
     security:
       http:
         enabled: true  # Allow HTTP for redirection
       https:
         enabled: true
         redirect_http: true  # Redirect HTTP to HTTPS
     ```
   - For production, consider using Let's Encrypt for free, automated SSL certificates by setting:
     ```yaml
     security:
       https:
         enabled: true
         mode: "letsencrypt"
       letsencrypt:
         enabled: true
         email: "your-email@example.com"  # Required for Let's Encrypt
         domains:
           - "example.com"
           - "www.example.com"
         staging: false  # Set to false for production certificates
     ```

3. **Performance Tuning**:
   - Adjust `logging.max_records` based on your application's logging volume
   - Set appropriate `logging.retention_days` to manage storage growth
   - Configure Redis connection pooling according to your load requirements

Contributing
------------

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

### Recent Improvements

- Fixed FastAPI test fixtures to handle authentication correctly
- Added configuration-aware tests that respect settings in config.yaml
- Enhanced Let's Encrypt certificate management with robust testing
- Fixed HTTP security tests and middleware implementation
- Improved API endpoint testing with direct test endpoints instead of mocked calls
- Fixed JSON boolean values in test fixtures (using Python True instead of JSON true)
- Added comprehensive documentation for all security features
- Enhanced test suite with better async mocking strategies
- Updated testing documentation to clarify that API key authentication should be disabled during testing
- Added instructions for running benchmark and stability tests with a running server

License
-------

This project is licensed under the MIT License. See the LICENSE file for details.