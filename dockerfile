# Dockerfile

# 1. 베이스 이미지 (Python 3.11 슬림 버전 사용 - 용량 최소화)
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /code

# 3. 환경 변수 설정 (파이썬 버퍼링 비활성화 - 로그 즉시 출력)
ENV PYTHONUNBUFFERED=1

# 4. 의존성 파일 복사 및 설치
# (캐시 효율을 위해 requirements.txt만 먼저 복사)
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 5. 전체 소스 코드 복사
COPY ./app /code/app

# 6. 실행 명령어 (Uvicorn 서버 실행)
# host 0.0.0.0은 외부 접속 허용을 의미합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]