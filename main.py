from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBasicCredentials
from starlette.config import Config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from auth.fastapi_auth import verify_credentials, get_secret_key
from components.logger import log_error
from routers import sample_route
from db.clientRedis import AsyncRedisClient
from contextlib import asynccontextmanager


class CustomFastAPI(FastAPI):
    """
    A custom FastAPI class that holds additional application state.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Custom FastAPI Application"  # Title of the application
        self.redis_client = None  # Placeholder for Redis client instance


@asynccontextmanager
async def lifespan(myapp: CustomFastAPI):
    """
    Lifespan context manager for managing startup and shutdown events.
    This is where we initialize and clean up resources like the Redis client.
    """
    # Initialize the Redis client on startup
    myapp.redis_client = await AsyncRedisClient.get_instance()
    try:
        yield
    except Exception as e:
        log_error(f"Error during lifespan: {e}")
    finally:
        # Clean up and close the Redis client on shutdown
        if myapp.redis_client:
            await myapp.redis_client.close()


# Initialize the FastAPI app with custom settings
app = CustomFastAPI(
    docs_url=None,  # Disable the default docs endpoint
    redoc_url=None,  # Disable the default ReDoc endpoint
    openapi_url=None  # Disable the default OpenAPI schema endpoint
)
app.lifespan_context = lifespan  # Set the lifespan context manager

app.mount("/static", StaticFiles(directory="static"), name="static")  # Serve static files

# Load environment variables from a .env file
config = Config(".env")
load_dotenv()

# Configure CORS settings to allow specific origins
origins = [
    "*",  # Allow all origins (change as needed for production)
    "http://localhost",
    "http://localhost:3000",
    "http://192.168.110.128"
]

# Add CORS middleware to the application
app.add_middleware(
    CORSMiddleware,   # noqa
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Include API routers with a common prefix and security dependencies
prefix_path = '/api/v1'
app.include_router(
    sample_route.router,
    prefix=f'{prefix_path}/sample',
    dependencies=[Depends(get_secret_key)],  # Security dependency
    tags=["Sample Router"]  # Tag for grouping in the OpenAPI docs
)


# Custom OpenAPI schema endpoint
@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """
    Provides a custom OpenAPI schema.
    This endpoint is hidden from the standard documentation.
    """
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title="Booking.com API",
        version="v25.07.2024",
        description="Booking.com Unofficial API",
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
