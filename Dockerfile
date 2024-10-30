FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim
WORKDIR /app  # 여기를 /app으로 변경

# 백엔드 코드 복사
COPY app/backend/ backend/
COPY --from=frontend /app/frontend/../backend/static/ ./backend/static/

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN cd backend && pip install -r requirements.txt

# 권한 설정 수정
RUN chown -R root:root /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/backend  # 백엔드 폴더만 777 권한 부여

EXPOSE 8766

# 시작 명령어
CMD ["python", "backend/app.py"]  # 경로 수정