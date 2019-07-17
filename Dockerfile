ARG _STRIPE_API_KEY
ARG _AWS_ACCESS_KEY
ARG _AWS_SECRET_KEY

FROM python:3.7-alpine3.10
MAINTAINER Stewart Henderson <shenderson@mozilla.com>

ENV STRIPE_API_KEY=${_STRIPE_API_KEY}
ENV AWS_ACCESS_KEY=${_AWS_ACCESS_KEY}
ENV AWS_SECRET_KEY=${_AWS_SECRET_KEY}

RUN apk update
# Alpine Registry for package versions, https://pkgs.alpinelinux.org/packages
RUN apk add --no-cache bash==5.0.0-r0
RUN apk add build-base==0.5-r1
RUN apk add gcc==8.3.0-r0
RUN apk add linux-headers==4.19.36-r0
RUN apk add git==2.22.0-r0

RUN mkdir -p /subhub
COPY . /subhub

WORKDIR /subhub

EXPOSE 5000

RUN python -m setup develop
CMD ["python", "subhub/app.py"]