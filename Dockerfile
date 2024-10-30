FROM node:18 AS frontend
# app/frontend 경로 설정
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# app 폴더의 파일들 복사
COPY app/backend/ backend/
COPY app/start.sh .

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN cd backend && pip install -r requirements.txt

RUN chmod +x start.sh

EXPOSE 8766

CMD ["./start.sh"]