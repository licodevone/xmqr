# Da lógica ao Broker e Clientes MQTT utilizando Rust

35 slides: aula inicial sobre Rust/C/LLVM, cinco seções práticas, as 16 aulas
da reconstrução R01–R10 e encerramento. Tamanho 16:9, textos e diagramas editáveis.

- [Versão para alunos](curso-alunos.pptx): conteúdo de exibição, sem fala sugerida
  nem orientações privadas nas notas.
- [Versão do professor](curso-professor.pptx): mesmos slides, com notas em cada
  slide divididas em “Fala sugerida aos alunos”, “Orientações privadas ao
  apresentador” e fontes. As notas não aparecem na projeção dos slides.
- [Roteiro privado por slide](roteiro-professor.html): consultar a fala em outro
  dispositivo ou imprimir. Evite mostrar esta página durante a gravação.

Para distribuição aos alunos, use curso-alunos.pptx. As notas da versão do
professor fazem parte do arquivo e podem ser consultadas por quem o receber.
“Privado” descreve sua finalidade, não criptografia ou controle de acesso.

O código completo e a explicação de cada linha ficam no guia HTML do primeiro
commit, em docs/curso-udemy/primeiro-commit fora deste repositório. Os slides
explicam etapas e conceitos; trechos resumidos não substituem arquivos completos.

## Regerar

Edite [slides.json](../slides.json) e [AULA-INICIAL.md](../AULA-INICIAL.md)
somente depois de preparar/revisar o prompt. Os geradores ficam em scripts/:

```text
node scripts/build_first_commit_slides.mjs
python scripts/render_first_commit_course.py
python scripts/verify_first_commit_guide.py
node scripts/verify_first_commit_slides.mjs
```

Execute a partir da raiz do XMQR com o runtime de apresentações empacotado.
Os caminhos padrão desta máquina podem ser substituídos por XMQR_RUNTIME_ROOT
e XMQR_PRESENTATION_SKILL. Não instale substitutos na pasta desse runtime.
Pré-requisitos: artefatos P77 presentes, @oai/artifact-tool, Playwright, Python
do runtime, fontes Arial/Consolas e Edge para a verificação do guia.

Validação e previews ficam em target/p79-apresentacao; finais intermediários
validados em target/p79-entrega. O gerador copia as duas apresentações para
esta pasta versionada e para os artefatos locais do curso. Como só mudamos
material didático, não altera fonte histórica R10 nem a versão do broker/client.
