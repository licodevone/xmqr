from pathlib import Path
import html, re, collections

root=Path(__file__).resolve().parents[1]
path=root/'docs/code-guide.html'
page=path.read_text(encoding='utf-8')
calls={
'load':'carrega e valida a configuração de entrada',
'load_with':'combina arquivo opcional com overrides explícitos',
'parse':'interpreta e valida a representação de entrada',
'max_connections':'valida o teto de admissãoTCP na faixa1..64',
'required_path':'exige que o caminho obrigatório esteja presente e não vazio',
'ensure_state_profile':'verifica/grava a associação do diretório ao perfil de segurança',
'start_router':'recupera estado e inicia o ator de roteamento',
'load_policy':'carrega a política de autenticação/autorização selecionada',
'validate_security_environment':'recusa configurações de segurança incompatíveis',
'validate_open_lab_bind':'exige endereço de laboratório loopback',
'load_mtls_server_config':'monta o servidorTLS com verificação do certificado cliente',
'watch_security':'mantém o observador de reload do bundle de segurança',
'run_until_shutdown':'coordena atendimento até sinal de encerramento',
'serve_connection':'processa a máquina de estadosMQTT desta conexão',
'encode_connack':'codifica a resposta de conexãoMQTT',
'encode_connack_with_session':'codificaCONNACK incluindo Session Present',
'encode_puback':'codificaPUBACK para publicaçãoQoS1',
'encode_pubrec':'codificaPUBREC da negociaçãoQoS2',
'encode_pubrel':'codificaPUBREL da negociaçãoQoS2',
'encode_pubcomp':'codificaPUBCOMP da negociaçãoQoS2',
'encode_publish':'codifica uma publicaçãoMQTT',
'encode_pingresp':'codifica resposta aoPINGREQ',
'encode_suback':'codifica confirmação das assinaturas',
'encode_unsuback':'codifica confirmação deUNSUBSCRIBE',
'read_packet':'lê/decodifica o próximo pacote respeitando o deadline',
'commit':'solicita confirmação da transição candidata no armazenamento',
'snapshot':'solicita uma imagem compactada do estado',
'shutdown':'solicita encerramento coordenado do componente',
'allowed_publish':'consulta autorização para publicar no tópico',
'allowed_subscribe':'consulta autorização para assinar o filtro',
'allowed_delivery':'consulta autorização para receber a mensagem',
'validate_message':'verifica invariantes da mensagem armazenada',
'apply_message':'aplica publicação à imagem candidata e seus destinatários',
'authenticate':'valida identidade/credenciais sob a política selecionada',
'try_acquire_owned':'tenta obter uma vaga sem esperar; devolve permit com ownership',
'accept':'aguarda uma nova conexãoTCP',
'set_nodelay':'configuraTCP_NODELAY para o socket aceito',
'write_all':'tenta escrever todos os bytes fornecidos',
'read_to_end':'lê bytes até o fim ou o limite do leitor',
'read_exact':'exige ler exatamente a quantidade de bytes do buffer',
'sync_all':'solicita sincronização de dados/metadados do arquivo com oSO',
'create_dir_all':'cria diretório e pais ausentes',
'rename':'renomeia/move o caminho; atomicidade depende da plataforma e filesystem',
'metadata':'consulta metadados do arquivo',
'is_file':'verifica nos metadados se é arquivo regular',
'is_absolute':'verifica se o caminho é absoluto',
'is_loopback':'verifica se o IP pertence ao loopback',
'join':'combina segmentos de caminho ou une elementos, conforme o tipo receptor',
'contains':'verifica se o valor pertence à coleção/faixa',
'insert':'insere/substitui uma entrada na coleção',
'remove':'remove uma entrada e retorna o valor anterior quando existir',
'retain':'mantém apenas entradas aprovadas pelo predicado',
'extend':'acrescenta entradas; no mapa de configuração substitui chaves existentes',
'clone':'clona o valor; paraArc cria outra referência ao mesmo objeto',
'cloned':'copia porClone o valor obtido por referência',
'collect':'materializa o iterador na coleção/tipo inferido',
'filter_map':'transforma entradas e descarta resultadosNone',
'filter':'mantém elementos que satisfazem o predicado',
'map_err':'transforma o erro preservando o sucesso',
'map':'transforma o conteúdo ou elementos conforme o tipo receptor',
'unwrap_or':'usa o valor disponível ou o fallback indicado',
'unwrap_or_default':'usa o valor disponível ou oDefault do tipo',
'unwrap':'extrai sucesso/Some; causa panic se o valor forErr/None',
'expect':'extrai sucesso/Some; causa panic com a mensagem se falhar',
'ok_or':'converteOption emResult usando o erro indicado paraNone',
'ok_or_else':'converteOption emResult calculando erro paraNone',
'as_deref':'empresta o conteúdo desreferenciado deOption/Result',
'as_str':'empresta o conteúdo como texto',
'as_bytes':'empresta os bytes do texto/valor suportado',
'to_owned':'cria valor possuído a partir de referência',
'to_string':'converte o valor emString',
'into_string':'converteOsString emString; pode falhar por nãoUnicode',
'into_os_string':'converte o caminho possuído em representação nativa',
'from_utf8':'valida e interpreta bytes comoUTF-8',
'var_os':'consulta valor nativo opcional do ambiente ou snapshot',
'var':'consulta valor textual e diferencia ausência de nãoUnicode',
'env_remove':'remove variável apenas do ambiente do processo filho configurado',
'env':'define variável para o processo filho',
'output':'executa comando filho e captura saída/status',
'status':'executa comando filho e obtém o status',
'spawn':'inicia tarefa ou processo, conforme a API usada',
'timeout':'limita a duração de uma operação assíncrona',
'timeout_at':'limita a operação por instante absoluto',
'sleep':'suspende pelo intervalo indicado',
'sleep_until':'suspende até o instante indicado',
'fetch_add':'incrementa atomicamente e retorna o valor anterior',
'fetch_sub':'decrementa atomicamente e retorna o valor anterior',
'lock':'obtém exclusão mútua conforme o tipo; pode aguardar/bloquear',
'send':'envia mensagem/comando ao canal ou componente receptor',
'recv':'recebe mensagem/bytes conforme a API',
'push':'acrescenta elemento ao vetor',
'push_back':'acrescenta elemento ao fim da fila',
'pop_front':'retira primeiro elemento da fila quando existir',
'len':'obtém número de bytes/elementos conforme o tipo',
'is_empty':'verifica ausência de bytes/elementos',
'next':'obtém próximo elemento/evento conforme a API',
'set_transport':'configura transporte no clientMQTT',
'set_last_will':'configura mensagemWill do client',
'set_credentials':'configura usuário/senha da conexãoMQTT',
'publish':'solicita publicação com tópico,payload,QoS e retenção',
'subscribe':'solicita assinatura no broker',
'poll':'avança o event loop do client e obtém próximo evento',
'read_password_file':'lê senha seguindo requisitos de segurança do arquivo',
'build_client_config':'monta confiança e identidadeTLS do client',
'validate_password':'verifica regras locais da senha recebida',
}
variables={
'config':'snapshot da configuração', 'monitor_config':'configuração do monitorHTTP',
'metrics':'métricas compartilhadas','mode':'perfil selecionado','bind_address':'endereçoIP/porta do listener',
'state_directory':'diretório do estado persistido','limits':'limites aplicados ao componente',
'overrides':'valores explícitos que prevalecem sobre oTOML','result':'resultado intermediário',
'document':'documentoTOML desserializado','file':'arquivo aberto','bytes':'buffer de bytes',
'text':'representação textual validada','resolved':'caminho resolvido','tls_config':'configuraçãoTLS',
'auth':'política de autenticação/autorização','router':'handle do ator de roteamento',
'transport':'listener/transporte','permit':'vaga de admissão mantida pela tarefa',
'socket':'socketTCP aceito','peer_addr':'endereço remoto','connection_id':'identificador da conexão',
'state':'imagem do estadoMQTT','candidate':'imagem candidata ainda sujeita a validação/commit',
'session':'estado da sessão','client_id':'identificadorMQTT do cliente','generation':'geração da conexão',
'principal':'identidade autorizada','message':'mensagem em processamento','packet':'pacoteMQTT decodificado',
'reader':'leitor de frames','connect':'pacote de aberturaCONNECT','cli':'opções da linha de comando',
'password':'credencial sensível','publication':'entrada da publicação','options':'opções de conexão rumqttc',
'arguments':'argumentos de processo','output':'resultado/saída capturada','directory':'diretório temporário ou alvo',
'path':'caminho','deadline':'instante máximo permitido','start':'instante inicial de medição',
'reply':'canal para retornar a resposta','command':'comando recebido/preparado','value':'valor a validar/converter',
}
pending=[]
stats=collections.Counter()
def note(line):
 s=line.strip()
 if not s:return 'Linha vazia: separa visualmente blocos; não executa operação.'
 if s.startswith(('//!','///')):return 'Comentário de documentação: descreve contrato/uso do item; não executa operação.'
 if s.startswith('//'):return 'Comentário de manutenção: registra a razão ou regra indicada no texto; não é instrução executável.'
 if s.startswith('#[cfg'):return 'Compilação condicional: inclui o item seguinte somente na plataforma/configuração indicada.'
 if s.startswith('#[test]'):return 'Marca a função seguinte como teste a ser descoberto pelo harnessRust.'
 if s.startswith('#[tokio::test'):return 'Marca teste assíncrono e cria runtimeTokio para executá-lo.'
 if s.startswith('#[tokio::main'):return 'Gera entrada síncrona que cria runtimeTokio e executa o main assíncrono.'
 if s.startswith('#[serde(deny_unknown_fields)'):return 'Recusa campos não declarados ao desserializar este tipo.'
 if s.startswith('#[serde(default)'):return 'UsaDefault se o campo não estiver presente no documento.'
 if s.startswith('#[serde'):return 'Configura comoSerde serializa/desserializa o item seguinte.'
 if s.startswith('#[derive'):return 'Gera automaticamente as implementações dos traits listados para o tipo seguinte.'
 if s.startswith('#[must_use]'):return 'Solicita aviso se o resultado/item seguinte for descartado sem uso.'
 if s.startswith('#[error'):return 'Define o texto deDisplay desta variante de erro via thiserror.'
 if s.startswith('#[allow'):return 'Suprime especificamente o lint listado no item seguinte; não muda comportamento runtime.'
 if s.startswith('#['):return 'AtributoRust: configura geração/compilação ou validação do item seguinte.'
 if re.fullmatch(r'[}\]);,\s]+',s):return 'Fecha bloco, expressão, lista ou chamada aberta anteriormente; pontuação delimita seu alcance.'
 if s.startswith('use ') or re.match(r'^pub(?:\([^)]*\))? use ',s):return 'Importa os nomes/caminhos indicados para este módulo; pub também os reexporta.'
 if re.match(r'^(pub(?:\([^)]*\))? )?mod ',s):return 'Declara móduloRust e liga o arquivo correspondente; pub permite acesso externo.'
 if s.startswith('const ') or s.startswith('pub const '):return 'Declara constante de compilação com tipo e valor indicados; uso efetivo ocorre nas referências a ela.'
 if re.match(r'^(pub(?:\([^)]*\))? )?type ',s):return 'Declara alias de tipo para simplificar a assinatura; não cria valor runtime.'
 m=re.search(r'\b(?:async\s+)?fn\s+(\w+)',s)
 if m:
  n=m.group(1); pending[:]=[n]
  return f'Declara função {n}. '+(calls.get(n,'O corpo abaixo determina os efeitos; a assinatura define entradas/retorno')+'.')+(' async permite suspensão em await.' if 'async fn' in s else '')
 m=re.match(r'^(?:pub(?:\([^)]*\))?\s+)?(struct|enum|trait)\s+(\w+)',s)
 if m:return f'Declara {m.group(1)} {m.group(2)}: '+{'struct':'agrupa campos em um tipo.','enum':'representa alternativas discriminadas de estado/comando.','trait':'define um contrato de comportamento.'}[m.group(1)]
 if s.startswith('impl'):return 'Abre implementação de métodos/trait para o tipo indicado.'
 if s.startswith('where'):return 'Inicia restrições sobre tipos genéricos da assinatura anterior.'
 if s.startswith('assert_eq!'):return 'Teste: exige igualdade entre os valores; divergência causa panic e reprova o teste.'
 if s.startswith('assert_ne!'):return 'Teste: exige que os valores sejam diferentes.'
 if s.startswith('assert!'):return 'Teste: exige condição verdadeira; falsidade reprova o teste.'
 if s.startswith('panic!'):return 'Interrompe execução porpanic com a mensagem fornecida.'
 if s.startswith(('info!','warn!','debug!','error!')):return 'Registra evento no nível indicado e campos fornecidos; não confirma sucesso de negócio.'
 if s.startswith(('println!','print!','eprintln!','eprint!')):return 'Escreve texto formatado na saída padrão ou saída de erro conforme a macro.'
 if s.startswith('return '):return 'Encerra imediatamente a função retornando a expressão indicada.'+(' Devolve erro ao chamador.' if 'Err(' in s else '')
 if s.startswith('break'):return 'Encerra o laço atual, podendo fornecer o valor indicado.'
 if s.startswith('continue'):return 'Pula o restante desta iteração e inicia a próxima.'
 if s.startswith('if let '):return 'Executa o bloco somente se o valor corresponder ao padrão e extrai os campos indicados.'
 if s.startswith('else if '):return 'Testa condição alternativa apenas se o ramo anterior não foi escolhido.'
 if s.startswith('if '):return 'Avalia a condição indicada; executa o bloco quando verdadeira.'
 if s.startswith('} else') or s.startswith('else'):return 'Inicia alternativa usada quando condição/padrão anterior não foi atendido.'
 if s.startswith('for '):return 'Itera sobre os elementos da expressão; vincula cada entrada ao padrão indicado.'
 if s.startswith('while '):return 'Repete o bloco enquanto a condição indicada permanecer verdadeira.'
 if s.startswith('loop'):return 'Abre laço sem condição inicial; saída depende de break/return/erro.'
 if s.startswith('match '):return 'Seleciona um ramo pelo padrão do valor; cada variante possui tratamento explícito.'
 if '=>' in s:
  return 'Ramo de match/closure: ao corresponder ao padrão à esquerda, avalia a expressão/bloco à direita.'
 if s.startswith('let '):
  m=re.match(r'let (?:mut )?([A-Za-z_]\w*)',s); n=m.group(1) if m else 'padrão'
  explanation='Cria variável local '+n+(' mutável' if s.startswith('let mut') else '')
  if n in variables:explanation+=' para '+variables[n]
  return explanation+'. '+explain_calls(s)
 if s.startswith('tokio::select!'):return 'Aguarda múltiplas operações assíncronas e executa o ramo que ficar pronto conforme o contrato select.'
 if s.startswith('tokio::pin!'):return 'Fixa o futuro/valor para permitir polling por referência sem mover sua posição.'
 if s.startswith('drop('):return 'Descarta explicitamente o valor e executa seuDrop; permit libera vaga, socket fecha seu handle.'
 if s in ('Ok(())','Ok(())?;'):return 'Produz sucesso sem valor adicional; eventual ? propaga erro da expressãoResult.'
 if s.startswith('Ok('):return 'Constrói resultado de sucesso com o valor indicado.'
 if s.startswith('Err('):return 'Constrói resultado de erro com a causa indicada.'
 if s.startswith('Some('):return 'Constrói/seleciona a alternativaOption com valor presente, conforme posição na expressão.'
 if s.startswith('None'):return 'Indica ausência de valor opcional.'
 if s.startswith('Self {') or s.startswith('Self::'):return 'Usa o próprio tipo desta implementação para construir valor ou chamar método associado. '+explain_calls(s)
 if s.startswith('&[') or s in ('[','{','('):return 'Abre expressão/lista/bloco; as linhas seguintes fornecem seus elementos.'
 m=re.match(r'^(?:pub(?:\([^)]*\))?\s+)?([A-Za-z_]\w*)\s*:\s*(.*)',s)
 if m and not s.startswith(('http:','https:')):return 'Define campo, parâmetro ou elemento nomeado '+m.group(1)+' com tipo/valor à direita. '+explain_calls(s)
 if s.startswith(('.await','await')):return 'Espera a conclusão do futuro sem bloquear o worker; ? quando presente propaga erro ao chamador.'
 if s.startswith('.'):return 'Continua encadeamento sobre o resultado da linha anterior. '+explain_calls(s)
 if re.match(r'^("|r["#]|b")',s):return 'Fornece literal de texto/bytes: conteúdo de configuração, protocolo ou fixture conforme o contexto; não executa chamada sozinho.'
 if re.match(r'^\d',s):return 'Fornece literal numérico ou elemento de lista no contexto da expressão aberta.'
 if re.search(r'(?<![<>=!])=(?!=|>)',s):return 'Atribui à variável/campo à esquerda o resultado à direita. '+explain_calls(s)
 if re.search(r'\w+\s*\(',s):return explain_calls(s)
 if s.startswith('|') or s.startswith('move |'):return 'Define closure que captura o contexto e recebe os parâmetros entre barras.'
 if s.startswith(('&','*')):return 'Empresta ou desreferencia o valor indicado dentro da expressão; efeito exato depende do tipo.'
 if s.startswith(('true','false')):return 'Fornece valor booleano na expressão.'
 if s.endswith(';'):return 'Avalia a expressão/instrução indicada neste bloco; ponto e vírgula descarta valor final quando aplicável.'
 return 'Continua a declaração/expressão aberta: esta linha fornece tipo, valor ou componente listado; efeito ocorre com o conjunto das linhas do bloco.'

def explain_calls(s):
 names=re.findall(r'\b([A-Za-z_]\w*)\s*(?:\:\:<[^>]*>)?\s*\(',s)
 known=[]
 for n in names:
  if n in calls and calls[n] not in known:known.append(calls[n])
 phrase='; '.join(known)
 if not phrase:
  if names:phrase='invoca '+', '.join(dict.fromkeys(names))+': os efeitos internos estão no corpo dessas funções'
  else:phrase='o valor é determinado pela expressão à direita ou pelas linhas de continuação'
 if '?' in s:phrase+='; ? propaga falha ao chamador'
 if '.await' in s:phrase+='; await suspende até o futuro terminar'
 return phrase[0].upper()+phrase[1:]+'.'

pattern=r'<span class="line"><span class="num">(\d+)</span><code>(.*?)</code></span>'
original=[]
def replace(m):
 raw=html.unescape(m.group(2)); original.append(raw)
 explanation=note(raw); stats['lines']+=1
 if explanation.startswith('Continua a declaração'):stats['structural_continuations']+=1
 return f'<span class="line"><span class="num">{m.group(1)}</span><code>{m.group(2)}</code><span class="meaning">{html.escape(explanation)}</span></span>'
page,count=re.subn(pattern,replace,page)
expected=sum(len(p.read_text(encoding='utf-8-sig').splitlines()) for base in (root,root.parent/'xmqr-client') for p in (base/'src').rglob('*.rs'))
assert count==expected,(count,expected)
css='''.source{max-height:740px;min-width:0}.line{display:grid;grid-template-columns:48px minmax(300px,1.1fr) minmax(340px,1fr);min-width:800px;border-bottom:1px solid #172b40;align-items:start}.num{width:auto;padding:8px 10px}.line code{white-space:pre-wrap;overflow-wrap:anywhere;padding:8px 12px;color:#d9e7f5}.meaning{white-space:normal;font:13px/1.65 system-ui,sans-serif;padding:8px 16px;border-left:1px solid #304459;color:#afd2cb}.line:nth-child(even){background:#0d1928}.source::before{content:'LINHA · CÓDIGO RUST · EXPLICAÇÃO DA INSTRUÇÃO';display:block;padding:14px;color:#8de2b5;font:600 13px system-ui;position:sticky;top:0;background:#102033;z-index:1}@media print{.source{max-height:none;overflow:visible}.line{min-width:0;grid-template-columns:36px 1fr 1fr}.meaning,.line code{font-size:9px;color:#111}}'''
page=page.replace('</style>',css+'</style>')
page=page.replace('fontes completas numeradas e leitura detalhada','fontes completas numeradas, notas por linha e leitura detalhada')
page=page.replace('fontes completas numeradas para consulta.','fontes completas numeradas com notas de instrução ao lado de cada linha.')
page=page.replace('O HTML não afirma que cada linha dos demais módulos já recebeu uma explicação semântica individual.','Todas as linhas possuem notas sobre a instrução ou estrutura. As notas por linha são assistência de leitura baseada em sintaxe e operações reconhecidas; não substituem uma auditoria semântica humana de cada transição.')
page=page.replace('Código completo numerado —','Código com explicação ao lado —')
page=page.replace('mas a leitura semântica instrução por instrução está concentrada','com notas de leitura para todas as linhas. A análise semântica aprofundada está concentrada')
page=page.replace('Mostrar a fonte não equivale a explicar cada linha.','As notas estruturais de continuação identificam a participação da linha na expressão; os efeitos completos dependem das chamadas e tipos. Esses trechos permanecem candidatos a aprofundamento humano.')
page=page.replace('Índice extraído das declarações textuais;',f'Cada uma das {count:,} linhas tem nota ao lado, incluindo comentários e delimitadores. {stats["structural_continuations"]} linhas receberam nota de continuação estrutural, sem inferência de efeito de negócio. Índice extraído das declarações textuais;')
page=page.replace('Mostrar a fonte não equivale a explicar cada linha.','Notas automáticas de sintaxe não equivalem a revisão semântica integral.')
assert len(re.findall(r'<span class="meaning">',page))==expected
path.write_text(page,encoding='utf-8')
print(dict(stats))
