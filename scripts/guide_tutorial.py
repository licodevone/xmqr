"""Conteúdo humano do percurso didático P65; exemplos independentes do runtime."""
from html import escape
from pathlib import Path
import tomllib


HELLO = '''fn main() {
    println!("Meu primeiro programa Rust");
}
'''

BROKER = '''use std::io::{Read, Write};
use std::net::TcpListener;

fn main() -> std::io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:18830")?;
    println!("TCP de estudo em 127.0.0.1:18830");
    for connection in listener.incoming() {
        let mut stream = connection?;
        let mut buffer = [0_u8; 512];
        loop {
            let count = stream.read(&mut buffer)?;
            if count == 0 {
                break;
            }
            stream.write_all(&buffer[..count])?;
        }
    }
    Ok(())
}
'''

CLIENT = '''use std::io::{Read, Write};
use std::net::TcpStream;

fn main() -> std::io::Result<()> {
    let mut stream = TcpStream::connect("127.0.0.1:18830")?;
    stream.write_all(b"ping")?;
    let mut response = [0_u8; 4];
    stream.read_exact(&mut response)?;
    println!("Resposta: {}", String::from_utf8_lossy(&response));
    Ok(())
}
'''

# Checkpoints completos: o aluno os constrói por incrementos, sem copiar blocos.
TYPING_STEPS = [
    ('Função de entrada', 'fn main() {\n}\n', ''),
    ('Primeira saída', 'fn main() {\n    println!("Curso MQTT");\n}\n', 'Curso MQTT\n'),
    ('Guardar uma informação', 'fn main() {\n    let temperatura = 5;\n    println!("Temperatura: {}", temperatura);\n}\n', 'Temperatura: 5\n'),
    ('Tomar uma decisão', '''fn main() {
    let temperatura = 5;
    if temperatura > 4 {
        println!("Alerta: temperatura alta");
    } else {
        println!("Temperatura dentro do limite");
    }
}
''', 'Alerta: temperatura alta\n'),
]


def code(value, language='text'):
    return '<pre data-language="' + language + '"><code>' + escape(value) + '</code></pre>'


def p(value):
    return '<p>' + value + '</p>'


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>' + escape(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + escape(str(v)) + '</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def card(title, body):
    return '<article class="card filter"><h3>' + escape(title) + '</h3>' + body + '</article>'


def annotated(source, explanations):
    assert len(source.splitlines()) == len(explanations)
    return table(['Linha', 'Código exato', 'Explicação humana'], [(n, line, explanation) for n, (line, explanation) in enumerate(zip(source.splitlines(), explanations), 1)])


def sections(root):
    result = []
    def add(identifier, title, body):
        result.append((identifier, title, body))

    add('curso', 'Da lógica ao Broker e Clientes MQTT utilizando Rust — como estudar',
        p('O objetivo do curso é você escrever o programa com suas próprias mãos e compreender o que está construindo. A digitação acompanha a lógica: primeiro defina o problema, depois escolha a instrução e entenda suas palavras e símbolos. O código completo serve para conferir seu trabalho depois da tentativa.') +
        p('<strong>Caminho principal:</strong> construir os exercícios em uma pasta nova, digitando os trechos. O sistema pronto fica como referência posterior. A sequência didática foi organizada para aprendizado; não representa uma reconstrução comprovada de todos os commits antigos. Os prompts e seus registros históricos estão mais adiante.') +
        table(['Ordem', 'O que você construirá', 'Quando considerar concluído'], [
            ('1', 'Ambiente Linux/WSL e ferramentas Rust', 'rustc e cargo mostram suas versões dentro do Ubuntu.'),
            ('2', 'broker-escola e client-escola', 'Cada projeto imprime sua mensagem e compila sem dependências.'),
            ('3', 'Servidor e cliente TCP de estudo', 'O client recebe ping de volta; você consegue explicar cada linha.'),
            ('4', 'Tipos, módulos e decodificador MQTT', 'Bytes válidos são interpretados e pacotes inválidos são recusados.'),
            ('5', 'CONNECT, assinaturas e publicação QoS 0', 'Um publicador entrega mensagem a um assinante e ACL negativa recusa acesso.'),
            ('6', 'QoS 1/2, sessão, retained e Will', 'Transições, reconexão e reinício têm testes próprios.'),
            ('7', 'Persistência, TLS/mTLS e autenticação', 'Responsabilidade durável e acesso autorizado sobrevivem aos cenários previstos.'),
            ('8', 'Configuração, cliente CLI, operação e distribuição', 'Gates e artefatos verificáveis; release experimental com limites documentados.')]) +
        p('Não precisa criar uma biblioteca para cada conceito. O XMQR é um pacote com módulos, dois binários no broker e um pacote separado para o client. MQTT 5, WebSocket, bridge e cluster não estão implementados nesta baseline. A paridade integral com Mosquitto permanece um objetivo futuro.'))

    add('metodo-digitacao', 'Seu método: digitar, compreender e verificar',
        table(['Passo em cada aula', 'O que você faz', 'Como comprova compreensão'], [
            ('1. Problema', 'Descreva o comportamento desejado sem código.', 'Diga qual informação entra, o que é feito e qual resultado sai.'),
            ('2. Lógica', 'Escreva passos em português ou pseudocódigo.', 'Simule o resultado com valores pequenos.'),
            ('3. Local', 'Abra o arquivo indicado e confira a pasta/projeto.', 'Saiba distinguir código Rust, manifest e comando no terminal.'),
            ('4. Digitação', 'Digite uma instrução curta, observando maiúsculas, aspas e delimitadores.', 'Identifique palavras da linguagem, nomes escolhidos e dados.'),
            ('5. Leitura', 'Explique a instrução antes de executar.', 'Responda: o que acontece, por que ela existe e qual tipo participa?'),
            ('6. Checkpoint', 'Complete o bloco indicado, salve e execute.', 'Compare saída real com a previsão; registre a primeira divergência.'),
            ('7. Variação', 'Mude apenas um dado ou operação proposta.', 'Preveja a diferença antes de rodar novamente.'),
            ('8. Revisão', 'Explique o trecho em voz alta ou escreva uma frase.', 'Só avance quando conseguir justificar cada token relevante.')]) +
        p('Uma letra pode pertencer a uma palavra reservada, a um identificador ou a um texto literal. Em fn, as letras juntas formam a palavra da linguagem. Em temperatura, o nome foi escolhido por nós: temp também seria possível se todas as referências mudassem. Dentro de uma string, as letras são dados exibidos. Não há uma função independente para cada letra desses nomes.') +
        p('Pode haver erro enquanto uma linha ou bloco está incompleto. Execute nos checkpoints completos, em vez de compilar depois de cada tecla. Indentação facilita leitura; espaços entre tokens podem ser necessários para separá-los. Diferencie isso de espaços dentro de strings, que fazem parte da mensagem.') +
        p('Se houver erro: confirme o arquivo e o diretório; leia a primeira mensagem; compare aspas, chaves, nome e tipo com o trecho da aula; corrija uma causa por vez. Não troque uma biblioteca ou desative validações apenas para fazer o erro desaparecer.') +
        p('<strong>Estado deste material:</strong> as primeiras aulas abaixo têm checkpoints e explicações humanas. Os módulos avançados têm roteiro, critérios e fontes para consulta. Suas notas assistidas ainda precisam ser transformadas em aulas humanas próprias; elas não equivalem a um curso completo de digitação guiada de todas as linhas.'))

    add('tutor-ia', 'Como usar inteligência artificial durante a digitação',
        p('A proposta deste curso é usar IA como tutor de uma etapa por vez. Você continua responsável por escrever, explicar e verificar o programa. Essa escolha acompanha a orientação geral de educação centrada na participação humana da <a href="https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research">UNESCO sobre IA generativa na educação</a>; o roteiro abaixo é uma adaptação didática para este curso, não uma metodologia validada integralmente por essa fonte.') +
        table(['Momento', 'Pedido ao tutor', 'Sua ação'], [
            ('Antes de digitar', 'Explique o problema e faça uma pergunta sobre a lógica, sem escrever a solução inteira.', 'Responda com passos em português.'),
            ('Ao escrever', 'Mostre uma instrução pequena e explique palavras, símbolos, tipos e propósito.', 'Digite manualmente; diga o que é palavra reservada, nome e dado.'),
            ('Antes de executar', 'Pergunte qual saída eu espero.', 'Registre sua previsão antes de compilar.'),
            ('Quando houver erro', 'Analise a primeira mensagem do compilador e ofereça uma pista antes da correção.', 'Tente corrigir a causa e compare a saída.'),
            ('Depois de funcionar', 'Peça que eu explique a linha e proponha uma pequena variação.', 'Explique sem ler a resposta e execute a variação.'),
            ('Ao revisar', 'Faça perguntas sem fornecer código e registre onde tive dificuldade.', 'Reconstrua um trecho de memória; avance após comprovar entendimento.')]) +
        card('Prompt para iniciar uma aula',
            code('Você é meu tutor no curso Da lógica ao Broker e Clientes MQTT utilizando Rust.\nEstou na aula [nome], usando Rust [versão] no Ubuntu/WSL.\nQuero digitar o código e entender cada passo.\nApresente um objetivo pequeno e pergunte como eu resolveria em português.\nDepois, trabalhe uma instrução por vez: explique palavras, símbolos e tipos.\nEspere minha resposta antes de avançar.\nAntes de executar, peça minha previsão do resultado.\nQuando eu mostrar um erro, dê primeiro uma pista para eu tentar corrigi-lo.\nNão entregue o programa completo nem afirme que testou sem executar.\nNo fim, peça minha explicação e uma variação curta.', 'text') +
            p('Substitua nome e versão pelo contexto real. Use uma conversa por aula ou informe o checkpoint atual para o tutor não pular etapas. A IA pode explicar incorretamente uma API: confirme comportamento no compilador, nos testes e nas fontes oficiais já vinculadas ao curso.')) +
        card('Preparação das aulas pelo professor',
            p('Use IA para propor explicações alternativas, perguntas, erros didáticos e exercícios. Revise o conteúdo e execute o checkpoint antes de gravar a aula. Durante a demonstração, mostre seu raciocínio, a pergunta feita ao tutor e a verificação no terminal; a resposta da IA não é prova de correção.') +
            p('Para avaliar, peça ao aluno que preveja uma saída, explique um token, corrija um erro e adapte uma regra. Digitar o mesmo texto é parte da prática; a explicação e a aplicação mostram se ele entendeu. Este HTML contém orientações e prompts, sem conexão automática com serviço de IA.')))

    body = p('Faça estas aulas depois de instalar Rust e criar broker-escola na Etapa 2. Abra broker-escola/src/main.rs no editor. Os blocos mostram como o arquivo ficará em cada checkpoint; digite as alterações indicadas. No terminal Ubuntu, dentro de broker-escola, execute cargo +1.99.0 run depois de salvar.')
    body += card('Aula 1 — onde o programa começa',
        p('<strong>Lógica:</strong> iniciar e terminar, sem imprimir nada. Substitua o Hello inicial por uma função vazia. Digite fn, um espaço, main, os parênteses, um espaço e a chave de abertura. Pressione Enter e digite a chave de fechamento.') +
        code(TYPING_STEPS[0][1], 'rust') +
        table(['O que você digita', 'O que significa', 'Por que precisa estar aqui'], [
            ('fn', 'Palavra reservada que declara função.', 'Informa ao compilador qual construção começa aqui.'),
            ('main', 'Nome especial da entrada deste executável.', 'O programa inicia por essa função.'),
            ('()', 'Lista de parâmetros vazia.', 'Esta entrada não recebe parâmetros na assinatura.'),
            ('{', 'Início do corpo.', 'Delimita o conjunto de instruções da função.'),
            ('Enter / indentação', 'Organização visual do texto.', 'Ajuda a enxergar estrutura; não substitui os delimitadores.'),
            ('}', 'Fim do corpo.', 'Fecha o bloco iniciado pela chave anterior.')]) +
        p('<strong>Checkpoint:</strong> execução termina sem mensagem do seu programa. Cargo ainda pode mostrar mensagens de compilação/execução. <strong>Explique:</strong> por que não apareceu texto? Porque ainda não há instrução que imprima.'))
    body += card('Aula 2 — sua primeira instrução',
        p('<strong>Lógica:</strong> iniciar → escrever Curso MQTT na tela → terminar. Dentro das chaves, digite quatro espaços e println!("Curso MQTT");. A mensagem é livre; a estrutura Rust precisa continuar válida.') +
        code(TYPING_STEPS[1][1], 'rust') +
        table(['Parte', 'O que faz'], [('println', 'Nome da macro de impressão com nova linha.'), ('!', 'Nesta posição indica invocação de macro.'), ('(', 'Abre os argumentos da macro.'), ('"', 'Abre o literal de texto.'), ('Curso MQTT', 'Conteúdo a exibir; o espaço também pertence ao texto.'), ('"', 'Fecha o literal.'), (')', 'Fecha os argumentos.'), (';', 'Termina esta instrução dentro do bloco.')]) +
        p('<strong>Checkpoint:</strong> a saída do programa é Curso MQTT. <strong>Variação:</strong> mude apenas o texto para Meu broker e preveja a saída. <strong>Explique:</strong> por que uma palavra dentro de aspas pode mudar, mas remover a aspa de fechamento causa erro?'))
    body += card('Aula 3 — guardar um valor',
        p('<strong>Lógica:</strong> guardar temperatura 5 → mostrar valor guardado. Digite let temperatura = 5; antes da impressão. Depois altere a impressão para usar um marcador de formatação e a variável como segundo argumento.') +
        code(TYPING_STEPS[2][1], 'rust') +
        table(['Parte', 'Leitura'], [('let', 'Cria um binding: associa nome a valor.'), ('temperatura', 'Identificador escolhido por nós; não é palavra reservada.'), ('=', 'Inicializa o binding com o valor à direita.'), ('5', 'Literal numérico; neste exemplo o inteiro é inferido como i32.'), (';', 'Encerra a declaração.'), ('"Temperatura: {}"', 'Texto de formatação; {} reserva posição para o argumento.'), (', temperatura', 'Separa argumentos e fornece o valor que ocupa {}.')]) +
        p('<strong>Checkpoint:</strong> Temperatura: 5. <strong>Variação:</strong> troque 5 por 2 e preveja a saída. <strong>Explique:</strong> por que "temperatura" imprimiria letras, enquanto temperatura sem aspas fornece o valor?'))
    body += card('Aula 4 — tomar uma decisão',
        p('<strong>Problema:</strong> avisar quando a temperatura ultrapassar 4. Primeiro escreva a lógica em português: guardar valor; se for maior que 4, mostrar alerta; caso contrário, mostrar que está dentro do limite. O número vem do código de estudo; ainda não existe sensor físico.') +
        code(TYPING_STEPS[3][1], 'rust') +
        table(['Parte', 'Leitura'], [('if', 'Inicia decisão condicional.'), ('temperatura > 4', 'Compara o valor guardado com 4; produz true ou false.'), ('{ … } depois do if', 'Bloco executado se a comparação for verdadeira.'), ('else', 'Escolhe o caso alternativo quando a condição é falsa.'), ('{ … } depois do else', 'Bloco executado no caso alternativo.'), ('Chave final', 'Fecha main; as outras duas duplas pertencem aos ramos da decisão.')]) +
        p('<strong>Checkpoint:</strong> com 5, aparece Alerta: temperatura alta. <strong>Variações:</strong> preveja o resultado com 3 e com 4. Igual a 4 não satisfaz > 4. Depois compare a regra > com >=; só altere a regra depois de explicar o comportamento desejado.'))
    body += card('Ponte para o broker e os clients',
        p('Você já construiu entrada, saída, dado e decisão. No exercício TCP, o dado atravessa uma conexão. No MQTT, além de enviar bytes, identificamos sessão, tópico e confirmação. A regra de temperatura pertence à aplicação consumidora; o broker transporta e roteia mensagens sem precisar conhecer esse alarme.') +
        p('Ao chegar à Etapa 3, mantenha o método: escreva imports; explique std, :: e os traits; complete a assinatura; construa bind e analise o Result; só depois acrescente atendimento e leitura. A tabela humana de cada linha do servidor/client mostra a função de cada instrução.') +
        table(['Trecho de rede para destrinchar', 'Como ler seus tokens'], [
            ('let listener = TcpListener::bind("127.0.0.1:18830")?;', 'let associa nome; TcpListener é tipo; :: acessa função associada; bind abre listener; literal contém endereço; ? propaga erro; ; encerra.'),
            ('let mut buffer = [0_u8; 512];', 'let cria binding; mut permite alterar; [ ] forma array; 0_u8 é zero de tipo byte; ; interno separa valor e quantidade; ; final encerra declaração.'),
            ('stream.read(&mut buffer)?', 'stream é conexão; . chama método; &mut empresta buffer com exclusividade de mutação; ? propaga erro da leitura.'),
            ('&buffer[..count]', '& empresta fatia; [ ] seleciona trecho; ..count inclui início e exclui índice count.'),
            ('for connection in listener.incoming()', 'for itera resultados; connection recebe cada item; in liga padrão e iterador; incoming produz conexões recebidas.')]))
    add('aulas-digitadas', 'Primeiras aulas — escreva cada trecho e explique seus tokens', body)

    add('ambiente', 'Etapa 1 — instalar Rust e entender o ambiente',
        card('No Windows: entrar no Ubuntu do WSL',
            p('Abra PowerShell e confira o nome da distribuição. Os dois comandos abaixo pertencem ao Windows. Se o nome instalado for diferente, use o nome exibido na listagem.') +
            code('wsl -l -v\nwsl -d Ubuntu-26.04', 'powershell') +
            table(['Parte', 'Significado'], [('wsl', 'Programa Windows que gerencia/abre as distribuições Linux.'), ('-l', 'Lista as distribuições instaladas.'), ('-v', 'Mostra detalhes, inclusive WSL 1 ou 2.'), ('-d Ubuntu-26.04', 'Seleciona a distribuição de nome Ubuntu-26.04; não é um caminho.')]) +
            p('Depois que aparecer o terminal Ubuntu, siga os blocos Bash. O Rust instalado no Windows e o Rust instalado no Ubuntu são instalações distintas. Este curso usa Ubuntu/WSL como caminho principal, pois os testes operacionais do broker foram validados ali.')) +
        card('Dentro do Ubuntu: preparar compilação e instalar',
            code('sudo apt update\nsudo apt install build-essential cmake pkg-config perl git curl ca-certificates\ncurl --proto \'=https\' --tlsv1.2 -sSf https://sh.rustup.rs | sh\nsource "$HOME/.cargo/env"\nrustc --version\ncargo --version\nrustup --version', 'bash') +
            p('O instalador oficial fornece rustup, rustc e Cargo. rustup gerencia toolchains; rustc compila Rust; Cargo organiza pacote, dependências e tarefas. O instalador acrescenta ~/.cargo/bin ao PATH; source atualiza o terminal atual. No Windows nativo, o instalador é rustup-init.exe e a toolchain MSVC requer ferramentas C++ do Visual Studio. <a href="https://rust-lang.org/tools/install/">Instalação oficial Rust</a>.') +
            table(['Comando / componente', 'Por que está aqui'], [
                ('sudo', 'Executa a operação administrativa com as permissões necessárias.'), ('apt update', 'Atualiza o índice de pacotes; não instala a atualização do sistema inteiro.'), ('apt install', 'Instala os pacotes indicados.'), ('build-essential', 'Compilador/linker e ferramentas para dependências nativas.'), ('cmake / perl / pkg-config', 'Apoio a builds e descoberta de bibliotecas nativas, inclusive backend criptográfico.'), ('git', 'Obtém e versiona código.'), ('curl / ca-certificates', 'Download HTTPS e certificados confiáveis do ambiente.'), ("--proto '=https'", 'Restringe os protocolos usados pelo curl a HTTPS.'), ('--tlsv1.2', 'Exige pelo menos TLS 1.2 no download.'), ('-sSf', 'Agrupa silent, show-error e fail do curl.'), ('| sh', 'Entrega o script baixado ao interpretador para executá-lo.'), ('source', 'Avalia arquivo no shell atual.'), ('$HOME', 'Expansão do diretório pessoal pelo Bash; não é texto literal entre aspas duplas.'), ('--version', 'Solicita a versão do programa que recebe a opção.')])) +
        card('Fixar a referência usada nas validações do projeto',
            code('rustup toolchain install 1.99.0 --profile minimal\nrustup component add rustfmt clippy --toolchain 1.99.0\ncargo +1.99.0 --version', 'bash') +
            p('1.99.0 é a referência verificada nos registros Ubuntu/WSL desta baseline, não uma afirmação de versão mais recente. +1.99.0 seleciona essa toolchain por comando. O manifest declara rust-version=1.88, mas a versão mínima exata ainda não foi homologada. Rustfmt formata; Clippy detecta problemas. --profile minimal instala o conjunto mínimo da toolchain.') +
            p('Pacotes .deb publicados foram validados para Ubuntu 26.04 amd64. Ubuntu 24.04, outras arquiteturas e broker nativo Windows exigem validação própria; compartilhar Linux ou Docker não garante compatibilidade do binário, da libc, dos scripts ou da configuração.')))

    add('primeiro', 'Etapa 2 — criar seus primeiros dois projetos',
        p('Dentro do Ubuntu, use uma pasta nova de exercícios. Não execute cargo new sobre os repositórios existentes. Os nomes escola distinguem seus exercícios dos binários distribuídos.') +
        code('mkdir -p "$HOME/xmqr-estudo"\ncd "$HOME/xmqr-estudo"\ncargo +1.99.0 new --bin broker-escola\ncargo +1.99.0 new --bin client-escola\ncd broker-escola\ncargo +1.99.0 run', 'bash') +
        p('Cargo cria Cargo.toml e src/main.rs. Abra src/main.rs, substitua seu conteúdo pelo exemplo abaixo e execute cargo run novamente. Cargo build gera o executável; cargo check verifica o código; cargo run compila e executa. Cargo.lock registra versões resolvidas e target guarda artefatos gerados. <a href="https://doc.rust-lang.org/book/ch01-03-hello-cargo.html">Rust Book: Hello Cargo</a>.') +
        code(HELLO, 'rust') + annotated(HELLO, [
            'fn declara função; main é a entrada do executável; () indica nenhum parâmetro; { abre seu corpo.',
            'println! é uma macro de impressão. Aspas delimitam o texto. () contém o argumento e ; encerra a instrução.',
            '} fecha o corpo. Esta função não especifica retorno: seu resultado é a unidade ().']) +
        table(['Arquivo/pasta', 'Você escreve?', 'Responsabilidade'], [
            ('Cargo.toml', 'Sim', 'Manifest: metadados, edição, dependências e opções de compilação.'), ('src/main.rs', 'Sim', 'Entrada de cada executável.'), ('src/lib.rs', 'Quando extrair biblioteca interna', 'Exporta módulos reutilizados por binários e testes.'), ('Cargo.lock', 'Cargo gera', 'Resolução concreta das dependências; versionar nos aplicativos.'), ('target/', 'Não manualmente', 'Executáveis e intermediários; não é fonte do sistema.'), ('.gitignore', 'Sim quando necessário', 'Ignora builds e arquivos que não devem entrar no Git.')]) +
        p('Agora entre em ../client-escola e repita o Hello. Só continue quando ambos compilarem. Se cargo não for encontrado, confirme o terminal e reabra-o após a instalação. Se faltar linker, volte às ferramentas de compilação; trocar o código Rust não resolve a ausência de ferramenta do sistema.'))

    add('tcp-escola', 'Etapa 3 — aprender rede com servidor e cliente TCP',
        p('<strong>Este exercício é um eco TCP, ainda não MQTT.</strong> Não tem autenticação, concorrência, timeout nem persistência. Escuta somente no loopback e usa porta 18830 para não disputar 1883/8883 com o broker real. Ele mostra como bytes atravessam a rede antes de acrescentarmos protocolo.') +
        card('Servidor: substitua broker-escola/src/main.rs', code(BROKER, 'rust') + annotated(BROKER, [
            'Importa os traits Read e Write: disponibilizam métodos de leitura e escrita nos streams.',
            'Importa TcpListener da biblioteca padrão; std não requer dependência no Cargo.toml.',
            'Linha em branco separa imports e função para leitura.',
            'A função retorna Result: Ok(()) no sucesso ou io::Error. -> separa assinatura e retorno.',
            'bind abre o listener. let cria binding; ? devolve erro ao chamador se não conseguir abrir a porta.',
            'Imprime o endereço para o operador saber onde o exercício escuta.',
            'incoming fornece conexões sucessivas; for trata cada resultado, uma conexão por vez.',
            'Extrai a conexão ou propaga erro. mut permite operações que alteram o estado do stream.',
            'Array de 512 bytes inicializados em zero. u8 é inteiro sem sinal de 8 bits.',
            'loop repete a leitura da mesma conexão até terminar.',
            'Empresta buffer mutavelmente; read retorna quantidade recebida, que pode ser menor que 512.',
            'Se nenhum byte foi lido, o peer encerrou o envio nesta leitura.',
            'break sai apenas do loop interno.',
            'Fecha o if.',
            '..count cria fatia até count exclusivo; write_all tenta escrever todos os bytes recebidos.',
            'Fecha o loop de leitura; próxima conexão só será atendida após este encerramento.',
            'Fecha o for; incoming costuma continuar enquanto o listener existir.',
            'Retorna sucesso quando a função alcançar este ponto.',
            'Fecha main.'])) +
        card('Cliente: substitua client-escola/src/main.rs', code(CLIENT, 'rust') + annotated(CLIENT, [
            'Importa traits para ler/escrever no socket.', 'Importa tipo da conexão TCP ativa.', 'Separação visual.',
            'Entrada com retorno de sucesso ou erro de I/O.', 'Conecta ao listener loopback; ? propaga falha de conexão.',
            'b"ping" é literal de bytes, não String; envia exatamente os quatro bytes do exercício.',
            'Reserva array de quatro bytes para resposta conhecida.', 'read_exact espera quatro bytes ou retorna erro; não pressupõe que um read baste.',
            'Converte bytes para exibição tolerante a UTF-8 inválido; {} é lugar do argumento na macro.',
            'Retorna Ok com valor unitário.', 'Fecha main.'])) +
        code('# Terminal Ubuntu A\ncd "$HOME/xmqr-estudo/broker-escola"\ncargo +1.99.0 run\n\n# Terminal Ubuntu B\ncd "$HOME/xmqr-estudo/client-escola"\ncargo +1.99.0 run', 'bash') +
        p('Resultado esperado no client: <code>Resposta: ping</code>. Pare o servidor com Ctrl+C no terminal A. Se a conexão for recusada, inicie A e confira a porta. Se bind falhar, outra aplicação pode ocupá-la. Não conclua que o firewall é responsável sem verificar listener e endereço.') +
        p('TCP é um fluxo: uma leitura pode conter metade de um pacote ou vários pacotes juntos. write_all não comprova processamento pelo peer. O futuro codec deve acumular bytes suficientes, respeitar tamanho máximo e preservar o restante para o próximo pacote. A passagem para Tokio acrescentará atendimento concorrente com limites; não basta trocar read por read.await.'))

    add('caracteres', 'Ler os caracteres e símbolos sem decorar',
        p('O significado depende do contexto. Um ponto dentro de "127.0.0.1" é conteúdo de texto; fora dele pode acessar um campo. Letras de nomes como stream são escolhas do autor, não comandos individuais. Leia tokens, expressões e tipos em conjunto. <a href="https://doc.rust-lang.org/reference/tokens.html">Tokens da linguagem Rust</a>.') +
        table(['Símbolo / forma', 'Leitura contextual', 'Exemplo'], [
            ('{ }', 'Bloco de instruções, expressão de bloco ou construção de struct.', 'fn main() { … }; Config { port: 1883 }'),
            ('( )', 'Parâmetros/chamada, agrupamento ou tupla; () também é tipo/valor unitário.', 'bind(addr); (first, second); Ok(())'),
            ('[ ]', 'Array, índice ou atributo quando precedido de #.', '[0_u8; 512]; bytes[0]; #[test]'),
            (';', 'Termina instrução; no array separa valor e quantidade.', 'let x = 1; [0; 4]'),
            (',', 'Separa argumentos, campos ou itens.', 'Some(x), None'),
            (': / ::', 'Anotação de tipo ou campo / separador de caminho.', 'port: u16; std::io::Result'),
            ('.', 'Acesso a campo/método; não é o mesmo que separador de módulo.', 'stream.read(…); config.port'),
            ('-> / =>', 'Tipo de retorno / separação padrão-corpo em match.', 'fn f() -> u8; Some(x) => x'),
            ('= / == / !=', 'Atribuir binding/valor / comparar igualdade / desigualdade.', 'let n = 0; n == 0; n != 1'),
            ('< >', 'Parâmetros de tipo ou comparações conforme a expressão.', 'Vec<u8>; count < limit'),
            ('? / !', 'Propagar Result/Option compatível / macro ou negação conforme contexto.', 'read()?; println!(); !enabled'),
            ('& / &mut / *', 'Emprestar / emprestar com mutação exclusiva / dereferenciar ou multiplicar.', '&name; &mut buffer; *value; 2 * 3'),
            ('| / ||', 'Delimitadores de closure ou OR bit a bit / OR lógico ou closure sem argumentos.', '|x| x + 1; a || b; || work()'),
            ('.. / ..=', 'Intervalo exclusivo / inclusivo; .. também pode indicar restante de padrão.', 'buffer[..count]; 1..=64'),
            ('_ / _u8', 'Ignorar padrão / separar sufixo de tipo numérico.', 'match x { _ => … }; 0_u8'),
            ('" " / b" "', 'Literal UTF-8 / literal de bytes.', '"hello"; b"ping"'),
            ('\'a / \'x\'', 'Lifetime quando sem aspas de fechamento / caractere com aspas completas.', '&\'a str; \'x\''),
            ('\\n / \\t / \\"', 'Escapes dentro de literal: nova linha, tabulação, aspas.', '"linha\\nseguinte"'),
            ('// / /// / /* */', 'Comentário comum / documentação / comentário de bloco.', '// explica; /// API; /* nota */'),
            ('#[…]', 'Atributo aplicado ao item seguinte; não é comentário.', '#[derive(Debug)]; #[cfg(test)]')]) +
        p('Chaves criam escopos; o último valor sem ; pode ser o retorno do bloco. <a href="https://doc.rust-lang.org/reference/expressions/block-expr.html">Blocos</a>. &amp;, operadores e ? dependem dos tipos. <a href="https://doc.rust-lang.org/reference/expressions/operator-expr.html">Operadores</a>. Funções e atributos têm regras próprias. <a href="https://doc.rust-lang.org/reference/items/functions.html">Funções</a> e <a href="https://doc.rust-lang.org/reference/attributes.html">atributos</a>.') +
        card('Ownership: por que o compilador reclama?',
            p('Um valor tem proprietário. Mover String transfere seu ownership; emprestar com &amp; permite acesso sem transferi-lo. &amp;mut exige acesso exclusivo durante o empréstimo. Ao terminar o escopo, o proprietário libera recursos. clone não é sinônimo de empréstimo: pode copiar dados ou incrementar referência compartilhada. <a href="https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html">Ownership no Rust Book</a>.') +
            code('let topic = String::from("sensor/temperatura");\nlet borrowed = &topic;\nprintln!("{}", borrowed);\nlet moved = topic;\nprintln!("{}", moved);', 'rust') +
            p('Não use topic depois de movê-lo para moved. Arc compartilha ownership com contagem atômica; ainda é preciso definir como alterações concorrentes ocorrem. O ator do broker recebe comandos para serializar transições em vez de permitir mutação arbitrária por toda conexão.')))

    add('comandos', 'Comandos: quem interpreta cada parte',
        table(['Comando / fragmento', 'Interpretação', 'Resultado / cuidado'], [
            ('mkdir -p pasta', 'mkdir cria pasta; -p também cria pais ausentes.', 'A pasta passa a existir; não cria projeto Rust.'),
            ('cd pasta / cd ..', 'Shell muda diretório atual / sobe um nível.', 'Cargo procura manifest a partir do diretório selecionado.'),
            ('cargo new --bin nome', 'new cria pacote; --bin escolhe executável.', 'src/main.rs e Cargo.toml inicial.'),
            ('cargo check', 'Verificação de código sem gerar executável final normal.', 'Feedback rápido; não é execução dos testes.'),
            ('cargo build --locked --bins', 'Compila binários sem permitir mudança de resolução do lockfile.', 'Falha se o lockfile precisar ser atualizado.'),
            ('cargo build --release', 'Seleciona perfil otimizado.', 'target/release; não cria automaticamente .deb ou imagem.'),
            ('cargo run --bin mqtt-broker -- --version', 'Cargo seleciona binário; depois de -- vêm argumentos dele.', 'Consulta versão sem iniciar broker nesta baseline.'),
            ('cargo test --locked', 'Compila/executa testes unitários, integração e documentação aplicáveis.', 'Relatório real; teste ignorado não é PASS.'),
            ('cargo test -- --nocapture', 'Depois de -- são opções do executor de testes.', 'Mostra a saída capturada de testes.'),
            ('cargo fmt --all -- --check', 'Formata/verifica todos os pacotes; --check vai para rustfmt.', 'Verifica sem reformatar arquivos.'),
            ('cargo clippy --locked --all-targets -- -D warnings', 'Analisa alvos; -D warnings transforma avisos em erros.', 'Gate de análise; não substitui teste de comportamento.'),
            ('export MQTT_MODE=open-lab', 'Bash define variável exportada a processos filhos.', 'Vale nesse terminal e filhos; não altera serviço systemd existente.'),
            ('$env:MQTT_MODE = "open-lab"', 'PowerShell usa provedor env para variável de ambiente.', 'Não copie esta sintaxe em Bash.'),
            ('sudo systemctl start xmqr-broker.service', 'Gerenciador systemd inicia a unit instalada.', 'Requer Linux com systemd, pacote/unit e configuração.'),
            ('systemctl status xmqr-broker.service --no-pager', 'Mostra estado atual, sem paginador.', 'Logs históricos de falha não significam falha atual.'),
            ('journalctl -u xmqr-broker.service -f', '-u filtra unit; -f acompanha novas entradas.', 'Ctrl+C encerra visualização, não para serviço.'),
            ('sudo systemctl stop xmqr-broker.service', 'Envia parada coordenada segundo a unit.', 'Broker deve concluir encerramento previsto.'),
            ('sudo systemctl enable --now xmqr-broker.service', 'Habilita inicialização e inicia agora.', 'A unit deve existir antes; não cria usuário/configuração.'),
            ('docker build -t nome:versao .', 'Constrói Dockerfile do contexto . e atribui tag local.', 'Build de imagem não publica no DockerHub.'),
            ('docker run --rm nome:versao --version', 'Cria container e o remove ao terminar; argumento vai ao entrypoint.', 'Precisa imagem local ou disponível no registry.'),
            ('git status / git diff', 'Mostra situação / diferenças de conteúdo.', 'Confira antes de selecionar arquivos para commit.'),
            ('git add arquivo / git commit -m "mensagem"', 'Seleciona arquivo / cria registro local com mensagem.', 'Commit não sincroniza a internet.'),
            ('git push origin main', 'Envia commits da branch ao remoto.', 'Não envia imagens Docker e não cria Release.'),
            ('git tag -a vX.Y.Z -m "versão"', 'Cria tag anotada local apontando para commit.', 'Escolher versão real depois dos gates; não mover tags publicadas.'),
            ('git push origin vX.Y.Z', 'Envia a tag indicada.', 'Release e anexos são outra etapa.')]) +
        p('Em Bash, aspas duplas permitem expansão de $VAR; simples preservam texto. / separa caminhos Linux; . é diretório atual e .. é pai. # inicia comentário fora de aspas; \\ ao fim da linha continua o comando. > redireciona saída e substitui arquivo; >> acrescenta. | liga saída de um processo à entrada de outro; &amp;&amp; executa o próximo somente se o anterior teve sucesso. Esses operadores pertencem ao shell, não ao Rust.') +
        p('Cargo distingue flags antes/depois de --. --locked conserva a resolução e --release seleciona perfil de compilação. <a href="https://doc.rust-lang.org/cargo/commands/cargo-build.html">cargo build</a>. O test runner recebe os argumentos após --. <a href="https://doc.rust-lang.org/cargo/commands/cargo-test.html">cargo test</a>.') +
        p('Não execute uma linha apenas por aparecer nesta tabela: capítulos indicam contexto e pré-requisitos. Comandos de serviço aqui explicam operação do sistema pronto; eles não configuram o exercício TCP.'))

    purposes = {
        'argon2': ('Verificar/gerar hashes de senha com custo apropriado.', 'auth/mod.rs e bin/mqtt-admin/users.rs; não persistir senha em claro.'),
        'crc32fast': ('Checksum rápido dos registros duráveis.', 'persistence/mod.rs; detecta corrupção acidental, não autentica remetente.'),
        'fs2': ('Lock de arquivos para exclusão de acesso ao estado.', 'persistence/mod.rs; dois processos não podem escrever o mesmo estado livremente.'),
        'futures-util': ('Operações sobre futuros, incluindo captura de unwind.', 'transport/mod.rs; isolamento precisa panic=unwind, não panic=abort.'),
        'rand_core': ('Fonte criptográfica de aleatoriedade via OsRng.', 'mqtt-admin; getrandom habilita apoio do sistema, não usar PRNG previsível para salt.'),
        'rpassword': ('Ler credenciais interativamente sem eco no terminal.', 'mqtt-admin e client/credentials.rs; não colocar senha em argumento público.'),
        'rustls': ('Tipos e implementação TLS com validação de certificados.', 'transport e client/tls.rs; não desabilitar SAN/validação para contornar erro.'),
        'rustls-pemfile': ('Ler certificados/chaves representados em PEM.', 'transport e client/tls.rs; parser PEM não equivale a validar confiança.'),
        'serde': ('Transformar structs tipadas em/de documentos.', 'configuration, auth/dynamic e mqtt/store; derive gera implementações.'),
        'sha2': ('SHA-256 para fingerprints e integridade identificável.', 'auth/mod.rs e persistence/backup.rs; hash não é criptografia da senha.'),
        'subtle': ('Comparações apropriadas a dados sensíveis sem comparação ordinária variável.', 'auth/mod.rs; não promete que a aplicação inteira seja de tempo constante.'),
        'thiserror': ('Derivar erros tipados com Display e encadeamento de causa.', 'codec/transport/persistence; evita somente strings sem estrutura.'),
        'tokio': ('Agendar tarefas assíncronas e fornecer I/O/canais/tempo/sinais.', 'main, transport, router e client/session.rs; disco/hash bloqueante exige fronteira própria.'),
        'tokio-rustls': ('Conectar streams Tokio ao handshake TLS rustls.', 'transport/mod.rs; integração async não substitui políticas de autenticação.'),
        'toml': ('Interpretar documentos TOML em estruturas do sistema.', 'configuration, auth e store; esquema e campos desconhecidos são validados.'),
        'tracing': ('Emitir eventos estruturados por nível.', 'main e componentes; payload/credenciais não devem virar log.'),
        'tracing-subscriber': ('Configurar coleta/formatação/filtro dos eventos.', 'main.rs; env-filter e fmt habilitam esses recursos.'),
        'zeroize': ('Apagar valores sensíveis suportados ao descartá-los.', 'auth e mqtt-admin; não elimina cópias externas ou garante todo processo sem resíduos.'),
        'rumqttc': ('Motor MQTT do cliente: pacotes, conexão e ciclo de eventos.', 'client/session.rs; pin =0.25.1 preserva versão exata ensaiada.'),
        'tempfile': ('Diretórios/arquivos temporários isolados para testes.', 'dev-dependencies: não é configuração persistente do broker em operação.'),
    }
    body = p('Bibliotecas não entram todas no exercício inicial: acrescente uma quando a etapa passar a exigir seu papel. A tabela é derivada dos manifests desta baseline. “Por que” descreve o uso observável no código, sem inventar decisões antigas não registradas. Versão declarada sem = é uma restrição compatível de Cargo; a versão exata resolvida está em Cargo.lock. Não copie versões mais recentes automaticamente para um curso reproduzível.')
    for repo, name in [(root, 'Broker'), (root.parent / 'xmqr-client', 'Client')]:
        manifest = tomllib.loads((repo / 'Cargo.toml').read_text(encoding='utf-8'))
        rows = []
        for group in ('dependencies', 'dev-dependencies'):
            for name_dep, spec in manifest.get(group, {}).items():
                version = spec if isinstance(spec, str) else spec['version']
                features = 'Padrões da crate' if isinstance(spec, str) else ', '.join(spec.get('features', [])) + ('; defaults desligados' if spec.get('default-features') is False else '')
                purpose, use = purposes[name_dep]
                rows.append((name_dep + (' [testes]' if group == 'dev-dependencies' else ''), version, features, purpose, use))
        body += card(name + ': cada dependência direta', table(['Biblioteca', 'Restrição', 'Features', 'Função', 'Uso / limite'], rows))
    body += card('Entender features antes de habilitar',
        p('Features selecionam partes da biblioteca em tempo de compilação; não são parâmetros recebidos pela rede. default-features=false desativa o conjunto padrão. Dependências podem unificar features no grafo, portanto a configuração direta não prova ausência absoluta de um recurso transitivo. <a href="https://doc.rust-lang.org/cargo/reference/features.html">Cargo: features</a>.') +
        table(['Feature do manifest', 'Papel nesta composição'], [
            ('Tokio io-util', 'Extensões de leitura/escrita assíncrona.'), ('Tokio macros', 'Atributos de entrada/testes e macros de coordenação.'), ('Tokio net', 'Sockets e listeners.'), ('Tokio rt-multi-thread', 'Runtime com workers múltiplos.'), ('Tokio signal', 'Integração com sinais de parada/reload nas plataformas aplicáveis.'), ('Tokio sync', 'Canais, semáforos e sincronização.'), ('Tokio time', 'Timeouts e temporizadores.'), ('rustls aws_lc_rs', 'Backend criptográfico AWS-LC.'), ('rustls logging / std / tls12', 'Integração de logs / biblioteca padrão / suporte TLS 1.2.'), ('rustls prefer-post-quantum', 'Preferência criptográfica da configuração da biblioteca; não é MQTT 5.'), ('tokio-rustls aws_lc_rs / logging / tls12', 'Backend e opções do adaptador alinhados ao TLS.'), ('rumqttc use-rustls-no-provider', 'Usa rustls sem selecionar o provider padrão pela feature; provider é tratado pela composição.'), ('serde derive', 'Geração de Serialize/Deserialize por atributos.'), ('rand_core getrandom', 'Integração com aleatoriedade fornecida pelo ambiente.'), ('tracing-subscriber env-filter / fmt', 'Filtro por ambiente e saída formatada.')]) +
        p('Tokio fornece scheduler e I/O não bloqueante; #[tokio::main] envolve a função em runtime. await suspende uma tarefa, não cria uma thread por mensagem. <a href="https://docs.rs/tokio/latest/tokio/">API oficial Tokio</a>.'))
    add('bibliotecas', 'Cada biblioteca: motivo, feature e lugar no código', body)

    add('manifest-aula', 'Como escrever Cargo.toml e separar módulos',
        code('[package]\nname = "broker-escola"\nversion = "0.1.0"\nedition = "2024"\n\n[dependencies]\n', 'toml') +
        table(['Parte', 'Interpretação'], [
            ('[package]', 'Cabeçalho de tabela TOML com metadados do pacote.'), ('name = "broker-escola"', 'Chave, sinal = e string; a grafia do nome é escolha do projeto.'), ('version = "0.1.0"', 'Versão do aplicativo; não é versão MQTT.'), ('edition = "2024"', 'Conjunto de regras de linguagem; não obriga a usar o compilador de 2024.'), ('[dependencies]', 'Dependências normais; vazio é suficiente para os exemplos std.'), ('{ version = "…", features = ["…"] }', 'Tabela inline com restrição e array de recursos.'), ('[[bin]]', 'Array de tabelas: define um alvo executável por entrada.'), ('rust-version = "1.88"', 'Mínimo declarado da toolchain; precisa validação para promessa de compatibilidade.'), ('publish = false', 'Impede publicação desse pacote no crates.io; GitHub é outro canal.'), ('[profile.release]', 'Configura como o perfil release compila.'), ('panic = "unwind"', 'Permite desenrolamento da pilha utilizado no isolamento de panic.'), ('strip = "symbols" / lto = "thin"', 'Remove símbolos / otimiza entre unidades; não define comportamento MQTT.'), ('unsafe_code = "forbid"', 'Proíbe unsafe no código abrangido por essa regra; dependências têm regras próprias.'), ('all = "deny" / pedantic = "warn"', 'Configura níveis de lints Clippy; o gate -D warnings também eleva avisos.')]) +
        p('Manifest descreve o pacote; campos extras não viram automaticamente configuração de runtime. <a href="https://doc.rust-lang.org/cargo/reference/manifest.html">Referência Cargo.toml</a>.') +
        code('src/\n  main.rs\n  lib.rs\n  mqtt/\n    mod.rs\n    codec.rs\n    topic.rs\n    router.rs\n    store.rs\n  transport/mod.rs\n  persistence/mod.rs\n  auth/mod.rs\n  configuration.rs', 'text') +
        p('Esta árvore é um recorte para aprendizado. O catálogo abaixo contém a árvore Rust efetiva completa. Em lib.rs, pub mod mqtt; declara e exporta módulo; em mqtt/mod.rs, mod codec; declara submódulo. use aproxima um nome já existente. mod, use e pub não são intercambiáveis: declarar, importar e tornar acessível são operações distintas.') +
        p('Não divida tudo antes do primeiro programa funcionar. Extraia módulos quando surgir responsabilidade testável: interpretar pacote não deve abrir arquivo; decidir destinatários não deve negociar TLS; CLI não deve redefinir o protocolo.'))

    stages = [
        ('4 — codec e tópicos', 'src/mqtt/codec.rs; src/mqtt/topic.rs; src/mqtt/limits.rs',
         'Defina tipos de pacotes e erros. Leia byte de controle, Remaining Length e corpo somente após validar o tamanho. Distinga bytes de texto UTF-8. Em TCP, preserve sobras e aceite fragmentação.',
         'Comece por CONNECT/CONNACK e PUBLISH QoS 0. Faça encode/decode de vetor conhecido e negativos de flags, UTF-8, tamanho e fragmentação antes de rede concorrente.',
         'Teto do pacote inteiro 65536 bytes; tópico/filtro 1024 bytes UTF-8; payload 4096. Aceitar Remaining Length enorme antes de alocar abre consumo indevido. MQTT usa formato binário, não linhas de texto.', 'P04, P41, P58'),
        ('5 — conexão e keepalive', 'src/mqtt/mod.rs; src/transport/mod.rs',
         'Modele conexão não autenticada, CONNECT aceito e desconexão. Valide ordem dos pacotes, identificador e keepalive. Só registre Will após aceite da conexão.',
         'Cliente recebe CONNACK para entrada válida e falha previsível para pacote fora de ordem. Teste timeout/fechamento sem precisar esperar indefinidamente.',
         'Ter socket conectado não prova sessão MQTT aceita. Tarefa Tokio deve liberar permit e recursos mesmo no erro.', 'P05, P38, P47, P54'),
        ('6 — assinaturas e roteamento QoS 0', 'src/mqtt/topic.rs; src/mqtt/router.rs; src/mqtt/mod.rs',
         'Armazene filtros por sessão e gere destinatários. Implemente SUBSCRIBE/SUBACK, PUBLISH e UNSUBSCRIBE/UNSUBACK. Modele +, # e regra de tópicos iniciados por $.',
         'Dois clients: um assina sensor/temperatura, outro publica. Faça caso sem destinatário, filtros inválidos, unsubscribe e ACL negada.',
         'Filas precisam limite e tratamento de cliente lento. ACL de filtro e ACL de entrega não podem ser consideradas a mesma verificação.', 'P06, P22, P33'),
        ('7 — QoS 1 e 2', 'src/mqtt/mod.rs; src/mqtt/router.rs; src/mqtt/store.rs',
         'Separe fluxos inbound e outbound por identificador. QoS 1 usa PUBLISH/PUBACK; QoS 2 usa PUBLISH/PUBREC/PUBREL/PUBCOMP. Acompanhe duplicatas e retransmissões.',
         'Teste reconexão entre cada fase, ACK duplicado e identificador fora de estado. O estado durável deve acompanhar a responsabilidade antes do ACK aplicável.',
         'QoS 1 permite entrega duplicada. QoS 2 trata entrega MQTT no fluxo correspondente; não transforma atualização de banco externo em transação exatamente uma vez.', 'P07, P26, P28'),
        ('8 — sessão, retained e Last Will', 'src/mqtt/store.rs; src/mqtt/router.rs',
         'Diferencie assinatura persistente, mensagens offline, retained por tópico e Will de conexão. Representação com enums evita combinações ilegais. Associe gerações para conexão antiga não encerrar a nova.',
         'Reinicie com sessão persistente, entregue retained ao novo assinante e remova retained com payload vazio. DISCONNECT normal cancela Will; queda anormal segue as regras.',
         'Retained não é histórico. Reduzir quota incompatível com estado recuperado deve falhar. Quota saturada em Will exige preservar obrigação durável, como registrado em P55 rev3.', 'P08, P27, P29, P42, P55'),
        ('9 — persistência e ator de escrita', 'src/persistence/mod.rs; actor.rs; backup.rs; src/mqtt/store.rs',
         'Projete documento versionado, WAL e snapshot. Valide checksum/recovery. O writer recebe comandos e responde após commit no nível previsto. Um processo detém o lock de estado.',
         'Teste interrupção do processo e restauração, registro truncado, checksum errado, diretório concorrente e backup verificável offline.',
         'Crash de processo não simula toda perda de energia. Operações de disco/locks não devem bloquear workers Tokio. Backup copiado com writer ativo não é automaticamente consistente.', 'P25, P39, P45'),
        ('10 — TLS, usuários e ACL', 'src/transport/mod.rs; src/auth/mod.rs; src/auth/dynamic.rs; src/bin/mqtt-admin/',
         'Use rustls para handshake e certificados. No perfil seguro, vincule identidade, credenciais e ACL. Separe certificado público e chave privada. Adicione usuário, grupos e papéis por contrato explícito.',
         'Teste CA válida, SAN correto, certificado ausente/incorreto, senha inválida e tópico negado. Bundle inválido não substitui política válida; reload válido exige nova autenticação conforme o contrato.',
         'Padrão secure-mtls. Laboratórios TCP ficam no loopback. Expor porta não fornece confiança TLS. Não incorporar CA privada, server.key ou credenciais reais em Git/imagem.', 'P10, P23, P34, P35, P44'),
        ('11 — configuração e observabilidade', 'src/configuration.rs; src/monitoring.rs; src/main.rs',
         'Capture configuração inicial em snapshot. Combine defaults, TOML e overrides. Valide antes de listener. Métricas distinguem disponibilidade do ator/writer e admissão de transporte.',
         'Teste campo desconhecido, faixa inválida, caminho relativo e precedência. Readiness deve verificar trabalho útil do sistema, não apenas porta aberta.',
         'As quotas podem ser reduzidas dentro dos tetos, não ampliadas arbitrariamente. Monitor HTTP é opcional e loopback. SIGHUP do bundle não significa reload geral do TOML.', 'P43, P52, P54, P55'),
        ('12 — client independente', '../xmqr-client/src/cli.rs; tls.rs; credentials.rs; payload.rs; session.rs; signals.rs; output.rs',
         'Parseie CLI, obtenha credenciais sem eco, valide TLS e payload, configure rumqttc e mantenha EventLoop em andamento. Saída e sinais ficam separados da sessão.',
         'Teste pub/sub QoS, retained, retomada, prazo de execução e parada por sinal, além de opções incompatíveis. Compare cliente contra outro broker e outro cliente contra XMQR.',
         'AsyncClient enfileira solicitações; EventLoop.poll promove conexão e eventos. Queues e in-flight têm limite. Não usar publish enfileirado como prova de conclusão de negócio.', 'C25 a C40; consultar registros individuais'),
        ('13 — distribuição e evolução', 'tests/; scripts/; packaging/; Dockerfile; .github/workflows/; CHANGELOG.md',
         'Passe fmt/test/clippy e integrações proporcionais. Gere .deb, instale em ambiente isolado e teste upgrade/rollback. Monte Docker sem segredos, com usuário e volumes. Documente exatamente plataforma e artefatos.',
         'Release aponta para tag imutável, com checksums e .deb Ubuntu por versão. Teste parada SIGTERM, reinício/retained e negativas de TLS do container.',
         'Tag não é Release; Release não é repositório APT; Dockerfile não é imagem publicada. MQTT 5 pede codec, propriedades, estados e testes próprios, não trocar número da versão.', 'P47, P59 a P64; C31, C39, C40'),
    ]
    body = p('As etapas seguintes descrevem fatias para implementação guiada, não entregam um broker novo completo para copiar. Use as fontes atuais como referência e crie um prompt pequeno antes de cada mudança. Para cada fatia, implemente um caminho vertical funcionando, valide negativos e registre a evidência antes de avançar.')
    for title, files, work, exercise, pitfall, prompts in stages:
        body += card('Etapa ' + title, p('<strong>Arquivos de referência:</strong> ' + escape(files)) + p('<strong>O que criar e por quê:</strong> ' + escape(work)) + p('<strong>Exercício e critério de conclusão:</strong> ' + escape(exercise)) + p('<strong>O que entender antes de avançar:</strong> ' + escape(pitfall)) + p('<strong>Contratos relacionados:</strong> ' + escape(prompts)))
    body += p('Formato wire e transições devem seguir a especificação normativa, não o comportamento presumido de um exemplo. <a href="https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html">OASIS MQTT 3.1.1</a>. O client usa o ciclo de eventos de <a href="https://docs.rs/rumqttc/0.25.1/rumqttc/">rumqttc 0.25.1</a>; poll deve continuar avançando para operar a conexão.')
    add('construcao', 'Etapas 4–13 — transformar o exercício em broker MQTT', body)

    add('ler-fluxos', 'Leitura humana dos caminhos mais importantes do XMQR',
        card('Início e --version: main.rs',
            p('main é síncrona. args_os lê argumentos nativos; skip(1) remove o nome do executável. Duas chamadas next verificam se há zero, um ou mais argumentos. (None,None) chama run; um único --version/-V imprime CARGO_PKG_VERSION e retorna Ok. Qualquer outra combinação imprime mensagem estática e encerra com código 2. Não há --help implementado no broker.') +
            p('Só run possui #[tokio::main]. Ela configura logs, captura Configuration, configura monitor, seleciona perfil e valida segurança. Converte bind em SocketAddr, exige caminhos por perfil, recupera StateLimits e TransportLimits e só então chama serve. Esta ordem permite --version funcionar sem certificados e evita listener para configuração inválida.')) +
        card('Uma publicação até o ACK',
            p('Transporte aceita socket dentro da quota; TLS, quando exigido, autentica canal/certificado. O handler interpreta pacote e autentica CONNECT. Ao receber PUBLISH, codec valida flags, tópico, payload e framing. Política autoriza operação. Router decide transição e destinatários; Store valida estado candidato e quotas.') +
            p('Quando a transição assume responsabilidade durável, o writer confirma commit antes do ACK correspondente. Depois, entrega é agendada para assinantes autorizados. Um erro de commit não pode virar confirmação de sucesso. O ACK não confirma processamento pela aplicação do assinante. Para entender cada ramo, acompanhe o tipo do comando e seu retorno nos arquivos mostrados abaixo.')) +
        card('Retained, fila offline e inflight',
            p('Retained guarda a última publicação retida de um tópico. Offline pertence à sessão desconectada. Inflight representa mensagens aguardando fases de confirmação. Esses conjuntos consomem quotas diferentes; limitar um não limita os outros. A recuperação reaplica limites e recusa imagem incompatível, em vez de apagar mensagens silenciosamente.') +
            p('Na baseline, os tetos são 64 sessões, 256 retained e, por sessão, 256 assinaturas, 64 offline e 32 em cada conjunto inboundQoS2/outbound inflight. Conexões TCP até 64. Quantidade configurável é limite lógico, não medição de requisições por segundo ou capacidade sob TLS.')) +
        card('Client: comando não é evento concluído',
            p('cli.rs converte opções em configuração tipada. credentials.rs obtém valores; tls.rs compõe confiança e identidade; payload.rs escolhe bytes de arquivo/stdin/texto e seus limites. session.rs cria client/eventloop e processa eventos de conexão, publicação e recebimento. signals.rs coordena término; output.rs apresenta resultado.') +
            p('rumqttc evita reimplementar outro codec no client. Isso não dispensa testar interoperabilidade, política do broker, prazo de entrega e tratamento das notificações. Broker e client têm versões independentes.')))

    add('referencia-pronta', 'Baixar o sistema pronto para comparar com seu exercício',
        p('Execute numa nova pasta, depois da instalação das ferramentas. As tags selecionam uma referência reproduzível; não use cargo new nestes clones.') +
        code('mkdir -p "$HOME/xmqr-referencia"\ncd "$HOME/xmqr-referencia"\ngit clone --branch v0.11.2 https://github.com/licodevone/xmqr.git\ngit clone --branch v0.7.1 https://github.com/licodevone/xmqr-client.git\ncd xmqr\ncargo +1.99.0 build --locked --bins\ncargo +1.99.0 run --locked --bin mqtt-broker -- --version\ncd ../xmqr-client\ncargo +1.99.0 build --locked --bins\ncargo +1.99.0 run --locked --bin mqtt-client -- --help', 'bash') +
        p('git clone --branch com tag normalmente deixa HEAD destacado: é adequado à referência, mas crie branch própria antes de modificar. Broker sem argumentos precisa configuração completa. Para iniciar operação segura, siga README/docs/ubuntu-systemd.md; o tutorial não cria automaticamente certificados, usuário de serviço nem bundle real.') +
        p('Para o estudo em open-lab no Ubuntu, consulte primeiro as opções disponíveis do client com --help. O exemplo abaixo inicia somente o broker local em um diretório de estado novo. Não reuse estado secure-mtls ou de serviço: perfis têm isolamento próprio.') +
        code('cd "$HOME/xmqr-referencia/xmqr"\nexport MQTT_MODE=open-lab\nexport MQTT_BIND=127.0.0.1:1883\nexport MQTT_STATE_DIR="$HOME/xmqr-estudo/estado-open-lab"\ncargo +1.99.0 run --locked --bin mqtt-broker', 'bash') +
        p('Ao terminar, Ctrl+C encerra esse processo de primeiro plano; para serviço, use systemctl stop. O laboratório não serve de receita para expor autenticação em claro à LAN. Em TLS, o IP/nome usado pelo client deve constar no SAN do certificado, e o client deve confiar na CA correspondente.'))

    inventory = []
    for folder in ['tests', 'scripts', 'packaging', '.github/workflows', 'docs']:
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.name != 'code-guide.html':
                inventory.append((path.relative_to(root).as_posix(), {
                    'tests': 'Teste de integração/regressão: estudar cenário e asserção; arquivo existente não comprova execução.',
                    'scripts': 'Automação de geração/verificação/empacotamento; veja parâmetros antes de executar.',
                    'packaging': 'Metadados/exemplos/units do pacote; não é instalação já realizada.',
                    '.github/workflows': 'Automação GitHub; sucesso depende do registro da execução.',
                    'docs': 'Contrato ou explicação especializada; snapshots podem ter contexto histórico.'}[folder]))
    add('apoio', 'Arquivos de apoio: onde estudar e como manter o guia',
        p('O inventário abaixo cobre arquivos de texto de apoio presentes no broker. Eles não entram todos no runtime. Fontes Rust broker/client têm sua íntegra numerada na seção Arquivos e linhas. Cargo.lock contém muitas dependências transitivas: não confunda cada uma delas com uma decisão direta de arquitetura.') +
        table(['Arquivo', 'Papel'], inventory) +
        p('README apresenta uso; CHANGELOG lista diferenças entre versões; VERSIONING define publicação; CONTRIBUTING define gates; prompts definem contratos da mudança e registros dizem o que foi executado. Leitura didática proposta aqui não substitui evidência dos registros.') +
        code('python3 scripts/build_code_guide.py', 'bash') +
        p('Execute na raiz do broker, com Python 3.11+ e xmqr-client ao lado. build_code_guide.py monta catálogo e fontes; guide_tutorial.py contém capítulos humanos e exemplos; guide_line_notes.py produz notas assistidas de sintaxe. Regerar atualiza a fotografia dos arquivos e commits, mas não audita automaticamente a semântica de funcionalidades novas.') +
        p('Para cada nova fatia: prepare prompt → implemente → valide → registre → atualize explicação → revise diff → commit/push autorizados. Se um exemplo falhar, revise o prompt e a explicação junto da correção. O guia permite leitura offline; links oficiais são referências opcionais que exigem internet.'))
    return result
