# 기본 이미지 변경
FROM node:18 AS frontend
WORKDIR /app/frontend
COPY frontend/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY --from=frontend /app/frontend/dist /app/frontend/dist
COPY backend/ backend/
COPY start.sh .

# 필요한 패키지만 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN cd backend && pip install -r requirements.txt

# 실행 권한 부여
RUN chmod +x start.sh

# 포트 설정
EXPOSE 8766

# 시작 명령어
CMD ["./start.sh"]