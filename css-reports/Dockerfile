# Use the official Python image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy requirements (if any) and app files to the container
COPY requirements.txt /app/requirements.txt
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the app
CMD ["python3", "app.py"]
