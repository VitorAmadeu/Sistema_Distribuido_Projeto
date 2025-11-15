import time
import os
import csv
import numpy as np
import random
import socket
import threading
import comunicacao # Nosso módulo helper

# --- Parâmetros da Simulação ---
V_MAX = 5
P_SLOWDOWN = 0.3
HOST = '127.0.0.1'  # localhost
PORT = 65432

# --- Estado Global do Servidor ---
# (Armazena os resultados parciais de cada trabalhador)
worker_results_segments = {}
lock = threading.Lock()
barrier_calc = None # Será inicializado com o N de workers

def handle_worker(conn, worker_id, num_workers, road_length, sim_steps):
    """
    Função que cada thread do mestre usará para falar com um worker.
    """
    global worker_results_segments
    
    # 1. Calcular qual pedaço (chunk) este worker vai cuidar
    chunk_size = road_length // num_workers
    start_index = worker_id * chunk_size
    end_index = road_length if worker_id == num_workers - 1 else (worker_id + 1) * chunk_size

    print(f"[Mestre] Worker {worker_id} cuidará dos índices {start_index}-{end_index-1}")
    
    try:
        # 2. Enviar a tarefa de configuração inicial
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
        return # Encerra a thread

    # 3. Espera o sinal de "pronto" do worker
    # (Isso é implícito no primeiro recv() do loop)
    pass


def run_simulation_distributed(road_length, density, sim_steps, num_workers):
    """
    Executa UMA simulação distribuída e retorna o tempo.
    """
    global worker_results_segments, lock, barrier_calc
    
    # Reinicializa as barreiras e resultados para esta execução
    barrier_calc = threading.Barrier(num_workers)
    worker_results_segments = {}
    
    # 1. Inicialização da Estrada (no Mestre)
    road = np.full(road_length, -1)
    num_cars = int(road_length * density)
    if num_cars == 0: return 0.0
    car_positions = np.random.choice(road_length, num_cars, replace=False)
    road[car_positions] = np.random.randint(0, V_MAX + 1, num_cars)

    # 2. Configurar o Socket do Mestre e esperar conexões
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
            
            # Inicia uma thread para cuidar deste worker
            thread = threading.Thread(
                target=handle_worker, 
                args=(conn, i, num_workers, road_length, sim_steps)
            )
            thread.start()
            threads.append(thread)
            
    print(f"[Mestre] Todos os {num_workers} trabalhadores conectados. Iniciando simulação.")

    # --- Início da Medição de Tempo ---
    start_time = time.perf_counter()

    # 3. Loop Principal da Simulação (Mestre coordena)
    for step in range(sim_steps):
        
        # Limpa os resultados parciais
        worker_results_segments = {}
        
        # Tarefa para este passo
        task_data = {'road': road}
        
        # A. Enviar a ESTRADA ATUAL para TODOS os workers
        # (Este é o GARGALO de comunicação!)
        for conn in client_connections:
            comunicacao.send_msg(conn, task_data)

        # B. Receber os RESULTADOS PARCIAIS de TODOS os workers
        # (Cada thread 'handle_worker' faria isso, mas é mais simples aqui)
        # ... Esta lógica é complexa com threads.
        
        # Vamos simplificar: O handle_worker só faz a config.
        # O Mestre principal faz o loop de sim/comunicação.
        
        # --- REFAZENDO A LÓGICA DE COMUNICAÇÃO ---
        # A lógica de 'handle_worker' estava errada.
        # A thread 'handle_worker' deve rodar a *simulação inteira*.
        
        pass # Ver 'run_experiments_distributed' para a lógica correta
        
    # Esta função (run_simulation_distributed) é complexa.
    # Vamos delegar a lógica de loop para as threads 'handle_worker'
    # e apenas esperar elas terminarem.
    
    # O mestre só espera todas as threads terminarem
    for t in threads:
        t.join()
        
    end_time = time.perf_counter()
    # --- Fim da Medição de Tempo ---
    
    # Fechar conexões
    for conn in client_connections:
        conn.close()
        
    print("[Mestre] Simulação concluída.")
    return end_time - start_time

def handle_worker_full_loop(conn, worker_id, num_workers, road_length, sim_steps, road):
    """
    NOVA FUNÇÃO 'handle_worker'
    Esta thread agora gerencia o loop *inteiro* de simulação para um worker.
    """
    global worker_results_segments, lock, barrier_calc
    
    # !!! ADICIONE ESTE PRINT DE DEPURAÇÃO !!!
    print(f"[Debug-Thread-{worker_id}] Recebi sim_steps = {sim_steps}")
    
    # 1. Calcular chunk
    chunk_size = road_length // num_workers
    start_index = worker_id * chunk_size
    end_index = road_length if worker_id == num_workers - 1 else (worker_id + 1) * chunk_size

    print(f"[Mestre-Thread-{worker_id}] Cuidará de {start_index}-{end_index-1}")
    
    try:
        # 2. Enviar config
        task_config = {
            'id': worker_id, 'start_index': start_index, 'end_index': end_index,
            'sim_steps': sim_steps, 'v_max': V_MAX, 'p_slowdown': P_SLOWDOWN
        }
        comunicacao.send_msg(conn, task_config)

        # 3. Loop de Simulação
        for step in range(sim_steps):
            # A. Enviar a estrada atual para o worker
            # (O array 'road' é compartilhado entre as threads do mestre)
            task_data = {'road': road}
            comunicacao.send_msg(conn, task_data)
            
            # B. Receber o resultado parcial (o mapa de {pos: vel})
            partial_results = comunicacao.recv_msg(conn)
            if partial_results is None:
                print(f"[Mestre-Thread-{worker_id}] Worker desconectou inesperadamente.")
                break
            
            # C. Armazenar o resultado parcial (com segurança)
            with lock:
                worker_results_segments.update(partial_results)
            
            # D. Sincronizar (Barreira)
            # Espera TODOS os workers enviarem seus resultados
            barrier_calc.wait()
            
            # Apenas UMA thread (ex: a 0) monta o 'next_road'
            if worker_id == 0:
                # Cria o novo array 'road' para o próximo passo
                next_road = np.full(road_length, -1)
                
                # Preenche com os resultados de todos os workers
                for pos, vel in worker_results_segments.items():
                    next_road[pos] = vel
                
                # Atualiza o 'road' global para o próximo loop
                road[:] = next_road[:] # Atualização in-place
                
                # Limpa os resultados para o próximo ciclo
                worker_results_segments = {}
            
            # E. Sincronizar (Barreira)
            # Espera a thread 0 terminar de montar a nova 'road'
            # antes de enviar no próximo loop
            barrier_calc.wait() # Re-usa a mesma barreira
            
        # 4. Enviar sinal de término para o worker
        comunicacao.send_msg(conn, {'status': 'TERMINAR'})
        print(f"[Mestre-Thread-{worker_id}] Simulação terminada. Enviando sinal de fim.")

    except Exception as e:
        print(f"[Mestre-Thread-{worker_id}] Erro no loop: {e}")
    finally:
        conn.close()


def run_experiments_distributed():
    """Roda a bateria de testes distribuídos e salva em CSV."""
    global worker_results_segments, lock, barrier_calc
    
    print("Iniciando bateria de testes distribuídos (Sockets)...")

    # --- Configuração dos Testes ---
    comprimentos_estrada = [1000, 5000, 10000] # Menor, pois a com. é lenta
    densidades = [0.1, 0.3]
    passos_simulacao = 200
    lista_num_workers = [2, 4] # Testar com 2 e 4 workers
    
    resultados = []

    for num_w in lista_num_workers:
        for comp in comprimentos_estrada:
            for dens in densidades:
                
                print(f"  Testando: Workers={num_w}, Comp={comp}, Dens={dens}...")
                
                # 1. (RE)INICIALIZA barreiras e estado global
                barrier_calc = threading.Barrier(num_w)
                worker_results_segments = {}
                
                # 2. (RE)INICIALIZA estrada
                road = np.full(comp, -1)
                num_cars = int(comp * dens)
                if num_cars > 0:
                    car_pos = np.random.choice(comp, num_cars, replace=False)
                    road[car_pos] = np.random.randint(0, V_MAX + 1, num_cars)

                # 3. Abrir socket e esperar conexões
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
                        
                        # Inicia a thread que gerencia o worker
                        thread = threading.Thread(
                            target=handle_worker_full_loop, 
                            args=(conn, i, num_w, comp, passos_simulacao, road)
                        )
                        thread.start()
                        threads.append(thread)
                        
                print(f"[Mestre] Todos os {num_w} trabalhadores conectados. Medindo tempo.")
                
                # --- Início da Medição de Tempo ---
                start_time = time.perf_counter()

                # 4. Esperar todas as threads (e simulações) terminarem
                for t in threads:
                    t.join()
                    
                end_time = time.perf_counter()
                tempo = end_time - start_time
                # --- Fim da Medição de Tempo ---

                print(f"[Mestre] Simulação concluída.")
                print(f"    -> Tempo: {tempo:.4f} segundos")

                # Fechar conexões (já fechadas nas threads)
                
                # Armazena os resultados
                resultados.append([
                    f"Distribuido ({num_w} workers)",
                    comp, dens, passos_simulacao,
                    V_MAX, P_SLOWDOWN, num_w, tempo
                ])

    # --- Salvando os resultados em CSV ---
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
    run_experiments_distributed()