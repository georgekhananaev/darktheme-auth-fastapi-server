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
    echo "Please update the .env file with your secure credentials."
fi

# Check if Redis is needed
if grep -q "enabled: false" config.yaml; then
    echo "Starting server with Redis disabled..."
else
    echo "Starting server with Redis enabled..."
    echo "Make sure Redis is running locally or change 'enabled: true' to 'enabled: false' in config.yaml."
fi

# Run the server
echo "Starting server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload