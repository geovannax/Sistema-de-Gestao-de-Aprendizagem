# entra do diretorio
cd doc
# Cria ambiente virtual
python -m venv .venv
# ativa o ambiente
.venv\Scripts\activate
# Instala os pacotes
pip install -r requirements.txt
# Inicializa o servidor da documentacao
mkdocs serve 
# Go
http://127.0.0.1:8000/