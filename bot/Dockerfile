FROM python:3.8-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY req.txt ./
RUN apk update && apk add python3-dev \
                          gcc \
                          libc-dev \
                          libffi-dev

RUN pip install --upgrade pip
RUN pip install -r req.txt


COPY .. /app

CMD ["python3", "main.py"]