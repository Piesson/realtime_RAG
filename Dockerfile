FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim
WORKDIR /app/backend  # 여기가 변경됨

# 백엔드 코드 복사
COPY app/backend/ .

# 프론트엔드 빌드 결과물을 backend/static으로 복사
COPY --from=frontend /app/frontend/../backend/static/ ./static/

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN pip install -r requirements.txt

# 권한 설정
RUN chmod -R 777 /app

EXPOSE 8766

# 시작 명령어 (경로 수정)
CMD ["python", "app.py"]