FROM python:3.9.1
WORKDIR /opt/code
COPY . .
RUN pip install -r requirements.txt