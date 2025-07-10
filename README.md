# Repositório da matéria de Sistemas Distribuídos - OPT021

Este projeto implementa um sistema distribuído para versionamento de arquivos de texto, operando em uma arquitetura Peer-to-Peer (P2P).

O objetivo principal é garantir a consistência de dados e gerenciar conflitos de edição entre 2 nós sem a necessidade de um servidor central (próximos passos implementar a multiplos nós).

A comunicação entre os nós (peers) é realizada através de gRPC. A estrutura dos dados e os serviços disponíveis são definidos usando Protocol Buffers (.proto). 

Na arquitetura P2P do sistema, cada nó atua simultaneamente como cliente e servidor, respondendo a requisições de outros peers e iniciando a sincronização de dados ativamente.

A consistência e detecção de conflitos, é obtida através da implementação do conceito de Relógios Vetoriais (Vector Clocks). O sistema implementa um ciclo completo de gerenciamento de conflitos: detecção, isolamento da versão conflitante e um comando "resolve" explícito para que o usuário possa reintegrar uma versão mesclada de forma consistente.
 
<img width="2160" height="2496" alt="Arquitetura" src="https://github.com/user-attachments/assets/9706143b-f306-4a38-bb6c-d86f7fc3eccc" />

Principais Características:
- Consistência: Detecção de conflitos baseada em Relógios Vetoriais.
- Replicação de Dados: Os arquivos são replicados em todos os peers, garantindo alta disponibilidade.
- Persistência: O estado e os metadados de versionamento são mantidos localmente em arquivos JSON.
- Tolerância a falhas: Um nó continua em funcionamento mesmo com a parada de outro 

O sistema de diretórios segue este padrão:
<img width="339" height="564" alt="Captura de tela de 2025-07-10 18-49-30" src="https://github.com/user-attachments/assets/db8fb579-bb8a-44a6-acf7-92f50108d339" />





