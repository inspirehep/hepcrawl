FROM python:3-slim

WORKDIR /usr/src/app

RUN apt-get update \
  && apt-get install --no-install-recommends -y build-essential \
  && rm -rf /var/lib/apt/lists

COPY . .
RUN pip install --no-cache-dir -e .[all] && pip freeze

