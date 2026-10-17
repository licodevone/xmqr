# P138 — Topic Alias de entrada MQTT 5

- [Prompt P138 rev1–rev7](../broker/138-topic-alias-entrada-mqtt5.md) criado antes da implementação. Base: distribuição P137 aceita; fases 6A–6D abertas.
- Primeiro gate `cargo test --locked --quiet`: FAIL (153 passaram, 5 falharam, 6 ignorados). Os cinco negativos são expectativas antigas de CONNACK de 10 bytes; o anúncio de Topic Alias Maximum aumenta o pacote para 13 bytes. Nenhuma conclusão de aceite neste ponto. Prompt revisado para exigir vetores do novo pacote e preservar fallback sob limite de tamanho.
- Segundo gate: testes PASS (159 na suíte principal, 6 ignorados e suítes de integração Rust); Clippy FAIL por cast `u16 as u8` no CONNACK. Prompt revisado antes da correção de tipo. Build, integração TCP externa, CI e aceite: pendentes.
- Terceiro gate: suíte principal PASS, Clippy FAIL (E0716) no teste ACL acrescido durante o gate; o resultado da suíte anterior não valida esse teste novo. Prompt revisado antes de corrigir a asserção.
- Quarto gate: teste ACL PASS; Clippy FAIL pelo limite de linhas da função de contrato (127/100). Prompt revisado para extrair helper antes de nova validação.
- Quinto gate: teste ACL PASS; Clippy ainda FAIL por 104/100 linhas na função. Extrair a sequência para helper adicional.
- Sexto gate: teste ACL, Clippy e builds PASS; script TCP executou alias QoS0/1/2, rebind, reset e client independente, mas falhou no Mosquitto por Client ID vazio recusado pela política XMQR. Prompt rev7 ajusta o fixture para ID explícito. P134/P136 não foram executados porque o gate interrompeu antes.
- Sétimo gate: `verify_mqtt5_topic_alias.py` PASS (QoS0/1/2, rebind, reset, client C73 e Mosquitto); regressões P134/P136 PASS; fmt, 159 testes principais + suítes Rust, Clippy, release/debug build e licenças PASS. O teste de ACL com alias negado/permitido PASS. Nenhum teste físico ESP32 executado.
- Fonte exata, CI e aceite final: pendentes antes do commit/push.
