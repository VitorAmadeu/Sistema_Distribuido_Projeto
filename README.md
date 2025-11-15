📈 Simulação de Tráfego (Modelo Nagel–Schreckenberg)

Este projeto implementa o modelo de autômatos celulares Nagel–Schreckenberg para simulação de tráfego. Ele foi desenvolvido para um trabalho de computação paralela e distribuída, comparando o desempenho de três arquiteturas:

Sequencial: Uma única thread de execução.

Paralela: Múltiplas threads (com threading) em memória compartilhada.

Distribuída: Múltiplos processos (com sockets) em memória distribuída.

🐍 Pré-requisitos

Para executar este projeto, você precisará de:

Python 3.x

Biblioteca numpy

Você pode instalar a biblioteca necessária executando:

Bash

pip install numpy

📁 Descrição dos Arquivos

Aqui está uma breve explicação de cada script Python no projeto:

Versão Sequencial

simulacao\_sequencial.py

O que faz: Implementação base (single-thread) do modelo NaSch.

Como funciona: Roda uma bateria de testes com diferentes tamanhos de estrada e densidades. Em cada passo da simulação, um único loop for calcula o novo estado de todos os veículos. Salva os resultados em arquivos/resultados\_sequencial.csv.

Versão Paralela (Threads)

simulacao\_paralela.py

O que faz: Implementação paralela usando o módulo threading.

Como funciona: Divide a "estrada" (um array numpy) em segmentos e atribui cada segmento a uma thread. Usa threading.Barrier para sincronizar todas as threads em dois pontos críticos:

Após o cálculo das novas posições (para evitar que uma thread leia dados antigos).

Após a atualização da estrada (para garantir que o próximo passo de tempo comece com um estado consistente).

Salva os resultados em arquivos/resultados\_paralelo.csv.

Versão Distribuída (Sockets)

Esta versão usa um padrão Mestre/Trabalhador e requer três arquivos:

servidor\_mestre.py (O Mestre)

O que faz: O "cérebro" da simulação distribuída.

Como funciona: Espera que um número N de Trabalhadores se conecte. Ele não faz o cálculo pesado. Em vez disso, ele:

Inicia uma bateria de testes.

Para cada teste, espera os N Trabalhadores.

Entra no loop de simulação e, em cada passo:

Envia a estrada inteira para todos os Trabalhadores (o gargalo de comunicação).

Recebe os resultados parciais (movimentos calculados) de cada Trabalhador.

Monta a nova estrada com os resultados.

Salva os tempos de execução em arquivos/resultados\_distribuido.csv.

worker.py (O Trabalhador)

O que faz: O "músculo" da simulação. Você deve rodar este script em múltiplos terminais.

Como funciona:

Conecta-se ao Mestre.

Recebe sua tarefa (ex: "Calcule as células 0 a 499").

Entra em um loop, esperando ordens do Mestre:

Recebe a estrada atual.

Calcula as 4 regras do NaSch apenas para o seu segmento da estrada.

Envia seu resultado parcial de volta ao Mestre.

Recebe um sinal de "TERMINAR" no final da simulação e se desconecta.

comunicacao.py

O que faz: Um módulo "helper" de utilidade.

Como funciona: Contém as funções send\_msg e recv\_msg. Enviar objetos complexos (como arrays numpy) por sockets é complicado. Este módulo usa pickle para serializar os objetos e struct para garantir que o receptor saiba exatamente quantos bytes de dados ele precisa ler, evitando corrupção de mensagens.

🚀 Como Executar

Siga estas instruções para rodar cada versão.

1. Executando a Versão Sequencial

Este é o mais simples. Abra um terminal e execute:

Bash

python simulacao\_sequencial.py

1. Executando a Versão Paralela

Igualmente simples. Em um terminal, execute:

Bash

python simulacao\_paralela.py

1. Executando a Versão Distribuída

Esta versão é mais complexa e exige múltiplos terminais.

Você deve primeiro decidir quantos trabalhadores testar (ex: 2 e 4). Edite esta linha no servidor\_mestre.py: lista\_num\_workers = [2, 4]

Siga este processo para cada bateria de teste (ex: primeiro para 2, depois para 4):

Terminal 1 (Inicie o Mestre): O Mestre irá iniciar e ficar "Esperando 2 trabalhadores...".

Bash

python servidor\_mestre.py

Terminal 2 (Inicie o Worker 1): Abra um novo terminal e inicie o primeiro trabalhador.

Bash

python worker.py

Terminal 3 (Inicie o Worker 2): Abra um terceiro terminal e inicie o segundo trabalhador.

Bash

python worker.py

A Simulação Começa! Assim que o segundo worker se conectar, o Mestre terá o número esperado de conexões e a simulação (o primeiro teste) começará. Você verá os logs em todos os terminais.

⚠️ IMPORTANTE: Bateria de Testes

O Mestre (servidor\_mestre.py) foi feito para rodar vários testes (diferentes densidades, comprimentos e números de workers) em um loop.

No entanto, os scripts worker.py terminam e morrem após cada simulação.

Isso significa que quando o Mestre terminar o primeiro teste e tentar rodar o segundo (ex: Testando: Workers=2, Comp=1000, Dens=0.3...), ele ficará "Esperando 2 trabalhadores..." novamente.

Você precisará reiniciar manualmente os scripts worker.py nos terminais 2 e 3 para CADA teste que o Mestre tentar rodar.

📊 Resultados

Todos os scripts de simulação (sequencial, paralelo e mestre) criarão automaticamente a pasta arquivos/ e salvarão seus respectivos resultados de desempenho em arquivos .csv:

arquivos/resultados\_sequencial.csv

arquivos/resultados\_paralelo.csv

arquivos/resultados\_distribuido.csv

🔬 Análise

A pasta analise/ contém os notebooks ou scripts (ex: Jupyter, Python com Matplotlib) usados para processar os arquivos .csv gerados.

Nesta pasta, é feita a comparação de desempenho entre os três algoritmos (sequencial, paralelo e distribuído), incluindo:

Análises Gráficas: Gráficos de tempo de execução, speedup e eficiência.

Análises Matemáticas: Cálculo de métricas de escalabilidade e discussão sobre os gargalos (como o GIL do Python e a latência da rede).



