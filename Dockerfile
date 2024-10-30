# Python 이미지를 기반으로 설정
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# Node.js 설치
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 프로젝트 파일 복사
COPY . .

# 프론트엔드 빌드
RUN cd frontend && npm install && npm run build

# 백엔드 설정
RUN cd backend && pip install -r requirements.txt

# start.sh 실행 권한 부여
RUN chmod +x start.sh

# 포트 설정
EXPOSE 8766

# 시작 명령어
CMD ["./start.sh"]