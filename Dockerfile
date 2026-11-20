FROM python:3.12-slim
WORKDIR /app
COPY app.py .
COPY static static
USER 65534:65534
CMD ["python", "app.py"]
