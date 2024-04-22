FROM python:3.11.5-slim
RUN apt-get update && apt-get upgrade -y && apt-get autoremove -y
RUN apt-get install -y git
COPY requirements.txt ./

RUN pip install -U pip
RUN pip install -r requirements.txt

WORKDIR /app
COPY . .

#HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/live || exit 1

ENTRYPOINT ["python", "main.py"]