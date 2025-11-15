import pickle
import struct

"""
Módulo helper para enviar e receber objetos Python (como arrays numpy)
via sockets de forma confiável, lidando com o tamanho da mensagem.
"""

def send_msg(sock, data_object):
    """Serializa um objeto com pickle e o envia pelo socket."""
    try:
        data_bytes = pickle.dumps(data_object)
        
        # 1. Envia um cabeçalho de 8 bytes com o tamanho da mensagem
        msg_len_header = struct.pack('!Q', len(data_bytes)) # 'Q' = 8 bytes
        sock.sendall(msg_len_header)
        
        # 2. Envia os dados reais
        sock.sendall(data_bytes)
        
    except Exception as e:
        print(f"Erro ao enviar dados: {e}")

def recv_msg(sock):
    """Recebe uma mensagem do socket, lendo primeiro o cabeçalho de tamanho."""
    try:
        # 1. Lê o cabeçalho de 8 bytes
        msg_len_header = sock.recv(8)
        if not msg_len_header:
            return None # Conexão fechada
        
        msg_len = struct.unpack('!Q', msg_len_header)[0]
        
        # 2. Lê exatamente 'msg_len' bytes dos dados
        data_bytes_list = []
        bytes_recebidos = 0
        while bytes_recebidos < msg_len:
            # Lê em pedaços (chunks) para garantir que tudo chegue
            chunk_size = min(msg_len - bytes_recebidos, 4096)
            chunk = sock.recv(chunk_size)
            if not chunk:
                raise ConnectionError("Conexão perdida durante a recepção.")
            data_bytes_list.append(chunk)
            bytes_recebidos += len(chunk)
            
        data_bytes = b''.join(data_bytes_list)
        
        # 3. Desserializa os dados com pickle
        return pickle.loads(data_bytes)
    
    except Exception as e:
        print(f"Erro ao receber dados: {e}")
        return None