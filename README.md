# Repositório da matéria de Sistemas Distribuídos - OPT021

Sistema de versionamento de arquivos entre duas máquinas.

A arquitetura do sistema é utilizando o modelo P2P.

Em cada nó há um cliente e um servidor. O Cliente possui a função de adicionar arquivos a uma branch, realizar um comiit e solicitar push/pull request para o servidor do outro nó.
 
<img width="2160" height="2496" alt="Arquitetura" src="https://github.com/user-attachments/assets/9706143b-f306-4a38-bb6c-d86f7fc3eccc" />

A comunicação entre os nós é realizada através do gRPC + protocol buffer.

O sistema de diretórios segue este padrão:

![Captura de tela de 2025-06-10 15-45-11](https://github.com/user-attachments/assets/005d7fed-f716-4581-a29d-e1d8cdc5a7bd)


