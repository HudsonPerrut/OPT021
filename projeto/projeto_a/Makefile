# Define o interpretador Python a ser usado
PYTHON = python3

# Define o nome do diretório do ambiente virtual
VENV_DIR = venv
VENV_PYTHON = $(VENV_DIR)/bin/python

# O alvo padrão que será executado quando você digitar apenas "make"
.DEFAULT_GOAL := all

# Alvos que não representam arquivos
.PHONY: all setup install build clean

# Alvo "all": Executa a instalação das dependências e a geração do código gRPC
all: install build

# Alvo "setup": Cria o ambiente virtual se ele não existir
# A existência do arquivo 'activate' serve como indicador de que o venv foi criado.
$(VENV_DIR)/bin/activate:
	@echo "--- Criando ambiente virtual em '$(VENV_DIR)'... ---"
	$(PYTHON) -m venv $(VENV_DIR)

# Alvo "install": Instala as dependências do projeto usando o pip do venv
# Depende da criação do ambiente virtual.
install: $(VENV_DIR)/bin/activate
	@echo "--- Instalando dependências (grpcio, grpcio-tools)... ---"
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install grpcio grpcio-tools

# Alvo "build": Gera o código Python a partir do arquivo .proto
# Depende da instalação das ferramentas.
build: install
	@echo "--- Gerando código gRPC a partir de versioning.proto... ---"
	$(VENV_PYTHON) -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. versioning.proto
	@echo "Código gerado com sucesso!"

# Alvo "clean": Remove os arquivos gerados e o ambiente virtual para uma limpeza completa
clean:
	@echo "--- Limpando o projeto... ---"
	rm -rf $(VENV_DIR)
	rm -f versioning_pb2.py versioning_pb2.pyi versioning_pb2_grpc.py
	@echo "Limpeza concluída."