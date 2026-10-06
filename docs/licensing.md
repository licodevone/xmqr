# Licenciamento do XMQR

O código próprio do XMQR continua sob MIT. `LICENSE` preserva o texto integral
e `Copyright (c) 2026 Luis E. S. Pinheiro`; `Cargo.toml` declara `license = "MIT"`.
Os arquivos novos de implementação e ferramentas identificam essa licença com SPDX.
Contribuições devem preservar os avisos de autoria e ser fornecidas sob os
termos MIT do projeto, sem importar código de terceiros com termos não avaliados.

## Dependências

Cada componente mantém sua própria licença. O
[inventário de metadados](third-party-licenses.md) inclui dependências diretas,
transitivas, de desenvolvimento e de outras plataformas do `Cargo.lock`.
Uma licença `OR` representa alternativas; `AND` exige combinar condições.
O código dos clientes Mosquitto não foi incorporado ao XMQR: os executáveis
são usados externamente nos testes. Os novos testes não acrescentam crates.

```bash
python3 scripts/license_inventory.py --check
python3 scripts/license_inventory.py
```

O CI verifica a declaração MIT do projeto e a correspondência do inventário.
Esse mecanismo detecta alterações de metadados; não é uma análise jurídica,
não escolhe automaticamente licenças alternativas nem examina todos os fontes
vendorizados. Mudanças no lockfile exigem revisar o inventário antes de atualizá-lo.

## Preparação de uma distribuição

Antes de publicar binários, imagens Docker, instaladores ou firmware:

1. Inclua o `LICENSE` completo do XMQR e seus avisos de autoria.
2. Identifique os componentes efetivamente incorporados ao artefato e a opção
   de licença adotada quando existirem alternativas.
3. Inclua os textos de licença e avisos originais exigidos, inclusive NOTICE e
   componentes nativos/vendorizados, como os utilizados pelo backend criptográfico.
4. Preserve os avisos exigidos nos materiais de distribuição e registre
   alterações em código de terceiros quando os termos aplicáveis exigirem.
5. Atualize o inventário e a evidência por artefato; não rotule todas as
   dependências como MIT.

Nenhum instalador, imagem ou firmware foi publicado nesta fatia. A montagem
do pacote de avisos completos pertence ao gate de distribuição desses artefatos.
