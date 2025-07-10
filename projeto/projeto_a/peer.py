import grpc
from concurrent import futures
import time
import os
import json
import threading

import versioning_pb2
import versioning_pb2_grpc

# --- CONFIGURAÇÕES DO PEER ---
PEER_ID = "peer_a" 
MY_PORT = "50051"   # Porta deste peer
PEER_PORT = "50052" # Porta do outro peer
WORKSPACE_DIR = f"{PEER_ID}/workspace"
METADATA_FILE = f"{PEER_ID}/metadata.json"

metadata = {}

def load_metadata():
    """Carrega os metadados do arquivo JSON."""
    global metadata
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            try:
                metadata = json.load(f)
            except json.JSONDecodeError:
                print(f"AVISO: Arquivo de metadados '{METADATA_FILE}' corrompido ou vazio. Começando do zero.")
                metadata = {}
    else:
        metadata = {}

def save_metadata():
    """Salva os metadados no arquivo JSON."""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def is_newer(c1, c2):
    """Verifica se o relógio vetorial c1 domina (é mais novo que) c2."""
    at_least_one_greater = False
    all_keys = set(c1.keys()) | set(c2.keys())
    for k in all_keys:
        v1 = c1.get(k, 0)
        v2 = c2.get(k, 0)
        if v1 < v2:
            return False
        if v1 > v2:
            at_least_one_greater = True
    return at_least_one_greater

def is_conflict(c1, c2):
    """Verifica se há conflito entre c1 e c2 (concorrência)."""
    if c1 == c2:
        return False
    return not is_newer(c1, c2) and not is_newer(c2, c1)

class VersioningServicer(versioning_pb2_grpc.VersioningServicer):
    """Implementação do servidor gRPC."""

    def GetFileList(self, request, context):
        """Retorna a lista de arquivos e seus relógios vetoriais."""
        print(f"[{PEER_ID}-Servidor] Recebido GetFileList.")
        file_list = []
        for filename, data in metadata.items():
            vc = data.get("vector_clock", {})
            file_list.append(versioning_pb2.FileInfo(filename=filename, vector_clock=vc))
        return versioning_pb2.FileList(files=file_list)

    def GetFile(self, request, context):
        """Retorna o conteúdo de um arquivo específico."""
        filename = request.filename
        print(f"[{PEER_ID}-Servidor] Recebido GetFile para '{filename}'.")
        filepath = os.path.join(WORKSPACE_DIR, filename)
        if filename in metadata and os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            vc = metadata[filename].get("vector_clock", {})
            return versioning_pb2.FileContent(filename=filename, content=content, vector_clock=vc)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Arquivo '{filename}' não encontrado no servidor.")
        return versioning_pb2.FileContent()

    def PushFile(self, request, context):
        """Recebe um arquivo de outro peer e decide se o aceita."""
        filename = request.filename
        incoming_vc = dict(request.vector_clock)
        
        # --- CORREÇÃO CRÍTICA (LEITURA) ---
        # Extrai corretamente o relógio vetorial local da estrutura aninhada para comparação.
        local_vc = metadata.get(filename, {}).get("vector_clock", {})
        
        print(f"[{PEER_ID}-Servidor] PushFile '{filename}'. Remoto: {incoming_vc}, Local: {local_vc}")

        if is_newer(incoming_vc, local_vc):
            print(f"[{PEER_ID}-Servidor] Versão de '{filename}' é mais nova. Aceitando.")
            filepath = os.path.join(WORKSPACE_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(request.content)
            
            # --- CORREÇÃO CRÍTICA (ESCRITA) ---
            # Salva os metadados mantendo a estrutura aninhada correta.
            metadata[filename] = {"vector_clock": incoming_vc}
            save_metadata()
            return versioning_pb2.PushResponse(success=True, message="Arquivo atualizado.")
        
        elif is_conflict(incoming_vc, local_vc):
            print(f"!!!!!!!! CONFLITO DETECTADO EM '{filename}' !!!!!!!!")
            conflict_path = os.path.join(WORKSPACE_DIR, f"{os.path.splitext(filename)[0]}.conflict_{int(time.time())}{os.path.splitext(filename)[1]}")
            with open(conflict_path, 'wb') as f:
                f.write(request.content)
            
            if filename not in metadata:
                metadata[filename] = {"vector_clock": {}}
            metadata[filename]['in_conflict'] = True
            metadata[filename]['conflicting_clock'] = incoming_vc
            save_metadata()

            print(f"A versão recebida foi salva em: {conflict_path}")
            print(f"Use o comando 'resolve {filename}' após mesclar as alterações.")
            return versioning_pb2.PushResponse(success=False, message=f"Conflito detectado. Salvo como {conflict_path}")

        else:
            print(f"[{PEER_ID}-Servidor] Versão de '{filename}' recebida é mais antiga ou igual. Ignorando.")
            return versioning_pb2.PushResponse(success=False, message="Versão local já é mais nova ou igual.")

def serve():
    """Inicia o servidor gRPC em uma thread separada."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    versioning_pb2_grpc.add_VersioningServicer_to_server(VersioningServicer(), server)
    server.add_insecure_port(f'[::]:{MY_PORT}')
    server.start()
    print(f"[{PEER_ID}-Servidor] Servidor iniciado na porta {MY_PORT}.")
    server.wait_for_termination()

def get_peer_stub():
    """Cria uma conexão (stub) com o outro peer."""
    channel = grpc.insecure_channel(f'localhost:{PEER_PORT}')
    return versioning_pb2_grpc.VersioningStub(channel)

def commit_local_change(filename):
    """Cria uma nova versão de um arquivo localmente e a envia ao outro peer."""
    filepath = os.path.join(WORKSPACE_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Erro: Arquivo '{filepath}' não existe para commit.")
        return

    if metadata.get(filename, {}).get('in_conflict'):
        print(f"Erro: O arquivo '{filename}' está em conflito. Use 'resolve {filename}' primeiro.")
        return

    print(f"\n[{PEER_ID}-Cliente] Realizando commit do arquivo '{filename}'...")
    
    if filename not in metadata:
        metadata[filename] = {"vector_clock": {}}
    
    current_vc = metadata[filename].get("vector_clock", {})
    current_vc[PEER_ID] = current_vc.get(PEER_ID, 0) + 1
    
    metadata[filename] = {"vector_clock": current_vc}
    print(f"[{PEER_ID}-Cliente] Novo relógio vetorial: {metadata[filename]['vector_clock']}")
    save_metadata()
    
    with open(filepath, 'rb') as f:
        content = f.read()

    try:
        stub = get_peer_stub()
        file_content = versioning_pb2.FileContent(
            filename=filename,
            content=content,
            vector_clock=metadata[filename]['vector_clock']
        )
        response = stub.PushFile(file_content)
        print(f"[{PEER_ID}-Cliente] Resposta do peer: '{response.message}'")
    except grpc.RpcError as e:
        print(f"[{PEER_ID}-Cliente] Erro ao contatar o outro peer: {e.details()}")

def synchronize():
    """Sincroniza com o outro peer de forma eficiente."""
    print(f"\n[{PEER_ID}-Cliente] Iniciando sincronização com o peer na porta {PEER_PORT}...")
    try:
        stub = get_peer_stub()
        remote_file_list = stub.GetFileList(versioning_pb2.Empty())
        
        for remote_file in remote_file_list.files:
            filename = remote_file.filename
            remote_vc = dict(remote_file.vector_clock)
            local_vc = metadata.get(filename, {}).get("vector_clock", {})
            
            print(f"[{PEER_ID}-Cliente] Checando '{filename}'. Local: {local_vc}, Remoto: {remote_vc}")

            if is_newer(remote_vc, local_vc):
                print(f"[{PEER_ID}-Cliente] Versão remota de '{filename}' é mais nova. Baixando...")
                file_content = stub.GetFile(versioning_pb2.FileRequest(filename=filename))
                filepath = os.path.join(WORKSPACE_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_content.content)
                metadata[filename] = {"vector_clock": remote_vc}
                save_metadata()
                print(f"[{PEER_ID}-Cliente] '{filename}' atualizado.")

            elif is_conflict(remote_vc, local_vc):
                print(f"!!!!!!!! CONFLITO DETECTADO DURANTE A SINCRONIZAÇÃO EM '{filename}' !!!!!!!!")
                if filename not in metadata:
                    metadata[filename] = {"vector_clock": {}}
                metadata[filename]['in_conflict'] = True
                metadata[filename]['conflicting_clock'] = remote_vc
                save_metadata()
                print(f"Sua versão local e a remota entraram em conflito.")
                print(f"Use o comando 'status' para ver detalhes e 'resolve {filename}' após mesclar.")

        print(f"[{PEER_ID}-Cliente] Sincronização concluída.")
    except grpc.RpcError as e:
        print(f"[{PEER_ID}-Cliente] Não foi possível conectar ao outro peer para sincronizar: {e.details()}")

def show_status():
    """Mostra um status formatado dos arquivos gerenciados."""
    print("\n--- Status dos Arquivos ---")
    if not metadata:
        print("Nenhum arquivo sendo gerenciado.")
        return

    for filename, data in metadata.items():
        vc = data.get("vector_clock", {})
        if data.get('in_conflict'):
            conflicting_vc = data.get('conflicting_clock', {})
            print(f"🔴 ARQUIVO: {filename} [EM CONFLITO]")
            print(f"   - Sua Versão (VC): {vc}")
            print(f"   - Versão Conflitante (VC): {conflicting_vc}")
            print(f"   - AÇÃO: Mescle as alterações do arquivo .conflict em '{filename}' e use o comando 'resolve {filename}'.")
        else:
            print(f"✅ ARQUIVO: {filename} [OK]")
            print(f"   - Versão (VC): {vc}")
    print("---------------------------\n")

def resolve_conflict(filename):
    """Resolve um conflito após a mesclagem manual do usuário."""
    if filename not in metadata or not metadata[filename].get('in_conflict'):
        print(f"Erro: O arquivo '{filename}' não está marcado como em conflito.")
        return

    print(f"Iniciando resolução de conflito para '{filename}'...")
    
    local_vc = metadata[filename].get('vector_clock', {})
    conflicting_vc = metadata[filename].get('conflicting_clock', {})
    
    resolved_vc = {}
    all_peers = set(local_vc.keys()) | set(conflicting_vc.keys())
    for peer in all_peers:
        resolved_vc[peer] = max(local_vc.get(peer, 0), conflicting_vc.get(peer, 0))
    
    resolved_vc[PEER_ID] = resolved_vc.get(PEER_ID, 0) + 1
    
    print(f"Relógio vetorial resolvido: {resolved_vc}")

    metadata[filename] = {'vector_clock': resolved_vc}
    save_metadata()
    
    print("Enviando versão resolvida para o outro peer...")
    filepath = os.path.join(WORKSPACE_DIR, filename)
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        stub = get_peer_stub()
        file_content = versioning_pb2.FileContent(filename=filename, content=content, vector_clock=resolved_vc)
        response = stub.PushFile(file_content)
        print(f"Resposta do peer: '{response.message}'")
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{filepath}' não encontrado. Certifique-se que ele existe.")
    except grpc.RpcError as e:
        print(f"ERRO ao contatar o outro peer: {e.details()}")

if __name__ == '__main__':
    if not os.path.exists(f"{PEER_ID}"):
        os.makedirs(f"{PEER_ID}")
    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)

    load_metadata()

    server_thread = threading.Thread(target=serve)
    server_thread.daemon = True
    server_thread.start()

    print("\n--- Sistema de Versionamento P2P ---")
    print(f"ID deste Peer: {PEER_ID}")
    print("Comandos disponíveis:")
    print("  'commit <nome_do_arquivo>' - Versiona uma alteração local e envia ao peer.")
    print("  'sync' - Sincroniza com o outro peer, baixando arquivos mais novos.")
    print("  'status' - Mostra os metadados locais.")
    print("  'resolve <nome_do_arquivo>' - Resolve um arquivo em conflito.")
    print("  'exit' - Fecha o programa.")
    print("------------------------------------")

    try:
        while True:
            cmd_input = input(f"({PEER_ID}) > ").strip().split()
            if not cmd_input:
                continue
            
            command = cmd_input[0].lower()

            if command == 'exit':
                break
            elif command == 'commit':
                if len(cmd_input) > 1:
                    commit_local_change(cmd_input[1])
                else:
                    print("Uso: commit <nome_do_arquivo>")
            elif command == 'sync':
                synchronize()
            elif command == 'status':
                show_status()
            elif command == 'resolve':
                if len(cmd_input) > 1:
                    resolve_conflict(cmd_input[1])
                else:
                    print("Uso: resolve <nome_do_arquivo>")
            else:
                print("Comando desconhecido.")
    except KeyboardInterrupt:
        print("\nDesligando...")
    finally:
        save_metadata()