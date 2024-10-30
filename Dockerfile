FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# 먼저 파일들을 복사
COPY app/backend/ backend/
COPY --from=frontend /app/frontend/../backend/static/ ./backend/static/

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN cd backend && pip install -r requirements.txt

# 간단한 권한 설정
RUN chmod -R 755 backend

EXPOSE 8766

# 시작 명령어
CMD ["python", "backend/app.py"]