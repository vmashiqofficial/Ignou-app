# Use the official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy your requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose port 7860 (Hugging Face Spaces requires port 7860)
EXPOSE 7860

# Run the application using Gunicorn mapped to port 7860
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]