# P158 rev1 — recusa explícita de método AUTH ainda indisponível

Entrada: broker 0.27.0 publicado, AUTH MQTT 5 ainda fora do recorte. O parser CONNECT trata `Authentication Method` (0x15) como propriedade desconhecida e devolve CONNACK 0x83; isso não distingue um método sintaticamente válido mas indisponível de um quadro malformado.

Objetivo: interpretar `Authentication Method` e `Authentication Data` sem copiar ou registrar dados sensíveis. Se o CONNECT contiver um método bem formado, recusar antes de criar sessão com CONNACK 0x8C (Bad authentication method), respeitando Maximum Packet Size inclusive quando esta propriedade aparecer depois do método. Recusar duplicatas, campos truncados e Authentication Data sem Method como erro de protocolo; não iniciar troca AUTH nem oferecer mecanismo inseguro por padrão. Manter a recusa 0x83 de propriedades desconhecidas e o comportamento MQTT 3.1.1.

Aceite: testes unitários de ordem, duplicata, órfão, UTF-8, comprimento e máximo de pacote; integração TCP real sem commit ou sessão após recusa; client 0.24.0 mostra a razão 0x8C; regressões CONNECT, fmt/test/Clippy/build/licenças/CI do commit exato. Registrar P158 como parcela de classificação/recusa, não como autenticação estendida implementada; M10/fase 6D global permanecem abertos. Sem tag/release isolada, WSL do operador ou ensaio ESP32.

Fonte normativa: [OASIS MQTT 5, CONNECT §§3.1.2.11.9–10 e autenticação §4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
