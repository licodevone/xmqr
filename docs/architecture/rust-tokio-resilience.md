# Como Rust + Tokio muda o perfil de falhas

Rust e Tokio não tornam um broker automaticamente seguro, mas removem ou isolam causas estruturais quando a arquitetura usa seus mecanismos corretamente.

## Rede e alta carga

Cada conexão é uma task leve, e o runtime multithread distribui tasks prontas entre workers. Uma conexão lenta fica suspensa aguardando I/O em vez de bloquear o processamento das demais. Isso só permanece verdadeiro se callbacks, filesystem, DNS e criptografia pesada não bloquearem workers; operações bloqueantes devem ir para um pool limitado ou um ator dedicado.

Admission control, semáforos e canais limitados tornam a capacidade explícita. Quando o limite é atingido, o broker rejeita ou aplica backpressure em vez de continuar alocando até o OOM.

## Segurança de memória

Ownership e bounds checking eliminam, em código Rust seguro, use-after-free, double-free, data races e buffer overflow clássicos de C/C++. Isso não elimina consumo lógico ilimitado, deadlocks, panic, `unsafe` incorreto ou vulnerabilidades de dependências. Este projeto proíbe `unsafe` no crate e limita entrada antes de alocar.

## Keep-alive e isolamento

Uma task por conexão possui sua própria máquina de estados e deadlines. Erros viram resultados locais; panics com unwind são capturados na fronteira da task. Um scheduler de deadlines ou timer wheel deve tratar grandes volumes de keep-alive sem varrer todas as conexões a cada tick.

## Persistência

O runtime assíncrono não corrige corrupção sozinho. Já existe uma [base de persistência](persistence.md) com escritor exclusivo fora dos workers Tokio, WAL com checksum, commit atômico por mutação e `fsync` antes da resposta, replay, snapshots com versão e testes de interrupção do processo. Ela ainda não está integrada às sessões MQTT. `fsync` configurável, transações multichave, rotação automática, testes de perda real de energia e a emissão de ACK condicionada ao commit continuam pendentes.

## Limite da comparação

O Mosquitto continua sendo uma implementação madura e útil; uma reimplementação nova começa com risco de incompatibilidade maior. A vantagem de Rust precisa ser demonstrada por matriz normativa, fuzzing, testes black-box e benchmarks, não apenas pela linguagem escolhida.
