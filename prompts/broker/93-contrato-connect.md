# P93 v1.2 — recusas CONNECT normativas em TCP real

Preparado 2026-10-13, subordinado a P89/B08. Antes de alterações runtime,
demonstrar com bytes independentes no handler/router/writer real: protocolo
MQTT com nível não suportado deve receber CONNACK 0x01; ClientID recusado
(vazio em ambos CleanSession ou acima da quota local 256 bytes) deve receber
CONNACK 0x02. SessionPresent zero e encerramento sem processar pipeline.

Fonte: [OASIS MQTT 3.1.1 + errata](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html),
MQTT-3.1.2-2, 3.1.3-5/8/9, 3.1.4-1/5, 3.2.2-4/5. Não atribuir a quota
256 à norma; IDs de 1..23 bytes alfanuméricos obrigatórios continuam aceitos.
Vazio é política de recusa, não geração implícita de IDs. Nome errado, flags
inválidas e UTF-8 inválido fecham sem CONNACK. TLS/ACL não são relaxados.

Primeiro adicionar regressões cfg(test,unix) e executar baseline com falha
esperada. Registrar resultado, revisar este prompt antes do fix. Depois
separar erro tipado de nível no codec, verificar ID antes de autenticação e
registro, reutilizar constante da store sem alterar formato/quota/actor.
Aceitar limites 256 bytes e UTF-8 válido, recusar 257 com resposta correta;
malformados, pipeline, zero commits e router saudável são negativos exigidos.
Todos os sockets loopback e diretórios temporários próprios, sem operador.

Ownership coordenador: mod.rs, connect_contract_tests.rs, erro mínimo em
codec.rs (agente P90 informado), visibilidade de MAX_CLIENT_ID_BYTES em
store.rs. Gates targeted antes/depois, fmt/test locked/clippy e integração
externa em P91. MIT e avisos preservados; versão/distribuição em P92/P89.

## Revisão1.1 antes do fix

Regressões adicionadas antes do runtime. Compilação targeted inicialmente
bloqueada por módulo P90 ainda ausente e erros do harness concorrente; não
chamar isso de falha MQTT. P91 wire externo baseline0.11.5 executou19casos:
17PASS, 2FAIL ClientIDvazioCS0/1 (EOF sem CONNACK2), reproduzindo gap. Inspeção
do decoder demonstra nível recusado como erro genérico; targeted reproduzirá
esta recusa também. Corrigir distinção de erro e ID antes do registro, sem
relaxar nenhum negativo, depois reexecutar targeted/matriz externa completa.

## Revisão1.2 antes do ajuste de teste

Pós-fix targeted4PASS,1.04s; revisão independente sem achado runtime. Clippy
detectou byte_char_slices no novo teste que constrói ID257UTF8bytes. Trocar
chain([b'a']) por chain(*b"a"), sem suprimir aviso/mudar limite ou assert.
Não alterar runtime para resolver lint do harness.
