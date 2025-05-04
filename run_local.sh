#!/bin/bash

# Ensure the logs directory exists
mkdir -p logs

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists, create example if not
if [ ! -f ".env" ]; then
    echo "Creating example .env file..."
    echo "BEARER_SECRET_KEY=example_secret_key" > .env
    echo "FASTAPI_UI_USERNAME=admin" >> .env
    echo "FASTAPI_UI_PASSWORD=password" >> .env
    echo "API_KEY=your_api_key_here" >> .env
    echo "Please update the .env file with your secure credentials."
fi

# Check if API key is enabled
if grep -q "api_key:\s*$" -A 2 config.yaml | grep -q "enabled: true"; then
    echo "API Key authentication is enabled."
    if ! grep -q "API_KEY" .env; then
        echo "API_KEY not found in .env file. Adding it..."
        echo "API_KEY=your_api_key_here" >> .env
        echo "Please update the API_KEY in your .env file."
    fi
fi

# Check if Redis is needed
if grep -q "enabled: false" config.yaml; then
    echo "Starting server with Redis disabled..."
else
    echo "Starting server with Redis enabled..."
    echo "Make sure Redis is running locally or change 'enabled: true' to 'enabled: false' in config.yaml."
fi

# Check if Let's Encrypt certificate directory exists
mkdir -p certs

# Check if HTTP is disabled
HTTP_DISABLED=$(grep -A 2 "http:" config.yaml | grep "enabled:" | grep -q "false" && echo "true" || echo "false")

# Check if HTTPS is enabled
if grep -q "https:\s*$" -A 2 config.yaml | grep -q "enabled: true"; then
    echo "Starting server with HTTPS enabled..."
    
    # Determine HTTPS mode (custom or Let's Encrypt)
    HTTPS_MODE=$(grep -A 3 "https:" config.yaml | grep "mode:" | awk '{print $2}' | tr -d '"')
    
    if [ "$HTTPS_MODE" = "letsencrypt" ]; then
        echo "Using Let's Encrypt mode for SSL..."
        
        # Check if Let's Encrypt is enabled
        LETSENCRYPT_ENABLED=$(grep -A 2 "letsencrypt:" config.yaml | grep "enabled:" | awk '{print $2}')
        
        if [ "$LETSENCRYPT_ENABLED" = "true" ]; then
            echo "Let's Encrypt is enabled. Checking certificate status..."
            
            # Check if certificates exist
            if [ -f "./certs/server.crt" ] && [ -f "./certs/server.key" ]; then
                echo "Found existing Let's Encrypt certificates."
                
                # Run the server with SSL
                echo "Starting server with Let's Encrypt SSL..."
                if [ "$HTTP_DISABLED" = "true" ]; then
                    echo "HTTP is disabled. Only HTTPS will be available."
                    # Pass flag to indicate HTTP is disabled
                    DISABLE_HTTP=1 uvicorn main:app --host 0.0.0.0 --port 443 --reload --ssl-certfile ./certs/server.crt --ssl-keyfile ./certs/server.key
                else
                    uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ssl-certfile ./certs/server.crt --ssl-keyfile ./certs/server.key
                fi
            else
                echo "Let's Encrypt certificates not found."
                echo "Certificates will be generated automatically on first request to the certificate management API."
                if [ "$HTTP_DISABLED" = "true" ]; then
                    echo "ERROR: HTTP is disabled but no HTTPS certificates are available."
                    echo "Cannot start server without either HTTP or HTTPS enabled."
                    echo "Please modify config.yaml to enable HTTP or provide SSL certificates."
                    exit 1
                else
                    echo "Starting server with HTTP for now..."
                    echo "After starting, you can issue a certificate via the API endpoint."
                    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
                fi
            fi
        else
            echo "Let's Encrypt is configured but not enabled. Starting without SSL..."
            if [ "$HTTP_DISABLED" = "true" ]; then
                echo "ERROR: HTTP is disabled but HTTPS is not properly configured."
                echo "Cannot start server without either HTTP or HTTPS enabled."
                echo "Please modify config.yaml to enable HTTP or configure HTTPS properly."
                exit 1
            else
                uvicorn main:app --host 0.0.0.0 --port 8000 --reload
            fi
        fi
    else
        # Default custom SSL certificate mode
        # Check if certificates exist
        if [ -f "./certs/server.crt" ] && [ -f "./certs/server.key" ]; then
            # Run the server with SSL
            echo "Starting server with custom SSL certificates..."
            if [ "$HTTP_DISABLED" = "true" ]; then
                echo "HTTP is disabled. Only HTTPS will be available."
                # Pass flag to indicate HTTP is disabled
                DISABLE_HTTP=1 uvicorn main:app --host 0.0.0.0 --port 443 --reload --ssl-certfile ./certs/server.crt --ssl-keyfile ./certs/server.key
            else
                uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ssl-certfile ./certs/server.crt --ssl-keyfile ./certs/server.key
            fi
        else
            echo "WARNING: HTTPS is enabled in config.yaml but certificates not found."
            echo "Creating certs directory..."
            mkdir -p certs
            echo "Please place your SSL certificates in the certs directory:"
            echo "  - ./certs/server.crt"
            echo "  - ./certs/server.key"
            if [ "$HTTP_DISABLED" = "true" ]; then
                echo "ERROR: HTTP is disabled but no HTTPS certificates are available."
                echo "Cannot start server without either HTTP or HTTPS enabled."
                echo "Please modify config.yaml to enable HTTP or provide SSL certificates."
                exit 1
            else
                echo "Starting server with HTTP for now..."
                uvicorn main:app --host 0.0.0.0 --port 8000 --reload
            fi
        fi
    fi
else
    # Check if HTTP is disabled
    if [ "$HTTP_DISABLED" = "true" ]; then
        echo "ERROR: HTTP is disabled and HTTPS is not enabled."
        echo "Cannot start server without either HTTP or HTTPS enabled."
        echo "Please modify config.yaml to enable HTTP or HTTPS."
        exit 1
    else
        # Run the server without SSL
        echo "Starting server with HTTP only..."
        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    fi
fi