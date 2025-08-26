FROM python

WORKDIR /app

# Copy requirements
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy static files (frontend)
COPY static ./static

# Copy the backend
COPY app.py ./

# Set environment variables
ENV HF_TOKEN=${HF_TOKEN}
ENV TRANSLATION_PROMPT_API_KEY=${TRANSLATION_PROMPT_API_KEY}

# Expose the port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "app:app", "--bind", "0.0.0.0:5000"]