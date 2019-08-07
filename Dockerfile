FROM python:3.7-alpine3.10
MAINTAINER Stewart Henderson <shenderson@mozilla.com>

ARG STRIPE_API_KEY
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG STRIPE_LOG
ARG STRIPE_API_MOCK
ARG LOCAL_FLASK_PORT

ENV STRIPE_API_KEY=$STRIPE_API_KEY
ENV AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
ENV STRIPE_LOG=$STRIPE_LOG
ENV STRIPE_API_MOCK=$STRIPE_API_MOCK
ENV LOCAL_FLASK_PORT=$LOCAL_FLASK_PORT

# Enable Flask debug mode
ENV FLASK_ENV=development

RUN apk update
# Alpine Registry for package versions, https://pkgs.alpinelinux.org/packages
RUN apk add --no-cache bash==5.0.0-r0
RUN apk add build-base==0.5-r1
RUN apk add gcc==8.3.0-r0
RUN apk add linux-headers==4.19.36-r0
RUN apk add git==2.22.0-r0
RUN apk add graphviz-dev==2.40.1-r1

RUN mkdir -p /subhub
COPY . /subhub

WORKDIR /subhub

EXPOSE $LOCAL_FLASK_PORT

RUN pip install --upgrade pip
RUN pip install awscli
RUN pip install -r automation_requirements.txt
RUN ls -ltra 
# RUN python dodo.py

# ENTRYPOINT scripts/entrypoint.sh
