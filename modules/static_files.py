import os
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi import FastAPI
from starlette.datastructures import URL


class CachedStaticFiles(StaticFiles):
    """
    A custom StaticFiles class that adds proper cache headers.
    This helps browsers cache static files properly and reduces unnecessary requests.
    """
    
    def __init__(self, *args, **kwargs):
        self.cache_max_age = kwargs.pop("cache_max_age", 86400)  # Default 1 day
        super().__init__(*args, **kwargs)
    
    async def get_response(self, path, scope):
        """
        Override the get_response method to add cache headers to the response.
        """
        response = await super().get_response(path, scope)
        
        if isinstance(response, FileResponse) and 200 <= response.status_code < 300:
            # Add cache headers
            response.headers["Cache-Control"] = f"public, max-age={self.cache_max_age}"
            
            # Add Expires header (helps older browsers)
            from datetime import datetime, timedelta
            expires = datetime.utcnow() + timedelta(seconds=self.cache_max_age)
            response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            # Add ETag and Vary for better caching
            if "ETag" not in response.headers:
                import hashlib
                file_path = os.path.join(self.directory, path)
                if os.path.exists(file_path):
                    file_stat = os.stat(file_path)
                    etag = hashlib.md5(f"{file_stat.st_mtime}-{file_stat.st_size}".encode()).hexdigest()
                    response.headers["ETag"] = f'"{etag}"'
            
            response.headers["Vary"] = "Accept-Encoding"
        
        return response


def mount_static_files(app: FastAPI, path: str, directory: str, name: str = None, cache_max_age: int = 86400):
    """
    Mounts static files to a FastAPI app with proper cache headers.
    
    Args:
        app: The FastAPI app to mount static files to
        path: The URL path to mount the static files to
        directory: The directory containing the static files
        name: The name for the mounted app
        cache_max_age: The max age for cache control (in seconds)
    """
    static_files = CachedStaticFiles(directory=directory, html=True, cache_max_age=cache_max_age)
    app.mount(path, static_files, name=name)
    return static_files