🌍 [English](./README.md) | [한국어](./README.ko.md) | [日本語](./README.ja.md) | [简体中文](./README.zh-CN.md) | **Español**

<div align="center">

# Make Me Unicorn

**Deja de construir a ciegas. Lanza tu SaaS con confianza.**

El checklist de lanzamiento y sistema operativo open-source para builders independientes.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![Status: v0.4](https://img.shields.io/badge/status-v0.4-blue.svg)](./ROADMAP.md)
[![CLI](https://img.shields.io/badge/cli-mmu-f59e0b.svg)](./SPEC.md)
[![Guardrails CI](https://img.shields.io/badge/ci-doctor%20%2B%20gates-22c55e.svg)](./.github/workflows/mmu-guardrails.yml)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-16a34a.svg)](./CONTRIBUTING.md)

<img src="./assets/brand/unicorn-hero.png" alt="Make Me Unicorn mascot" width="960" />

</div>

## El Problema

Estás construyendo un producto SaaS. Usas IA para programar más rápido que nunca. Pero entonces:

> "Momento... ¿agregué el flujo de recuperación de contraseña?"
>
> "El webhook de pagos... ¿es idempotente?"
>
> "¿Tengo política de privacidad? ¿Política de reembolsos? ¿OG tags?"
>
> "¿Qué decidí la semana pasada sobre el proveedor de auth? ¿Por qué?"

**No estás fallando en programar. Estás fallando en rastrear lo que importa.**

Todo builder independiente se topa con los mismos muros:

| Qué sale mal | Qué te cuesta |
|--------------|---------------|
| Te olvidas del reset de contraseña mientras construyes el login | Los usuarios se quedan bloqueados el día 1 |
| Te saltas la verificación de firma del webhook | Los atacantes replican eventos de pago |
| Lanzas sin OG tags | Cada link compartido se ve roto |
| Pierdes el contexto entre sesiones de IA | Re-explicas tu proyecto desde cero, cada vez |
| No tienes política de reembolsos | Primera disputa = cuenta de Stripe congelada |

MMU atrapa estos problemas **antes de que te cuesten usuarios, dinero o confianza**.

## Cómo Funciona

```
mmu init                    # 1. Get 534+ checklist items across 15 categories
mmu scan                    # 2. Auto-detect your stack — pre-check what you already have
mmu                         # 3. See what's done, what's missing
```

```text
  🦄  MAKE ME UNICORN — STATUS DASHBOARD

          .--*--.
         / °v°  \          Stage: HATCHING    ██████░░░░░░░░░░░░░░  22%
        |       |
         \ ___ /           📋 LAUNCH GATES
          '---'              M0 Problem Fit   ████████████████  ✓ PASS
                             M1 Build Fit     ████████████████  ✓ PASS
  🗺️ BLUEPRINTS (124/551)   M2 Revenue Fit   ████████████████  ✓ PASS
    Frontend    ██████░░ 41%   M3 Trust Fit     ████████████████  ✓ PASS
    Backend     ████████ 53%   M4 Growth Fit    ████████████░░░░  ✗ OPEN
    Auth        ██████░░ 38%   M5 Scale Fit     ███░░░░░░░░░░░░░  ✗ OPEN
    ...13 more
```

Tu unicornio evoluciona mientras construyes: Egg → Hatching → Foal → Young → Unicorn → Legendary.

## Qué Cubre MMU (Para Que No Tengas Que Recordarlo)

<table>
<tr>
<td width="33%">

**Construir el producto**
- Frontend (responsive, a11y, formularios)
- Backend (API, DB, colas)
- Auth (login, reset, OAuth, sesiones)
- Facturación (Stripe, webhooks, reembolsos)
- Testing (unitario, E2E, seguridad de agentes)

</td>
<td width="33%">

**Preparar el lanzamiento**
- SEO (OG tags, sitemap, meta)
- Legal (privacidad, términos, GDPR)
- Seguridad (CORS, rate limits, secrets)
- Rendimiento (caching, lazy load)
- CI/CD (pipeline, plan de rollback)

</td>
<td width="34%">

**Operarlo después del lanzamiento**
- Monitoreo (errores, uptime, alertas)
- Analytics (funnel, retención, eventos)
- Email (transaccional, templates)
- Accesibilidad (WCAG, navegación por teclado)
- Confiabilidad (backups, plan de incidentes)

</td>
</tr>
</table>

**534+ items. 15 categorías. Cero improvisación.**

## Para Quién Es

| Tú eres... | MMU te ayuda a... |
|-------------|-------------------|
| **Un founder que programa con IA** | Dejar de re-explicar tu proyecto en cada sesión. Mantener el contexto entre herramientas. |
| **Un desarrollador frontend** | Saber exactamente qué construir: flujos de auth, estados de error, breakpoints responsive, OG tags. |
| **Un product manager / planner** | Obtener un PRD estructurado, estrategia de precios y checklist de lanzamiento — todo en markdown. |
| **Un builder fullstack** | Rastrear frontend, backend, facturación y compliance en un solo lugar. Que no se escape nada. |

## Inicio Rápido

```bash
pip install -e .

# Option A: Start with empty templates, fill them yourself
mmu init

# Option B: Let Claude generate your project docs (requires API key)
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
mmu init --interactive        # answer 5 questions → get filled strategy, product, pricing docs
```

Luego:

```bash
mmu scan                      # auto-detect your tech stack
mmu                           # see your dashboard
mmu show frontend             # drill into any category
mmu check frontend 3          # mark items as done
mmu gate --stage M0           # verify you're ready for the next phase
mmu doctor                    # run guardrail health checks
```

## 6 Launch Gates

Piensa en estas como salidas de fase. No te las saltes.

```
M0 Problem Fit    →  Do you know WHO you're building for and WHY?
M1 Build Fit      →  Does the core product actually work end-to-end?
M2 Revenue Fit    →  Can someone pay you? And get a refund?
M3 Trust Fit      →  Privacy policy? Support path? Logging?
M4 Growth Fit     →  Will shared links look right? Can people find you?
M5 Scale Fit      →  What happens when something breaks at 3am?
```

Ejecuta `mmu gate --stage M0` para verificar. Todos los items sin marcar = NOT PASS.

## 12 Modos de Operación

Un modo por sesión. Cada modo carga solo los documentos que necesitas.

```bash
mmu start --mode backend      # loads: architecture.md, sprint, ADR logs
mmu start --mode billing      # loads: pricing.md, billing checklist, compliance
mmu start --mode growth       # loads: SEO checklist, metrics
```

Esto previene el problema #1 de programar con IA: **sobrecarga de contexto**. Tu asistente de IA recibe solo lo que necesita — no tu proyecto entero.

## Integración con IA (Opcional)

MMU funciona sin ninguna IA. Pero con Claude, se vuelve poderoso:

```bash
pip install make-me-unicorn[llm]
export ANTHROPIC_API_KEY=sk-ant-...
```

| Comando | Qué hace |
|---------|----------|
| `mmu init --interactive` | Responde 5 preguntas sobre tu producto. Claude escribe tu estrategia, spec de producto, precios, arquitectura y docs de UX. |
| `mmu start --mode X --agent` | Auto-formatea el contexto de tu sesión — pega directamente en Claude Code o cualquier LLM. |
| `mmu doctor --deep` | Claude lee tu código y docs, detecta inconsistencias, brechas de seguridad y puntos ciegos. |
| `mmu generate strategy` | Genera o actualiza cualquier doc core basado en el estado actual de tu proyecto. |

El CLI core no tiene dependencias externas. Las funciones de IA son opcionales y degradan elegantemente.

## Flujo de Sesión

Cada sesión sigue el mismo ritmo:

```
1. mmu start --mode backend      ← pick a focus, load relevant docs
2. Build / decide / validate      ← do the work
3. mmu close                      ← log what changed, what's next
```

El cierre de sesión usa tags estructurados para la memoria:

- `[DONE]` — lo que completaste
- `[DECISION]` — decisiones tomadas (crear ADR si es significativo)
- `[ISSUE]` — qué salió mal (categorizar: brecha de contexto / dirección incorrecta / conflicto doc-código)
- `[NEXT]` — primera tarea para la próxima sesión

Esto significa que tu próxima sesión arranca en **5 segundos**, no en 15 minutos de "¿dónde me quedé?"

## Ejemplo: TaskNote

Mira un ejemplo completamente llenado de MMU en acción:

```
examples/filled/tasknote/
├── docs/core/strategy.md      ← ICP, value prop, competitors
├── docs/core/product.md       ← MVP scope, user journey, P0/P1
├── docs/core/pricing.md       ← Free/Pro/Team, billing rules
├── docs/core/architecture.md  ← Next.js + FastAPI + Postgres
├── docs/adr/001_billing_provider_choice.md  ← Why Stripe?
└── current_sprint.md          ← This week's 3 goals
```

## Requisitos

- Python `3.10+`
- `pip`
- CLI core: cero dependencias externas
- Funciones de IA: `pip install make-me-unicorn[llm]`

## Estructura del Proyecto

```
make-me-unicorn/
├── src/mmu_cli/           # CLI source (Python)
├── docs/
│   ├── core/              # Strategy, Product, Pricing, Architecture, UX
│   ├── ops/               # Roadmap, Metrics, Compliance, Reliability
│   ├── blueprints/        # 15 category checklists (534+ items)
│   ├── checklists/        # M0–M5 launch gates
│   └── adr/               # Decision log templates
├── prompts/               # Session start/close/ADR templates
├── examples/filled/       # Concrete example (TaskNote)
└── tests/                 # Unit tests
```

## CI Guardrails

`mmu doctor` se ejecuta en cada PR. `mmu gate` se ejecuta para las etapas listadas en `docs/ops/gate_targets.txt`.

## Contribuir

Ver `CONTRIBUTING.md`.

## Licencia

MIT. Ver `LICENSE`.
