from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBasicCredentials
from starlette.config import Config as StarletteConfig
from fastapi.middleware.cors import CORSMiddleware
from auth.fastapi_auth import verify_credentials, get_secret_key
from modules.logger import log_system, logger
from modules.static_files import mount_static_files
from modules.middleware import LoggingMiddleware, HTTPSRedirectMiddleware, HTTPDisableMiddleware
from modules.config import config
from modules.certificate_manager import certificate_manager
from routers import system, logs, certificates
from db.clientRedis import AsyncRedisClient
from db.clientSQLite import AsyncSQLiteClient
from contextlib import asynccontextmanager


class CustomFastAPI(FastAPI):
    """
    A custom FastAPI class that holds additional application state.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = config.get_server_title()  # Title of the application
        self.redis_client = None  # Placeholder for Redis client instance
        self.sqlite_client = None  # Placeholder for SQLite client instance


@asynccontextmanager
async def lifespan(myapp: CustomFastAPI):
    """
    Lifespan context manager for managing startup and shutdown events.
    This is where we initialize and clean up resources like the Redis client and SQLite logger.
    """
    # Log application startup
    log_system("Application starting", level="INFO")
    
    # Initialize SQLite client for logging
    try:
        myapp.sqlite_client = await AsyncSQLiteClient.get_instance()
        await myapp.sqlite_client.setup()
        await logger.setup_sqlite_handlers()
        log_system("SQLite logging initialized successfully", level="INFO")
    except Exception as e:
        log_system(f"Error initializing SQLite logging: {e}", level="ERROR")
        myapp.sqlite_client = None
    
    # Only initialize Redis if enabled in config
    if config.is_redis_enabled():
        try:
            myapp.redis_client = await AsyncRedisClient.get_instance()
            log_system("Redis client initialized successfully", level="INFO")
        except Exception as e:
            log_system(f"Error initializing Redis client: {e}", level="ERROR")
            myapp.redis_client = None
    else:
        log_system("Redis is disabled in configuration", level="INFO")
    
    # Initialize certificate manager for Let's Encrypt if enabled
    if config.is_letsencrypt_enabled():
        log_system("Let's Encrypt is enabled, initializing certificate manager", level="INFO")
        try:
            # Start certificate manager with automatic renewal
            await certificate_manager.start()
            log_system("Certificate manager started successfully", level="INFO")
        except Exception as e:
            log_system(f"Error starting certificate manager: {e}", level="ERROR")
    else:
        log_system("Let's Encrypt is disabled, skipping certificate manager initialization", level="INFO")
    
    try:
        yield
    except Exception as e:
        log_system(f"Error during application lifecycle: {e}", level="ERROR")
    finally:
        # Stop certificate manager if Let's Encrypt is enabled
        if config.is_letsencrypt_enabled():
            try:
                await certificate_manager.stop()
                log_system("Certificate manager stopped", level="INFO")
            except Exception as e:
                log_system(f"Error stopping certificate manager: {e}", level="ERROR")
        
        # Clean up and close the Redis client on shutdown if it was initialized
        if myapp.redis_client:
            await AsyncRedisClient.close()
            log_system("Redis connection closed", level="INFO")
        
        # Close SQLite connection
        if myapp.sqlite_client:
            await myapp.sqlite_client.close()
            log_system("SQLite connection closed", level="INFO")
        
        # Log application shutdown
        log_system("Application shutting down", level="INFO")


# Initialize the FastAPI app with custom settings
app = CustomFastAPI(
    docs_url=None,  # Disable the default docs endpoint
    redoc_url=None,  # Disable the default ReDoc endpoint
    openapi_url=None,  # Disable the default OpenAPI schema endpoint
)
app.lifespan_context = lifespan  # Set the lifespan context manager

# Add HTTP management middleware
app.add_middleware(HTTPDisableMiddleware)  # Check if HTTP is disabled
app.add_middleware(HTTPSRedirectMiddleware)  # Redirect HTTP to HTTPS if enabled

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Mount static files with proper cache headers (cache for 7 days)
mount_static_files(app, "/static", "static", name="static", cache_max_age=604800)

# Load environment variables from a .env file
env_config = StarletteConfig(".env")
load_dotenv()

# Configure CORS settings to allow specific origins
cors_config = config.get_cors_config()
origins = cors_config.get('origins', ["*"])

# Add CORS middleware to the application
app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=origins,
    allow_credentials=cors_config.get('allow_credentials', True),
    allow_methods=cors_config.get('allow_methods', ["GET", "POST", "PUT", "PATCH", "DELETE"]),
    allow_headers=cors_config.get('allow_headers', ["*"]),
    expose_headers=cors_config.get('expose_headers', ["Content-Disposition"])
)

# Include API routers with a common prefix and security dependencies
prefix_path = config.get_api_prefix()
app.include_router(
    system.router,
    prefix=f'{prefix_path}/system',
    tags=["System Router"]  # Tag for grouping in the OpenAPI docs
)

# Include logs router
app.include_router(
    logs.router,
    prefix=f'{prefix_path}',
    tags=["Logs"]  # Tag for grouping in the OpenAPI docs
)

# Include certificates router for Let's Encrypt management only if enabled
if config.is_letsencrypt_enabled():
    log_system("Let's Encrypt is enabled, adding certificate management endpoints", level="INFO")
    app.include_router(
        certificates.router,
        prefix=f'{prefix_path}/certificates',
        tags=["Certificates"]  # Tag for grouping in the OpenAPI docs
    )


# Custom OpenAPI schema endpoint
@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """
    Provides a custom OpenAPI schema.
    This endpoint is hidden from the standard documentation.
    """
    from fastapi.openapi.utils import get_openapi
    server_config = config.get_server_config()
    openapi_schema = get_openapi(
        title=server_config.get('title', "darktheme-auth-fastapi-server"),
        version=server_config.get('version', "v25.07.2024"),
        description=server_config.get('description', "API server with authentication and authorization."),
        routes=app.routes,
    )
    return openapi_schema


# Custom Swagger UI documentation endpoint
@app.get("/docs", include_in_schema=False)
async def custom_docs_url(credentials: HTTPBasicCredentials = Depends(verify_credentials)):  # noqa
    """
    Custom endpoint for accessing Swagger UI documentation.
    Requires authentication via HTTP Basic credentials.
    """
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title,
        swagger_css_url="/static/swagger_ui_dark.min.css"
    )


# Custom ReDoc documentation endpoint
@app.get("/redoc", include_in_schema=False)
async def custom_redoc_url(credentials: HTTPBasicCredentials = Depends(verify_credentials)):  # noqa
    """
    Custom endpoint for accessing ReDoc documentation.
    Requires authentication via HTTP Basic credentials.
    """
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=app.title
    )