FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build
# 빌드 결과물이 /app/frontend/../backend/static에 생성됨

FROM python:3.11-slim
WORKDIR /app/backend

# 백엔드 코드 복사
COPY app/backend/ .

# static 폴더 복사 (이 부분이 수정됨)
COPY --from=frontend /app/frontend/../backend/static/ ./static/
# vite.config.ts의 outDir: "../backend/static" 설정과 일치

RUN pip install -r requirements.txt
RUN chmod -R 755 .

EXPOSE 8766

CMD ["python", "app.py"]