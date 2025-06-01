FROM python:3.13.3-slim

# Set the working directory
WORKDIR /app
# Copy the requirements file into the container
COPY src/requirements.txt .
# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application code into the container
COPY src/ .