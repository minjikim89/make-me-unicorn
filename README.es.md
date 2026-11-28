<div align="center">

# make-me-unicorn

**Una puerta de lanzamiento para agentes de programación con IA.**

Tu agente no puede hacer commit de un webhook que confía en eventos sin firmar, de una tabla de Supabase sin RLS<br>
ni de una clave `service_role` en el bundle del navegador. Determinista, sin conexión, sin cuenta, sin LLM, en unos 0.1 s.

[![PyPI](https://img.shields.io/pypi/v/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![CI](https://github.com/minjikim89/make-me-unicorn/actions/workflows/mmu-guardrails.yml/badge.svg)](./.github/workflows/mmu-guardrails.yml)
[![Benchmark](https://img.shields.io/badge/P0%20false%20positives-0%20in%2020%20OSS%20repos-22c55e)](./docs/benchmark.md)

[English](./README.md) · [한국어](./README.ko.md) · [日本語](./README.ja.md) · [简体中文](./README.zh-CN.md) · **Español**

</div>

<!-- mcp-name: io.github.minjikim89/make-me-unicorn -->

```bash
uvx make-me-unicorn install --claude    # or --codex, --cursor, --gemini, --git, --all
```

Esa es toda la configuración. A partir de ahora, cuando tu agente ejecute `git commit`, el hook analiza lo que está en staging. Un hallazgo P0 deniega el comando y le entrega al agente una corrección que puede aplicar. Salida real del commit inicial de un proyecto Next.js + Supabase + Stripe (líneas acortadas, cinco avisos P1 omitidos):

```text
mmu vibecheck: 4 blocking (P0), 5 warning(s) (P1), 0 suppressed | scope: staged (22 file(s))
P0 secrets .env:3 (+1: components/AdminPanel.tsx:8)
  what: possible hardcoded secrets in 2 file(s): Supabase service_role JWT; ... (the service_role
        key is in a "use client" file: it bypasses RLS for every visitor)
P0 client-bundle-secrets .env:6 (+1: app/api/ai/summarize/route.ts:4)
  what: secret shipped to the browser bundle via public env prefix in 2 file(s): NEXT_PUBLIC_OPENAI_API_KEY ...
P0 webhook-signature app/api/webhooks/stripe-legacy/route.ts:5
  what: 1 of 2 webhook handler(s) trust the event without verifying its signature
  fix: Verify the signature on the raw body before trusting the event, and return 400 when it fails:
       event = stripe.webhooks.constructEvent(await req.text(), req.headers.get("stripe-signature")!,
       process.env.STRIPE_WEBHOOK_SECRET!) Do not call req.json() before this: the check needs the
       exact bytes the provider signed.
  silence (only if false positive): // mmu-ignore[webhook-signature]: <reason>
P0 supabase-rls supabase/migrations/0001_init.sql:1
  what: 1 table(s) created without ENABLE ROW LEVEL SECURITY: public.invoices
  fix: Add a migration for each listed table: `alter table <schema>.<table> enable row level security;`
       plus at least one policy, e.g. `create policy "owner can read" on <table> for select using
       (auth.uid() = user_id);`. ...
Fix every P0 above, then re-run `mmu vibecheck --format agent --staged` until it reports 0 blocking.
```

El agente corrige, vuelve a ejecutar y hace commit. Cuando el código ya es correcto, la puerta no dice nada: en una prueba real con Claude Code, el agente escribió un webhook de Stripe verificado al primer intento y el commit pasó directamente.

## Por qué comprobar ausencias

Los escáneres de secretos y las herramientas SAST buscan código malo que está presente. El código escrito por agentes falla más a menudo por el código que no está: la verificación de firma que nadie escribió, la política RLS que nunca se añadió, el rate limit delante de una ruta que llama a un LLM de pago.

- Tenzai hizo que cinco agentes de programación construyeran las mismas tres aplicaciones (15 aplicaciones). Ninguna contenía un SQLi o XSS explotable; en cuanto a los controles de seguridad, "in almost all cases, they didn't even try" (en casi todos los casos, ni siquiera lo intentaron) ([SecurityWeek, enero de 2026](https://www.securityweek.com/vibe-coding-tested-ai-agents-nail-sqli-but-fail-miserably-on-security-controls/)).
- GitGuardian midió una tasa de filtración de secretos del 3.2% en commits públicos asistidos por Claude Code, frente a una referencia del 1.5% ([State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/)).

Un linter no va a señalar una función que no existe. `mmu vibecheck` lee el proyecto como un revisor que pregunta "¿dónde verificas este webhook?" y bloquea solo cuando la respuesta es claramente "en ningún sitio".

## Cómo funciona la puerta

Los agentes se saltan las herramientas opcionales. Los hooks no se los pueden saltar. `mmu install` escribe entradas de hook que llaman a `mmu hook`, que habla el protocolo de hooks de cada host.

| Host | Puerta de commit / push | Puerta de "aún no terminado" | Feedback tras editar | Flag de `mmu install` |
|------|--------------------|---------------------|--------------------|--------------------|
| Claude Code | `PreToolUse` sobre `Bash` | `Stop` | `PostToolUse` sobre `Edit`/`Write`/`MultiEdit` | `--claude` |
| Codex CLI | `PreToolUse` sobre `Bash` | `Stop` | `PostToolUse` sobre `apply_patch` | `--codex` |
| Cursor | `beforeShellExecution` | `stop` | no disponible | `--cursor` |
| Gemini CLI | `BeforeTool` sobre `run_shell_command` | `AfterAgent` | no disponible | `--gemini` |
| git | `pre-commit`, encadenando cualquier hook existente | | | `--git` |
| framework pre-commit | hook id `mmu-vibecheck` | | | `.pre-commit-hooks.yaml` |
| GitHub Actions | `uses: minjikim89/make-me-unicorn@v0.9.2`, SARIF hacia code scanning | | | |

- **La puerta de commit** analiza lo que va a contener el commit: los archivos en staging, o los archivos modificados en el caso de `git commit -a`, pathspecs y `git add ... && git commit`. Un push analiza lo que ha cambiado desde el upstream.
- **La puerta de "aún no terminado"** se ejecuta cuando el agente intenta dar la tarea por finalizada. Solo mira los archivos que el agente editó en esta sesión, así que nunca le obliga a reescribir código que no tocó. Devuelve al agente al trabajo como máximo `MMU_STOP_MAX` veces (3 por defecto); si le dijiste al agente que aplazara el endurecimiento, enumera los P0 y se detiene.
- **El feedback tras editar** devuelve como contexto los hallazgos P0 del archivo que se acaba de escribir. Nunca bloquea.
- `mmu install --all`, `--dry-run`, `--uninstall`; `--agents-md` añade un bloque de instrucciones a `AGENTS.md`, `--skill` copia la Agent Skill `mmu-vibecheck` en `.agents/skills/`. La configuración existente se fusiona, nunca se reemplaza.

Claude Code está probado en sesiones reales. Codex CLI, Cursor y Gemini CLI siguen sus contratos de hooks documentados y están probados con los payloads documentados; se agradecen informes de sesiones reales.

Restricciones de diseño, todas con pruebas:

- **Determinista.** Mismo árbol, mismos hallazgos. Sin llamadas a modelos, sin red, sin cuenta.
- **Fail-open.** Si el propio escáner falla o agota el tiempo, el comando pasa con un aviso visible. Una puerta rota nunca deja inutilizada una sesión.
- **Una persona puede saltársela.** `MMU_HOOK_DISABLE=1 git commit ...` para un solo comando; defínela en el entorno del agente para desactivar la puerta durante una sesión.
- **Rápida.** Mediana de 89 ms en 20 repositorios reales, 1.1 s en el más grande (1,699 archivos).

## Qué detecta

P0 bloquea. P1 avisa. Toda heurística de ausencia es P1 salvo que la evidencia sea específica.

| Regla | Sev | Detecta |
|------|-----|-------|
| `secrets` | P0 | Claves activas de proveedores y JWT `service_role` de Supabase en el código fuente, en la configuración o en un archivo dotenv que git no ignora |
| `client-bundle-secrets` | P0 | Secretos tras los prefijos `NEXT_PUBLIC_` / `VITE_` / `EXPO_PUBLIC_` o leídos en código de cliente |
| `supabase-rls` | P0 | Tablas creadas en migraciones sin `ENABLE ROW LEVEL SECURITY` |
| `webhook-signature` | P0 | Handlers de webhooks de Stripe, GitHub, Svix, Clerk... que usan el evento sin verificarlo |
| `sql-fstring` | P0 | SQL construido con f-strings, `%`, `.format`, template literals o concatenación y pasado a `execute` |
| `code-injection` | P0 | Datos de la petición que llegan a `eval`, `exec`, `Function` o a un shell |
| `jwt-secret-default` | P0 | Secretos de firma con un valor hardcodeado o con `|| 'fallback'` |
| `unsafe-deserialization` | P0 | `yaml.load` sin un safe loader, `pickle` sobre entrada externa |
| `git-config-exec` | P0 | Claves de `.git/config` que ejecutan un programa durante el uso normal de git (`core.fsmonitor`, `core.sshCommand`, `alias.x = !cmd`) |
| `llm-route-unthrottled` | P1 | Rutas que llaman a una API de LLM de pago sin autenticación ni rate limit |
| `admin-route-no-auth` | P1 | Rutas `/admin` sin comprobación de sesión o de rol |
| `password-reset` | P1 | Login con contraseña sin ningún flujo de recuperación o restablecimiento |
| `webhook-idempotency` | P1 | Efectos de un webhook que resultan incorrectos cuando el proveedor reintenta |
| `rate-limiting` | P1 | Un servidor sin ningún rate limiting |
| `cors-wildcard` | P1 | Orígenes `*`, `cors()` sin opciones, comodín con credentials |
| `dangerous-html` | P1 | `dangerouslySetInnerHTML` / `v-html` sobre valores sin sanitizar |
| `jwt-localstorage` | P1 | Tokens de autenticación guardados en `localStorage` / `sessionStorage` |
| `stack-trace-leak` | P1 | Detalles de excepciones devueltos al cliente |
| `sourcemaps-exposed` | P1 | Source maps de producción habilitados |
| `env-not-ignored` | P1 | Archivos dotenv con valores cuyo nombre sugiere credenciales y que git no ignora |
| `disabled-ssl` | P1 | `verify=False`, `rejectUnauthorized: false` |
| `debug-mode` | P1 | `DEBUG = True`, `app.run(debug=True)`, `--reload` en un Dockerfile |
| `error-monitoring` | P1 | Sin Sentry ni equivalente |

`mmu vibecheck --list-rules` imprime esta tabla; `mmu vibecheck --explain <rule>` imprime qué busca una regla y cómo corregirlo.

## Precisión

Medida, reproducible y documentada con sus límites en [`docs/benchmark.md`](./docs/benchmark.md).

| Medición | Resultado |
|-------------|--------|
| 20 aplicaciones open source populares (starters, kits SaaS, ejemplos de frameworks), configuración por defecto | 0 hallazgos P0 erróneos tras la revisión (11 antes de la reelaboración de reglas de esta versión) |
| 12 proyectos fixture con 55 problemas plantados | Precision P0 100%, recall P0 100%, 52 de 55 problemas plantados encontrados |
| No detectado | IDOR, comparación de contraseñas en texto plano, columna password devuelta por el login: ninguna regla modela la autorización ni el flujo de datos |

Los fixtures se escribieron junto con las reglas, así que deben tratarse como una suite de regresión. El barrido de repositorios open source es la comprobación independiente.

## Uso directo

```bash
pip install make-me-unicorn          # or run any command through uvx make-me-unicorn ...
mmu vibecheck                        # whole project, human-readable
mmu vibecheck --staged               # what is about to be committed
mmu vibecheck --since origin/main    # what this branch changed
mmu vibecheck --format agent         # compact fix list for a coding agent
mmu vibecheck --format json          # schema mmu.vibecheck/v1
mmu vibecheck --format sarif --output mmu.sarif
```

Códigos de salida: `0` nada que bloquee, `1` al menos un hallazgo igual o superior a `--fail-on` (por defecto `P0`), `2` el análisis no pudo ejecutarse. Esquema JSON: [`docs/vibecheck-json-schema.md`](./docs/vibecheck-json-schema.md).

### Falsos positivos

Suprime una línea, con un motivo (una supresión sin motivo se ignora):

```ts
// mmu-ignore[webhook-signature]: verified by the API gateway before this handler runs
```

O una ruta en `.mmu/config.toml`:

```toml
[vibecheck]
ignore = ["scripts/seed.ts:secrets", "examples/**:jwt-secret-default"]
```

Para adoptar la puerta en una base de código existente: `mmu vibecheck --write-baseline` registra los hallazgos de hoy y, a partir de ahí, `mmu vibecheck --baseline` informa solo de los nuevos.

## GitHub Actions

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: minjikim89/make-me-unicorn@v0.9.2
    with:
      sarif-file: mmu.sarif
  - uses: github/codeql-action/upload-sarif@v4
    if: always()
    with:
      sarif_file: mmu.sarif
```

Los hallazgos aparecen en la pestaña Security y como anotaciones en el pull request.

## Plugin de Claude Code

```text
/plugin marketplace add minjikim89/make-me-unicorn
/plugin install make-me-unicorn@make-me-unicorn
```

Registra los mismos tres hooks desde el código fuente incluido en el plugin (requiere `python3` 3.10+, sin `pip install`), además de un comando `/vibecheck`, la skill `mmu-vibecheck` y el servidor MCP (iniciado con [uv](https://docs.astral.sh/uv/)).

## Servidor MCP

Para los agentes que prefieren preguntar: `mmu serve-mcp` expone `mmu_vibecheck`, `mmu_explain_rule` y `mmu_list_rules` (solo lectura). Funciona con el SDK de MCP v1 y v2.

```json
{
  "mcpServers": {
    "mmu": { "command": "uvx", "args": ["--from", "make-me-unicorn[mcp]>=0.9", "mmu", "serve-mcp"] }
  }
}
```

Las herramientas MCP son una comodidad. Los hooks son la puerta.

## Añadir una regla

Las reglas están en [`src/mmu_cli/vibecheck/rules/`](./src/mmu_cli/vibecheck/rules/). Una regla se entrega con un fixture en `bench/fixtures/` y los hallazgos esperados en `bench/expected/`, y debe mantener el benchmark en cero falsos positivos P0 (`python -m unittest tests.test_bench`). Consulta [CONTRIBUTING.md](./CONTRIBUTING.md).

## También en este repositorio: checklists de lanzamiento

make-me-unicorn empezó como una checklist de lanzamiento para desarrolladores en solitario, y esa parte se sigue distribuyendo: 15 categorías de checklist, puertas de lanzamiento de M0 a M5, modos de sesión enfocada y un servidor MCP de blueprints. Registra lo que un proyecto ha decidido y hecho; la puerta descrita arriba comprueba lo que el código hace realmente.

```bash
mmu init && mmu scan && mmu status
```

Detalles: [docs/checklists.md](./docs/checklists.md) y [SPEC.md](./SPEC.md).

## Licencia

MIT
