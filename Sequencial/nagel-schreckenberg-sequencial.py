# Algoritimo base -> https://gist.github.com/xmichaelx/2a3b45ba589296da73ef

import time
import os
import csv
import numpy as np
import random

# --- Parâmetros da Simulação ---
V_MAX = 5        # Velocidade máxima (células / passo)
P_SLOWDOWN = 0.3 # Probabilidade de desaceleração aleatória

def run_simulation(road_length, density, sim_steps):
    """
    Executa uma única simulação sequencial do modelo NaSch.

    Retorna: O tempo (em segundos) que a simulação levou.
    """
    
    # 1. Inicialização da Estrada
    # -1 representa uma célula vazia.
    # >= 0 representa um carro com aquela velocidade.
    road = np.full(road_length, -1)
    
    # Preenche a estrada com carros
    num_cars = int(road_length * density)
    if num_cars == 0:
        return 0.0 # Evita divisão por zero se a densidade for muito baixa

    # Escolhe posições aleatórias únicas para os carros
    car_positions = np.random.choice(road_length, num_cars, replace=False)
    
    # Atribui velocidades iniciais aleatórias (0 a V_MAX)
    road[car_positions] = np.random.randint(0, V_MAX + 1, num_cars)

    # Inicia a medição do tempo (APENAS o loop de simulação)
    start_time = time.perf_counter()

    # 2. Loop Principal da Simulação
    for _ in range(sim_steps):
        
        # Cria o array para o próximo estado da estrada
        # É essencial usar um buffer para não atualizar o estado "ao vivo"
        next_road = np.full(road_length, -1)
        
        # Itera por cada célula da estrada
        for i in range(road_length):
            
            # Se a célula NÃO tiver um carro, pule
            if road[i] == -1:
                continue

            # --- É um carro. Aplicar as 4 regras do NaSch ---
            
            v_atual = road[i]
            
            # Regra 0: Encontrar a distância (d) para o próximo carro
            # (Fazemos isso primeiro para aplicar as regras 1 e 2)
            distancia = 1
            # Procura na próxima célula em diante, com 'wrap-around' (estrada circular)
            while road[(i + distancia) % road_length] == -1:
                distancia += 1
                
                # Otimização: Se a distância for maior que V_MAX + 1,
                # não precisamos procurar mais, pois v_nova nunca passará de V_MAX.
                if distancia > V_MAX + 1:
                    break
            
            # --- Aplicação das Regras ---
            
            # Regra 1: Aceleração
            v_nova = min(v_atual + 1, V_MAX)
            
            # Regra 2: Desaceleração (Evitar Colisão)
            # A velocidade não pode ser maior que o espaço livre à frente (distancia - 1)
            v_nova = min(v_nova, distancia - 1)
            
            # Regra 3: Aleatorização (Comportamento Humano)
            if v_nova > 0 and random.random() < P_SLOWDOWN:
                v_nova = v_nova - 1
                
            # Regra 4: Movimento
            # Coloca o carro (com sua v_nova) na nova posição no array 'next_road'
            nova_posicao = (i + v_nova) % road_length
            next_road[nova_posicao] = v_nova

        # Atualiza a estrada 'atual' com o 'próximo' estado
        # O loop for recomeça com a estrada atualizada
        road = next_road

    # Para a medição do tempo
    end_time = time.perf_counter()
    
    return end_time - start_time

def run_experiments():
    """
    Roda a bateria de testes e salva os resultados em um CSV.
    """
    print("Iniciando bateria de testes sequenciais...")
    
    # --- Configuração dos Testes ---
    
    # Você pode aumentar isso para testes mais pesados
    # Lembre-se que o tempo cresce muito com o comprimento
    comprimentos_estrada = [1000, 5000, 10000, 20000] 
    
    # Densidades diferentes (0.1 = 10% de carros, 0.3 = 30%, etc.)
    densidades = [0.1, 0.3, 0.5]
    
    # Número de passos de tempo (iterações) para simular
    passos_simulacao = 200
    
    # --- Execução ---
    
    resultados = []
    
    for comp in comprimentos_estrada:
        for dens in densidades:
            
            print(f"  Testando: Comprimento={comp}, Densidade={dens}...")
            
            # Executa a simulação
            tempo = run_simulation(comp, dens, passos_simulacao)
            
            print(f"    -> Tempo: {tempo:.4f} segundos")
            
            # Armazena os resultados
            resultados.append([
                "Sequencial",
                comp,
                dens,
                passos_simulacao,
                V_MAX,
                P_SLOWDOWN,
                tempo
            ])

    # --- Salvando os resultados em CSV ---
    
    output_dir = "arquivos"
    output_file = os.path.join(output_dir, "resultados_sequencial.csv")
    
    # Cria o diretório 'arquivos' se ele não existir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"\nSalvando resultados em '{output_file}'...")
    
    # Escreve o cabeçalho e as linhas de dados
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
                "Tempo_s"
            ])
            
            # Dados
            writer.writerows(resultados)
            
        print("Resultados salvos com sucesso.")
        
    except IOError as e:
        print(f"Erro ao salvar arquivo: {e}")

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    # Instala o numpy se não estiver instalado
    try:
        import numpy
    except ImportError:
        print("Biblioteca 'numpy' não encontrada. Instalando...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
        print("Numpy instalado com sucesso.")

    # Roda os experimentos
    run_experiments()