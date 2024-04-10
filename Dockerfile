FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MAX_COURSE_ATTEMPTS="" \
    FERNET_KEY="" \
    FABMAN_API_KEY="" \
    CLASSMARKER_WEBHOOK_SECRET="" \
    FLASK_SECRET_KEY="" \
    MAIL_USERNAME="" \
    MAIL_PASSWORD="" \
    VERIFY_CLASSMARKER_REQUESTS="" \
    SECRET_KEY="" \
    MAIL_SERVER="" \
    MAIL_PORT="" \
    MAIL_USERNAME="" \
    MAIL_PASSWORD="" \
    MAIL_USE_TLS="" \
    BE_ENV="prod"

WORKDIR "/"
COPY . .

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
RUN pip install gunicorn==20.1.*

EXPOSE 5000

CMD gunicorn --log-level=debug --workers=2 --bind=[::]:8000 'main_run:main_loop()'
