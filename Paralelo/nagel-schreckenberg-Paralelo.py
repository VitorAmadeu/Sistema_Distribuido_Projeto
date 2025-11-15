import time
import os
import csv
import numpy as np
import random
import threading

# --- Parâmetros da Simulação (iguais ao sequencial) ---
V_MAX = 5
P_SLOWDOWN = 0.3

def worker_thread(thread_id, num_threads, road_length, sim_steps, road, next_road, barrier_calc, barrier_copy):
    """
    Função que cada thread executará.
    Ela processa apenas o seu "pedaço" (chunk) da estrada.
    """
    
    # 1. Calcular qual pedaço da estrada esta thread vai cuidar
    chunk_size = road_length // num_threads
    start_index = thread_id * chunk_size
    
    # A última thread pega todo o resto (caso não seja divisível)
    end_index = road_length if thread_id == num_threads - 1 else (thread_id + 1) * chunk_size

    # --- Loop de Simulação (dentro da thread) ---
    for _ in range(sim_steps):
        
        # --- FASE 1: CÁLCULO ---
        # A thread só itera sobre o SEU PEDAÇO
        for i in range(start_index, end_index):
            
            # Se a célula NÃO tiver um carro, pule
            if road[i] == -1:
                continue

            # --- É um carro. Aplicar as 4 regras do NaSch ---
            v_atual = road[i]
            
            # Regra 0: Encontrar a distância (d) para o próximo carro
            distancia = 1
            # A thread LÊ o array 'road' global (o que é seguro)
            # Ela pode precisar ler "além" do seu pedaço
            while road[(i + distancia) % road_length] == -1:
                distancia += 1
                if distancia > V_MAX + 1:
                    break
            
            # Regra 1: Aceleração
            v_nova = min(v_atual + 1, V_MAX)
            
            # Regra 2: Desaceleração (Evitar Colisão)
            v_nova = min(v_nova, distancia - 1)
            
            # Regra 3: Aleatorização
            if v_nova > 0 and random.random() < P_SLOWDOWN:
                v_nova = v_nova - 1
                
            # Regra 4: Movimento
            nova_posicao = (i + v_nova) % road_length
            
            # A thread ESCREVE no array global 'next_road'
            # Isso é seguro, pois cada thread é "dona" do carro 'i'
            next_road[nova_posicao] = v_nova

        # --- FIM DA FASE 1 ---

        # Sincronização: Espera todas as threads terminarem o CÁLCULO
        barrier_calc.wait()
        
        # --- FASE 2: CÓPIA ---
        # Agora que 'next_road' está completo, copiamos de volta para 'road'
        # Cada thread copia o seu próprio pedaço para manter o paralelismo
        
        # Limpa o pedaço do 'road' antes de copiar
        road[start_index:end_index] = -1 
        
        # Copia apenas os carros que "aterrissaram" no seu pedaço
        for i in range(start_index, end_index):
             if next_road[i] != -1:
                road[i] = next_road[i]
                next_road[i] = -1 # Limpa para o próximo ciclo

        # --- FIM DA FASE 2 ---
        
        # Sincronização: Espera todas as threads terminarem a CÓPIA
        # antes de começar o próximo passo da simulação
        barrier_copy.wait()


def run_simulation_parallel(road_length, density, sim_steps, num_threads):
    """
    Executa uma única simulação paralela com 'num_threads'.
    """
    
    # 1. Inicialização da Estrada (igual ao sequencial)
    road = np.full(road_length, -1)
    num_cars = int(road_length * density)
    if num_cars == 0:
        return 0.0

    car_positions = np.random.choice(road_length, num_cars, replace=False)
    road[car_positions] = np.random.randint(0, V_MAX + 1, num_cars)
    
    # O array 'next_road' também é compartilhado
    next_road = np.full(road_length, -1)

    # 2. Configuração das Threads e Barreiras
    threads = []
    
    # Barreiras para 'num_threads' threads
    barrier_calc = threading.Barrier(num_threads)
    barrier_copy = threading.Barrier(num_threads)

    # 3. Criar as threads
    for i in range(num_threads):
        # O 'target' é a função que a thread vai rodar
        # 'args' são os argumentos passados para essa função
        t = threading.Thread(
            target=worker_thread, 
            args=(i, num_threads, road_length, sim_steps, road, next_road, barrier_calc, barrier_copy)
        )
        threads.append(t)

    # Inicia a medição do tempo
    start_time = time.perf_counter()

    # 4. Iniciar as threads
    for t in threads:
        t.start()

    # 5. Esperar que TODAS as threads terminem
    for t in threads:
        t.join() # O 'join' bloqueia a thread principal até que 't' termine

    # Para a medição do tempo
    end_time = time.perf_counter()

    return end_time - start_time

def run_experiments_parallel():
    """
    Roda a bateria de testes paralelos e salva os resultados em um CSV.
    """
    print("Iniciando bateria de testes paralelos (Threads)...")
    
    # --- Configuração dos Testes ---
    comprimentos_estrada = [1000, 5000, 10000, 20000] 
    densidades = [0.1, 0.3, 0.5]
    passos_simulacao = 200
    
    # Vamos testar com diferentes números de threads
    lista_num_threads = [2, 4, 8] 
    
    # --- Execução ---
    
    resultados = []
    
    for num_t in lista_num_threads:
        for comp in comprimentos_estrada:
            for dens in densidades:
                
                print(f"  Testando: Threads={num_t}, Comp={comp}, Dens={dens}...")
                
                # Executa a simulação
                tempo = run_simulation_parallel(comp, dens, passos_simulacao, num_t)
                
                print(f"    -> Tempo: {tempo:.4f} segundos")
                
                # Armazena os resultados
                resultados.append([
                    f"Paralelo ({num_t} threads)",
                    comp,
                    dens,
                    passos_simulacao,
                    V_MAX,
                    P_SLOWDOWN,
                    num_t,
                    tempo
                ])

    # --- Salvando os resultados em CSV ---
    
    output_dir = "arquivos"
    output_file = os.path.join(output_dir, "resultados_paralelo.csv")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"\nSalvando resultados em '{output_file}'...")
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Cabeçalho
            writer.writerow([
                "Tipo_Execucao",
                "Comprimento_Estrada", 
                "Densidade", 
                "Passos_Simulacao",
                "V_Max",
                "P_Slowdown",
                "Num_Threads",
                "Tempo_s"
            ])
            
            # Dados
            writer.writerows(resultados)
            
        print("Resultados salvos com sucesso.")
        
    except IOError as e:
        print(f"Erro ao salvar arquivo: {e}")

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    run_experiments_parallel()