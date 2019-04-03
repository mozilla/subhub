FROM python:3.7
# lifted straight from https://github.com/docker-library/python/blob/7eca63adca38729424a9bab957f006f5caad870f/3.6/onbuild/Dockerfile
WORKDIR /usr/src/app/
RUN mkdir -p /usr/src/app/

# Extra python env
ENV PYTHONUNBUFFERED=1, \
    PYTHONDONTWRITEBYTECODE=1, \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build args with defaults
ENV APP_UID=1000
ENV APP_GID=1000
ENV APP_USER=subhub
ENV APP_PORT=5000
ENV APP_WORKERS=1
ENV APP_MODULE=app:app
ENV APP_SRCTAR=.src.tar.gz
ENV PYTHONPATH=.:/usr/src/app/:/usr/src/app/bot:$PYTHONPATH

# add bundled source code
ADD $APP_SRCTAR /usr/src/app/

# add python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# add non-priviledged user
RUN groupadd --gid $APP_GID $APP_USER && \
    adduser --uid $APP_UID --disabled-password --gecos '' --ingroup $APP_USER --no-create-home $APP_USER

# change user
RUN chown $APP_USER:$APP_USER -R .
USER $APP_USER
RUN ["chmod", "+x", "/usr/src/app/boot.sh"]
CMD sh -c "/usr/src/app/convert_env.sh && /usr/local/bin/gunicorn -w ${APP_WORKERS} -b :${APP_PORT} ${APP_MODULE}"
