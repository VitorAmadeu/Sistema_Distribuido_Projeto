import socket
import numpy as np
import random
import time
import comunicacao # Nosso módulo helper

HOST = '127.0.0.1'  # O IP do Mestre
PORT = 65432

def run_na_sch_rules(road, start_index, end_index, v_max, p_slow):
    """
    Executa as 4 regras do NaSch para um sub-conjunto (chunk) da estrada.
    Lê da 'road' global, retorna um mapa de {nova_pos: nova_vel}
    """
    partial_results = {}
    road_length = len(road)
    
    # Itera APENAS sobre o pedaço que este worker é responsável
    for i in range(start_index, end_index):
        
        # Se a célula NÃO tiver um carro, pule
        if road[i] == -1:
            continue

        # --- É um carro. Aplicar as 4 regras do NaSch ---
        v_atual = road[i]
        
        # Regra 0: Encontrar a distância (d) para o próximo carro
        distancia = 1
        # Procura na estrada global (lida com wrap-around)
        while road[(i + distancia) % road_length] == -1:
            distancia += 1
            if distancia > v_max + 1:
                break
        
        # Regra 1: Aceleração
        v_nova = min(v_atual + 1, v_max)
        
        # Regra 2: Desaceleração (Evitar Colisão)
        v_nova = min(v_nova, distancia - 1)
        
        # Regra 3: Aleatorização
        if v_nova > 0 and random.random() < p_slow:
            v_nova = v_nova - 1
            
        # Regra 4: Movimento (calcular nova posição)
        nova_posicao = (i + v_nova) % road_length
        
        # Armazena o resultado
        # O worker NÃO escreve em um 'next_road', ele reporta
        # o que ele encontrou para o Mestre.
        partial_results[nova_posicao] = v_nova
        
    return partial_results

def main():
    """Função principal do Trabalhador."""
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"[Worker] Conectado ao Mestre em {HOST}:{PORT}")
        except ConnectionRefusedError:
            print(f"[Worker] ERRO: Não foi possível conectar ao Mestre.")
            print("Você lembrou de iniciar o 'servidor_mestre.py' primeiro?")
            return

        # 1. Receber a configuração inicial
        config = comunicacao.recv_msg(s)
        if config is None:
            print("[Worker] Falha ao receber config.")
            return

        worker_id = config['id']
        start_index = config['start_index']
        end_index = config['end_index']
        sim_steps = config['sim_steps']
        v_max = config['v_max']
        p_slowdown = config['p_slowdown']
        
        print(f"[Worker {worker_id}] Tarefa recebida. Cuidarei de {start_index}-{end_index-1}")

        # 2. Loop de Simulação (ouvindo o Mestre)
        while True:
            # A. Receber a estrada atual (ou sinal de término)
            task_data = comunicacao.recv_msg(s)
            
            if task_data is None:
                print(f"[Worker {worker_id}] Mestre desconectou.")
                break
            
            if task_data.get('status') == 'TERMINAR':
                print(f"[Worker {worker_id}] Sinal de término recebido. Encerrando.")
                break

            road = task_data['road']
            
            # B. Processar o trabalho (a parte de CPU)
            partial_results = run_na_sch_rules(
                road, start_index, end_index, v_max, p_slowdown
            )
            
            # C. Enviar o resultado parcial de volta ao Mestre
            comunicacao.send_msg(s, partial_results)
            
        print(f"[Worker {worker_id}] Desconectando.")

if __name__ == "__main__":
    main()