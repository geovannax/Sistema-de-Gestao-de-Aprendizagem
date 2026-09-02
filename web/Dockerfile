FROM python:3.14

ENV PYTHONUNBUFFERED=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# Dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# upgrade do pip
RUN pip install --no-cache-dir --upgrade pip

# Instala as dependências Python primeiro para aproveitar o cache do Docker
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia os arquivos do CodeMirror 6 para o contêiner
COPY ./web/codemirror6/package.json ./web/codemirror6/package-lock.json /app/codemirror6/

# Instala as dependências do CodeMirror 6
RUN cd /app/codemirror6 \
    && npm ci

EXPOSE 8000

ENTRYPOINT ["/bin/bash"]