FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# 백엔드 파일 복사
COPY app/backend/ backend/
COPY app/start.sh .
COPY --from=frontend /app/frontend/../backend/static/ ./backend/static/

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지를 시스템에 직접 설치
RUN cd backend && pip install -r requirements.txt

RUN chmod +x start.sh

EXPOSE 8766

CMD ["./start.sh"]