import pickle
import struct

"""
Módulo auxiliar para comunicação confiável via sockets.
Serializa e desserializa objetos Python usando pickle, com cabeçalho de tamanho.
"""

def send_msg(sock, data_object):
    """Serializa e envia um objeto via socket com cabeçalho de tamanho."""
    try:
        data_bytes = pickle.dumps(data_object)
        
        # Envia cabeçalho com tamanho da mensagem (8 bytes)
        msg_len_header = struct.pack('!Q', len(data_bytes))
        sock.sendall(msg_len_header)
        
        # Envia os dados serializados
        sock.sendall(data_bytes)
        
    except Exception as e:
        print(f"Erro ao enviar dados: {e}")

def recv_msg(sock):
    """Recebe e desserializa uma mensagem do socket."""
    try:
        # Lê cabeçalho de 8 bytes com tamanho da mensagem
        msg_len_header = sock.recv(8)
        if not msg_len_header:
            return None  # Conexão fechada
        
        msg_len = struct.unpack('!Q', msg_len_header)[0]
        
        # Lê os dados em chunks para garantir integridade
        data_bytes_list = []
        bytes_recebidos = 0
        while bytes_recebidos < msg_len:
            chunk_size = min(msg_len - bytes_recebidos, 4096)
            chunk = sock.recv(chunk_size)
            if not chunk:
                raise ConnectionError("Conexão perdida durante recepção.")
            data_bytes_list.append(chunk)
            bytes_recebidos += len(chunk)
            
        data_bytes = b''.join(data_bytes_list)
        
        # Desserializa os dados
        return pickle.loads(data_bytes)
    
    except Exception as e:
        print(f"Erro ao receber dados: {e}")
        return None