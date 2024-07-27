
darktheme-auth-fastapi-server
=============================

darktheme-auth-fastapi-server is a robust and versatile template FastAPI server, designed to be easily integrated into any backend project. It provides a secure, scalable, and efficient framework that simplifies the process of setting up and maintaining API services. This template includes essential features such as authentication-protected endpoints, caching with Redis, comprehensive logging, and a custom dark theme for API documentation, offering both aesthetics and functionality.

By leveraging this template, you can focus on developing your unique application features without worrying about the underlying infrastructure. The custom dark theme for the documentation not only enhances the visual appeal but also ensures a consistent and professional look across your development and production environments. For those who dislike the strain of staring at a bright white screen all day, this dark-themed documentation provides a much-needed visual relief, making the development process more comfortable and enjoyable.

--------

- **Authentication & Security**: Includes token-based authentication for securing API endpoints and HTTP Basic authentication for accessing documentation.
- **Protected Documentation**: Custom dark-themed Swagger UI and ReDoc documentation, accessible only after authentication.
- **Redis Caching**: Utilizes Redis for caching to improve performance and reduce load on backend services.
- **Comprehensive Logging**: Implements logging to monitor and troubleshoot application behavior.
- **Environment Configuration**: Uses environment variables for configuration, ensuring sensitive information is kept secure.

Getting Started
---------------

### Prerequisites

- **Docker** and **Docker Compose**: To run the application and Redis server in containers.
- **Python 3.12.4**: The application runs on Python 3.12.4 (slim).

### Installation

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

3. **Build and start the Docker containers:**

   ```bash
   docker-compose up --build
   ```

   This command builds the Docker images and starts the containers for the application and Redis.

   ![accessibility text](/screenshots/running_server.png)


Usage
-----

- **Access the API**: The FastAPI server runs on `http://localhost:8000`. You can use tools like `curl` or Postman to interact with the API endpoints.

- **Documentation**: The API documentation is available at:
    - Swagger UI: `http://localhost:8000/docs`
    - ReDoc: `http://localhost:8000/redoc`

  These pages require HTTP Basic authentication using the username and password set in the `.env` file.

Project Structure
-----------------

- **`main.py`**: The main entry point for the FastAPI application.
- **`db/`**: Contains the Redis client configuration.
- **`auth/`**: Includes authentication-related functions and security settings.
- **`routers/`**: Contains route definitions and API logic.
- **`components/`**: Houses shared components like logging utilities.
- **`logs/`**: Directory where logs are stored.

Customization
-------------

- **Dark Theme for Docs**: The Swagger UI documentation uses a custom dark theme located in the `/static` directory. You can customize this by modifying the CSS files.

- **Environment Variables**: Modify the `.env` file to change the application's configuration, such as security keys and credentials.

Contributing
------------

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

License
-------

This project is licensed under the MIT License. See the LICENSE file for details.

Contact
-------

For more information, please contact the project maintainers at `george.khananaev+github@gmail.com`.

Logs
-------
![accessibility text](/screenshots/logs.png)


Other Screenshots
-------
![hover text](/screenshots/protected_docs.png)
![accessibility text](/screenshots/docs.png)
![accessibility text](/screenshots/response.png)