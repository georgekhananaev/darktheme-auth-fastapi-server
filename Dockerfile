# Use the official Python image with version 3.12.4 slim
FROM python:3.12.4-slim

# Metadata as labels
LABEL maintainer="George Khananaev"
LABEL description="A template FastAPI server with dark-themed docs, authentication, and Redis caching."

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port on which the app will run
EXPOSE 8000

# Command to run the app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
