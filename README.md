# Repositório da matéria de Sistemas Distribuídos - OPT021

Sistema de versionamento de arquivos entre duas máquinas.

A arquitetura do sistema é utilizando o modelo P2P.
Em cada nó há um cliente e um servidor. O Cliente possui a função de adicionar arquivos a uma branch, realizar um comiit e solicitar push/pull request para o servidor do outro nó.
 
![SDDiagrama](https://github.com/user-attachments/assets/0250f27e-5f0f-43d2-8589-d0523b66ff87) 

A comunicação entre os nós é realizada através do gRPC + protocol buffer.
O sistema de diretórios segue este padrão:
/nome_da_pasta_do_nó/
├── node.py                         # O script principal do sistema de versionamento
└── meu_repositorio_distribuido/    # A pasta raiz do repositório versionado
    ├── src/                        # --> Diretório de Trabalho
    │   ├── arquivo_de_texto.txt
    │   ├── codigo_fonte.py
    │   └── imagens/
    │       └── imagem.png
    └── .repo_meta/                 # --> Diretório de Metadados do Repositório (oculto)
        ├── commits.json            # Armazena o histórico de commits (ID, mensagem, timestamp, arquivos)
        └── versions/               # Armazena as diferentes versões dos arquivos por commit
            ├── commit_id_12345/    # Versão completa dos arquivos no commit 12345
            │   ├── src/            # Recria a estrutura interna do `src/` para esta versão
            │   │   ├── arquivo_de_texto.txt
            │   │   ├── codigo_fonte.py
            │   │   └── imagens/
            │   │       └── imagem.png
            ├── commit_id_abcde/    # Versão completa dos arquivos no commit abcde
            │   └── src/
            │       ├── arquivo_de_texto.txt
            │       └── codigo_fonte_nova.py
            └── ... (outros diretórios de commits)


