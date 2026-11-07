# P262 - Manager Terminal Linux

- Prompt: ../broker/262-linux-terminal-manager.md v1.2; data2026-11-03.
- Pedido: funcionalidade como Manager Windows pelo terminal Linux/Oracle.
- Entrada: broker HEAD7c7a989; multiplos arquivos P257/P259/P260/P261 e logs
  preexistentes preservados; adminA29 nao alterado. Nenhum Rust/Cargo mudou.

## Diagnostico anterior dos paineis

Oracle: instalador fixa xmqr-admin_0.11.0-1_amd64.deb por SHA
fe03ffc858e7583e7d8ce6808b4f56495c688beb69d47870db7fe0c1b8b55469;
tagv0.11.0 commit4483a356196db93f99340bc7aa3b3cabfc4af810. Assets daquela
tag tem Visao geral/Operacoes/Sobre e token. HEADlocal28fea432 inclui A23
Console MQTT, A24 contas/sessoes/papeis e A25 indicadores, posteriores a tag.
Manifestos dos dois marcos continuam0.11.0. Assets sao include_str! no binario;
nao basta copiar HTML para atualizar o servico antigo.

Executavel instalado C:\Program Files\XMQR\Admin\xmqr-admin.exe SHA256
42687cfe339a593fa8b0fff479bc833322ce2da1dea0d5160735aaaae0b4a8bc coincide
com artefato A28 documentado. Consulta CIM do processo negada; nao inferir
seu PID/caminho de runtime por essa consulta. Screenshot e hash do instalado
confirmam a diferenca de distribuicao. A29 e fonte local adicional ainda nao
publicada/homologada; nao declarar que essa fonte ja foi instalada.

## Entrega

terminal.py adiciona CLI/menu sem GTK; compartilha backend original do Manager
Ubuntu. backend.py permanece byte-a-byte sem alteracao Git. Inventario protegido,
validacao de ExecStart, units allowlist e ordem Broker/Admin/Clients reutilizados.
Adapter exige root para controle, desativa pergunta de senha do systemctl,
troca pkexec por journalctl direto e limita logs a300entradas. Plano completo
confere configuracoes dos clients antes de qualquer parada no restart geral.
Sem elevar internamente, criar units, sudoers, credenciais ou alterar rede.

Menu e comandos: status/start/stop/restart/logs/paths, alvos individuais ou all;
client alias somente quando inequivoco. Dry-run le/plana sem executar mutacoes.
Erros do menu chegam ao handler com exit1. Bulk interrompido informa etapas
concluidas; nao promete rollback. Inicio/reinicio pode afetar conexoes MQTT.

ZIP fonte independente0.1.0-rc.1, allowlist6arquivos incluindo SHA256SUMS,
timestamps/modos fixos e checksum externo. Launcher proprio isolado em
/usr/local/bin/xmqr-manager-terminal, backend em lib proprio; guia recusa
sobrescrita e preserva o Manager desktop. Copia local entregue na pasta raiz
do agrupamento, conforme fluxo anterior. Nao instalado automaticamente na VPS.

## Validacao real

- Primeiro `python -m unittest discover -s tools/linux-manager/tests -p test_terminal.py -v`:
  14/14PASS, exit0, backend simulado em Windows.
- Revisao identificou erro capturado no menu sem exit de falha; prompt v1.2
  preparado antes da correcao e acrescentado teste de propagacao e masked.
- Uma aplicacao de patch falhou no contexto do README. Confirmado que nenhum
  arquivo daquele patch mudou; prompt revisado e reaplicacao correta.
- `python -m unittest discover -s tools/linux-manager/tests -v`:45casos,
  41PASS/4SKIP, exit0. Os4 exigem fixtures POSIX root; BLOCKED em Windows.
  Inclui16testes novos, sem alterar os testes do desktop.
- Sintaxe Python de terminal/buildzip PASS; help/version e CLI isolada do ZIP
  PASS; guarda status no Windows recusa exit2 antes de systemctl PASS.
- Dois ZIPs gerados em diretorios temporarios identicos byte-a-byte PASS;
  SHA256SUMS dos5arquivos PASS; sobrescrita de artefato existente recusada PASS.
  Hash do ZIP final entregue e checksums internos revalidados PASS.
- `git diff --check -- tools/linux-manager/README.md` PASS. Aviso local sobre
  conversao CRLF/LF nao equivale a erro. backend.py sem diff confirmado.
- Revisao de fronteiras: nao ha shell interpolado, chamada livre a executavel,
  sudo/pkexec interno, leitura de segredos em paths ou sucesso por consulta
  falha. Negativos root/unit externa/ExecStart/estado incerto/masked e falha
  parcial PASS com simulador. Nao e auditoria integral de systemd/polkit.
- Linux/WSL real, instalacao root, systemd real, Bash launcher e uso SSH/Oracle:
  NOT_RUN/BLOCKED, limites de runtime ja registrados. Nao iniciar servicos reais
  do usuario para testar. Gates Rust NOT_APPLICABLE. Sem commit/push/tag/release.
