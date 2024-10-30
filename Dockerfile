FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build
# 빌드 결과물이 backend/static 폴더에 생성됨

FROM python:3.11-slim
WORKDIR /app
# 수정된 경로로 복사
COPY --from=frontend /app/frontend/../backend/static/ ./backend/static/
COPY app/backend/ backend/
COPY app/start.sh .

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN cd backend && pip install -r requirements.txt
RUN chmod +x start.sh

EXPOSE 8766

CMD ["./start.sh"]