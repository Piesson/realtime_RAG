FROM node:18 AS frontend
WORKDIR /app/frontend
COPY app/frontend/ .
RUN npm install
RUN npm run build
# 여기서 빌드 결과물이 /app/backend/static에 생성됨

FROM python:3.11-slim
WORKDIR /app/backend

# 백엔드 코드 복사
COPY app/backend/ .

# static 폴더 복사 (경로 수정)
COPY --from=frontend /app/backend/static/ ./static/

RUN pip install -r requirements.txt
RUN chmod -R 755 .

EXPOSE 8766

CMD ["python", "app.py"]