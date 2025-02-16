FROM python:3.10-slim

# Create a non-root user
RUN useradd -m appuser

# Set the working directory
WORKDIR /app

# Install the dependencies
RUN pip install --no-cache-dir gunicorn

# Copy the requirements file
COPY requirements.txt .
# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy the entrypoint script
COPY entrypoint.sh .

# Set the ownership of the application code to the non-root user
RUN chown -R appuser:appuser /app

# Change to the non-root user
USER appuser

# Command to run the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]