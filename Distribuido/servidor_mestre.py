import time
import os
import csv
import numpy as np
import random
import socket
import threading
import comunicacao # Nosso módulo helper

# --- Parâmetros da Simulação ---
# Define constantes globais para a simulação do modelo Nagel-Schreckenberg
V_MAX = 5
P_SLOWDOWN = 0.3
HOST = '127.0.0.1'  # localhost
PORT = 65432

# --- Estado Global do Servidor ---
# Estruturas compartilhadas para coordenar resultados parciais entre threads
worker_results_segments = {}
lock = threading.Lock()
barrier_calc = None  # Inicializada dinamicamente com o número de workers

def handle_worker(conn, worker_id, num_workers, road_length, sim_steps):
    """
    Gerencia a comunicação inicial com um worker específico.
    Calcula o segmento da estrada atribuído ao worker e envia configuração.
    """
    global worker_results_segments
    
    # Calcula o segmento da estrada para este worker
    chunk_size = road_length // num_workers
    start_index = worker_id * chunk_size
    end_index = road_length if worker_id == num_workers - 1 else (worker_id + 1) * chunk_size

    print(f"[Mestre] Worker {worker_id} cuidará dos índices {start_index}-{end_index-1}")
    
    try:
        # Envia configuração inicial para o worker
        task_config = {
            'id': worker_id,
            'start_index': start_index,
            'end_index': end_index,
            'sim_steps': sim_steps,
            'v_max': V_MAX,
            'p_slowdown': P_SLOWDOWN
        }
        comunicacao.send_msg(conn, task_config)

    except Exception as e:
        print(f"[Mestre-Thread-{worker_id}] Erro ao enviar config: {e}")
        conn.close()
        return  # Encerra a thread


def run_simulation_distributed(road_length, density, sim_steps, num_workers):
    """
    Executa uma simulação distribuída completa e retorna o tempo de execução.
    Coordena múltiplos workers via sockets e threads.
    """
    global worker_results_segments, lock, barrier_calc
    
    # Reinicializa estruturas globais para esta execução
    barrier_calc = threading.Barrier(num_workers)
    worker_results_segments = {}
    
    # Inicializa a estrada com carros posicionados aleatoriamente
    road = np.full(road_length, -1)
    num_cars = int(road_length * density)
    if num_cars == 0: return 0.0
    car_positions = np.random.choice(road_length, num_cars, replace=False)
    road[car_positions] = np.random.randint(0, V_MAX + 1, num_cars)

    # Configura socket do servidor e aguarda conexões dos workers
    client_connections = []
    threads = []
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(num_workers)
        print(f"\n[Mestre] Esperando {num_workers} trabalhadores em {HOST}:{PORT}...")
        
        for i in range(num_workers):
            conn, addr = s.accept()
            print(f"[Mestre] Worker {i} (de {addr}) conectou.")
            client_connections.append(conn)
            
            # Inicia thread para gerenciar cada worker
            thread = threading.Thread(
                target=handle_worker, 
                args=(conn, i, num_workers, road_length, sim_steps)
            )
            thread.start()
            threads.append(thread)
            
    print(f"[Mestre] Todos os {num_workers} trabalhadores conectados. Iniciando simulação.")

    # Mede o tempo de execução da simulação
    start_time = time.perf_counter()

    # Loop principal da simulação - coordenado pelo mestre
    for step in range(sim_steps):
        
        # Limpa resultados parciais do passo anterior
        worker_results_segments = {}
        
        # Prepara dados da estrada para envio
        task_data = {'road': road}
        
        # Envia estado atual da estrada para todos os workers
        for conn in client_connections:
            comunicacao.send_msg(conn, task_data)

        # Recebe resultados parciais de todos os workers
        # Nota: Lógica simplificada; threads handle_worker gerenciam comunicação
        
        # Delegação: Threads handle_worker executam o loop completo
        pass  # Lógica delegada para threads
        
    # Aguarda conclusão de todas as threads
    for t in threads:
        t.join()
        
    end_time = time.perf_counter()
    
    # Fecha conexões
    for conn in client_connections:
        conn.close()
        
    print("[Mestre] Simulação concluída.")
    return end_time - start_time

def handle_worker_full_loop(conn, worker_id, num_workers, road_length, sim_steps, road):
    """
    Gerencia o loop completo de simulação para um worker específico.
    Coordena comunicação, cálculo parcial e sincronização via barreiras.
    """
    global worker_results_segments, lock, barrier_calc
    
    print(f"[Debug-Thread-{worker_id}] Recebi sim_steps = {sim_steps}")
    
    # Calcula o segmento da estrada atribuído a este worker
    chunk_size = road_length // num_workers
    start_index = worker_id * chunk_size
    end_index = road_length if worker_id == num_workers - 1 else (worker_id + 1) * chunk_size

    print(f"[Mestre-Thread-{worker_id}] Cuidará de {start_index}-{end_index-1}")
    
    try:
        # Envia configuração inicial ao worker
        task_config = {
            'id': worker_id, 'start_index': start_index, 'end_index': end_index,
            'sim_steps': sim_steps, 'v_max': V_MAX, 'p_slowdown': P_SLOWDOWN
        }
        comunicacao.send_msg(conn, task_config)

        # Loop principal da simulação para este worker
        for step in range(sim_steps):
            # Envia estado atual da estrada
            task_data = {'road': road}
            comunicacao.send_msg(conn, task_data)
            
            # Recebe resultados parciais do worker
            partial_results = comunicacao.recv_msg(conn)
            if partial_results is None:
                print(f"[Mestre-Thread-{worker_id}] Worker desconectou inesperadamente.")
                break
            
            # Armazena resultados com sincronização
            with lock:
                worker_results_segments.update(partial_results)
            
            # Sincroniza com outros workers
            barrier_calc.wait()
            
            # Thread principal (worker 0) consolida resultados
            if worker_id == 0:
                next_road = np.full(road_length, -1)
                
                # Atualiza estrada com contribuições de todos os workers
                for pos, vel in worker_results_segments.items():
                    next_road[pos] = vel
                
                # Atualiza estado global da estrada
                road[:] = next_road[:]
                
                # Limpa resultados para próximo passo
                worker_results_segments = {}
            
            # Sincroniza antes do próximo envio
            barrier_calc.wait()
            
        # Sinaliza término da simulação ao worker
        comunicacao.send_msg(conn, {'status': 'TERMINAR'})
        print(f"[Mestre-Thread-{worker_id}] Simulação terminada. Enviando sinal de fim.")

    except Exception as e:
        print(f"[Mestre-Thread-{worker_id}] Erro no loop: {e}")
    finally:
        conn.close()


def run_experiments_distributed():
    """Executa bateria de testes distribuídos e salva resultados em CSV."""
    global worker_results_segments, lock, barrier_calc
    
    print("Iniciando bateria de testes distribuídos (Sockets)...")

    # Configurações dos experimentos
    comprimentos_estrada = [1000, 5000, 10000]  # Tamanhos de estrada testados
    densidades = [0.1, 0.3]  # Densidades de tráfego
    passos_simulacao = 200  # Número de passos por simulação
    lista_num_workers = [2, 4]  # Número de workers a testar
    
    resultados = []

    for num_w in lista_num_workers:
        for comp in comprimentos_estrada:
            for dens in densidades:
                
                print(f"  Testando: Workers={num_w}, Comp={comp}, Dens={dens}...")
                
                # Reinicializa estruturas para cada teste
                barrier_calc = threading.Barrier(num_w)
                worker_results_segments = {}
                
                # Inicializa estrada com carros
                road = np.full(comp, -1)
                num_cars = int(comp * dens)
                if num_cars > 0:
                    car_pos = np.random.choice(comp, num_cars, replace=False)
                    road[car_pos] = np.random.randint(0, V_MAX + 1, num_cars)

                # Configura servidor e aguarda workers
                client_connections = []
                threads = []
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((HOST, PORT))
                    s.listen(num_w)
                    print(f"\n[Mestre] Esperando {num_w} trabalhadores em {HOST}:{PORT}...")
                    
                    for i in range(num_w):
                        conn, addr = s.accept()
                        print(f"[Mestre] Worker {i} (de {addr}) conectou.")
                        client_connections.append(conn)
                        
                        # Inicia thread para gerenciar worker
                        thread = threading.Thread(
                            target=handle_worker_full_loop, 
                            args=(conn, i, num_w, comp, passos_simulacao, road)
                        )
                        thread.start()
                        threads.append(thread)
                        
                print(f"[Mestre] Todos os {num_w} trabalhadores conectados. Medindo tempo.")
                
                # Mede tempo de execução
                start_time = time.perf_counter()

                # Aguarda conclusão das simulações
                for t in threads:
                    t.join()
                    
                end_time = time.perf_counter()
                tempo = end_time - start_time

                print(f"[Mestre] Simulação concluída.")
                print(f"    -> Tempo: {tempo:.4f} segundos")

                # Registra resultados
                resultados.append([
                    f"Distribuido ({num_w} workers)",
                    comp, dens, passos_simulacao,
                    V_MAX, P_SLOWDOWN, num_w, tempo
                ])

    # Salva resultados em CSV
    output_dir = "arquivos"
    output_file = os.path.join(output_dir, "resultados_distribuido.csv")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"\nSalvando resultados em '{output_file}'...")
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Tipo_Execucao", "Comprimento_Estrada", "Densidade", 
                "Passos_Simulacao", "V_Max", "P_Slowdown", 
                "Num_Workers", "Tempo_s"
            ])
            writer.writerows(resultados)
        print("Resultados salvos com sucesso.")
    except IOError as e:
        print(f"Erro ao salvar arquivo: {e}")

if __name__ == "__main__":
    # Executa os experimentos distribuídos quando o script é rodado diretamente
    run_experiments_distributed()