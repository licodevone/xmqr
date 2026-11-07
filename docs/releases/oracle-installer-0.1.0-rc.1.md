# XMQR Oracle Installer 0.1.0-rc.1

Primeiro candidato versionado da automação de instalação Oracle/Ubuntu26
amd64. Identifica e corrige duas falhas do script inicial: comparação
incompleta de mqtt-bridge --version e Client ID25 no teste MQTT3.1.1,
cujo limite do client é23. Não modifica os executáveis publicados do broker,
client ou admin, nem o formato de persistência.

## Mudanças

- Versão própria consultável, ZIP allowlist, manifesto e checksums.
- Saída esperada: mqtt-bridge0.5.0 (xmqr-client0.43.0), com espaçamento real
  preservado na comparação do script.
- IDs de smoke compatíveis e verificador da CLI real antes de gerar PKI.
- Retomadas específicas de install-packages e mqtt-smoke, com checkpoint
  privado/integridade, reserva por tentativa e preservação de materiais.
- Logs MQTT privados por teste e primeira linha de erro identificada.
- Pacotes fixados por SHA: broker0.43.0, client0.43.0 e admin0.11.0.

## Aceite de publicação

O workflow próprio exige três cenários reais em container Ubuntu26 com
systemd, executados somente em runner GitHub hospedado e descartável:
instalação nova; reprodução/correção da comparação da bridge; reprodução/
correção do ID longo e retomada MQTT sem regenerar credenciais. O pacote é
gerado duas vezes e comparado byte a byte. Tag/release são criadas somente
após esses gates, no commit exato, sem mover tags existentes ou latest.
EVIDENCE.json contém o resultado finito e a URL da execução.

## Compatibilidade e limites

Alvo Ubuntu26.04 amd64 novo; ARM e upgrade arbitrário são recusados.
Admin19080/monitor9090 em loopback, TLS8883 com certificado/senha/ACL.
Nenhuma abertura de firewall ou mudança de cobrança. Certificados folha
365dias, CA3650dias; renovação manual e backup de PKI continuam necessários.
Pacotes e instalador permanecem experimentais, sem homologação de produção.
Falha preserva os arquivos e para os serviços novos/retomados. Não apagar
estado ou certificados para voltar a executar como instalação nova.
