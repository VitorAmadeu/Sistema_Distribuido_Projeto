import socket
import numpy as np
import random
import time
import comunicacao # Nosso módulo helper

HOST = '127.0.0.1'  # Endereço IP do servidor mestre
PORT = 65432

def run_na_sch_rules(road, start_index, end_index, v_max, p_slow):
    """
    Aplica as regras do modelo Nagel-Schreckenberg a um segmento da estrada.
    Retorna um dicionário com as novas posições e velocidades dos carros no segmento.
    """
    partial_results = {}
    road_length = len(road)
    
    # Processa apenas o segmento atribuído a este worker
    for i in range(start_index, end_index):
        
        # Ignora células vazias
        if road[i] == -1:
            continue

        # Aplica as quatro regras do NaSch para o carro na posição i
        v_atual = road[i]
        
        # Regra 1: Calcula a distância até o próximo carro (com wrap-around)
        distancia = 1
        while road[(i + distancia) % road_length] == -1:
            distancia += 1
            if distancia > v_max + 1:
                break
        
        # Regra 2: Aceleração
        v_nova = min(v_atual + 1, v_max)
        
        # Regra 3: Desaceleração para evitar colisão
        v_nova = min(v_nova, distancia - 1)
        
        # Regra 4: Aleatorização (slowdown probabilístico)
        if v_nova > 0 and random.random() < p_slow:
            v_nova -= 1
            
        # Calcula nova posição após movimento
        nova_posicao = (i + v_nova) % road_length
        
        # Registra resultado parcial para envio ao mestre
        partial_results[nova_posicao] = v_nova
        
    return partial_results

def main():
    """Executa o loop principal do worker: conecta ao mestre e processa simulações."""
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"[Worker] Conectado ao Mestre em {HOST}:{PORT}")
        except ConnectionRefusedError:
            print(f"[Worker] ERRO: Não foi possível conectar ao Mestre.")
            print("Certifique-se de que 'servidor_mestre.py' está em execução.")
            return

        # Recebe configuração inicial do mestre
        config = comunicacao.recv_msg(s)
        if config is None:
            print("[Worker] Falha ao receber configuração.")
            return

        worker_id = config['id']
        start_index = config['start_index']
        end_index = config['end_index']
        sim_steps = config['sim_steps']
        v_max = config['v_max']
        p_slowdown = config['p_slowdown']
        
        print(f"[Worker {worker_id}] Tarefa recebida. Responsável por {start_index}-{end_index-1}")

        # Loop de simulação: recebe tarefas e envia resultados
        while True:
            # Recebe dados da tarefa ou sinal de término
            task_data = comunicacao.recv_msg(s)
            
            if task_data is None:
                print(f"[Worker {worker_id}] Mestre desconectou.")
                break
            
            if task_data.get('status') == 'TERMINAR':
                print(f"[Worker {worker_id}] Sinal de término recebido. Encerrando.")
                break

            road = task_data['road']
            
            # Processa o segmento da estrada
            partial_results = run_na_sch_rules(
                road, start_index, end_index, v_max, p_slowdown
            )
            
            # Envia resultados parciais ao mestre
            comunicacao.send_msg(s, partial_results)
            
        print(f"[Worker {worker_id}] Desconectando.")

if __name__ == "__main__":
    # Inicia o worker quando o script é executado diretamente
    main()