FROM python:alpine3.17
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY book.py .
EXPOSE 5001
CMD ["python", "book.py"]