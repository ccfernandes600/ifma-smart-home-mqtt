# Regras deste projeto

**Antes de ler ou editar qualquer arquivo aqui, leia `CLAUDE.md` nesta mesma pasta.**
Ele é a fonte única das regras de ifma-smart-home-mqtt — arquitetura, convenções, travas e o que é
proibido. Este arquivo é só um ponteiro: as regras NÃO são repetidas aqui de propósito,
para não existirem duas versões que divergem.

Se houver um `CLAUDE.md` na raiz do workspace E um no subprojeto, valem os dois: o da
raiz dá o contexto geral, o do subprojeto manda no caso específico.

## Você não está sozinho neste repositório

Três agentes de IA editam estes projetos (Claude Code, Antigravity CLI `agy`, Copilot CLI). As
regras de convivência — divisão de trabalho, arquivos congelados e protocolo de
entrega — estão em `~/projetos/FORCA-TAREFA.md`. **Leia antes de editar.**

Em resumo: não toque em `prompts/`, `.claude/skills/` nem em nenhum `CLAUDE.md`
sem passar pelo Claude Code; não releia o workspace inteiro para uma tarefa pontual;
e ao terminar devolva a saída do verificador, não o diff.

## Verificador (rode ao terminar, e cole a saída)

```bash
python3 verificacao/verificar.py
```

Ele precisa terminar em `TUDO CERTO`. Não roda o código (isso só acontece dentro do
Packet Tracer) — confere as regras que o simulador não perdoa: sintaxe, restrição
pedagógica (sem `class`), pacotes que existem no PT, `customRead()` sempre com
`.strip()`, orçamento de portas por controlador, porta repetida, comentário de pino
que mente, padrão dos tópicos MQTT e integridade do V3.

Se já estiver vermelho ANTES da sua tarefa, avise em vez de tentar consertar.

Idioma de todo conteúdo, código, comentário e documentação: **português do Brasil**.
