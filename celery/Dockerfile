FROM python:3.14

ENV PYTHONUNBUFFERED=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# Dependências do sistema
RUN apt-get update -y -qq \
    && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    nodejs \
    gcc \
    g++ \
    default-jdk \
    iptables

# upgrade do pip
RUN pip install --no-cache-dir --upgrade pip

# Instala as dependências Python primeiro para aproveitar o cache do Docker
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

ENTRYPOINT ["/bin/bash"]