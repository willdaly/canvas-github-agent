# AGNTCY IoA Roadmap

## Goal

Evolve the app from a deterministic Canvas assignment workflow into a coordinator that can:

- plan assignment work as explicit subtasks
- discover external agents using AGNTCY-compatible metadata and directories
- delegate selected subtasks to external agents when they outperform the local workflow
- record provenance, validation, and execution history for every generated artifact

The current app already exposes a stable HTTP and MCP surface, publishes service metadata, and supports async task polling. Those capabilities make it a good starting point for AGNTCY interoperability, but not yet a sophisticated Internet of Agents coordinator.

## Current State

What already exists:

- stable HTTP discovery surface in `api.py`
- MCP stdio tools and resources in `app/mcp_server.py`
- checked-in fact card and OASF record under `metadata/`
- deterministic assignment workflow in `app/agent.py`
- domain-aware local generation for maze and ML assignments
- async task lifecycle via `task_status_v1`

What is missing:

- outbound agent discovery
- outbound agent invocation
- explicit task planning and delegation
- durable workflow state
- artifact provenance and trust metadata
- evaluation loops comparing local and delegated outcomes

## Target Architecture

Introduce the following internal modules.

### Planning

- `app/planning.py`
- responsibility: convert an assignment into a structured execution plan
- primary output: `assignment_plan_v1`

Expected plan fields:

- assignment summary
- inferred domain
- required artifacts
- missing context
- candidate subtasks
- delegation recommendations
- validation requirements
- confidence score

### Discovery

- `app/registry.py`
- responsibility: discover candidate agents from AGNTCY directories, OASF records, and MCP metadata
- primary output: `agent_candidate_v1`

Expected capabilities:

- query by capability tags
- query by protocol support
- rank by trust, latency, validation history, and artifact fit
- cache directory lookups with short TTLs

### Remote Invocation

- `app/remote_agents.py`
- responsibility: invoke external agents over MCP and other supported transports
- primary output: `delegation_result_v1`

Expected capabilities:

- outbound MCP client invocation
- timeout and retry policy
- request and response normalization
- structured error reporting

### Provenance and Execution State

- `app/provenance.py`
- responsibility: attach execution lineage to every artifact and delegated subtask
- primary outputs:
  - `artifact_provenance_v1`
  - `execution_step_v1`

Expected capabilities:

- record which agent produced an artifact
- record inputs, timestamps, and validation results
- record remote endpoints and schemas used

### Durable Task Store

- `app/task_store.py`
- responsibility: replace the in-memory task store in `api.py`
- first implementation target: SQLite

Expected capabilities:

- resumable tasks
- step-level status
- stored results and errors
- provenance persistence

## External Contract Changes

The existing `/create` and `/tasks` contract should remain stable. Add new endpoints for planning, discovery, and execution tracing.

### Proposed HTTP Endpoints

- `POST /plan`
  - generate `assignment_plan_v1` without executing it
- `POST /discover-agents`
  - return ranked candidate agents for requested capability groups
- `POST /tasks/{task_id}/resume`
  - resume a persisted task after retryable failure
- `GET /tasks/{task_id}/steps`
  - list `execution_step_v1` records for the task
- `GET /tasks/{task_id}/artifacts`
  - list generated artifacts with provenance
- `GET /agents/candidates`
  - return cached ranked candidates by capability and trust profile

### Proposed MCP Tools

- `plan_assignment`
- `discover_agents`
- `list_task_steps`
- `list_task_artifacts`
- `resume_task`

### Proposed MCP Resources

- `canvas-assignment-workflow://schemas/assignment-plan-v1`
- `canvas-assignment-workflow://schemas/delegation-result-v1`
- `canvas-assignment-workflow://schemas/artifact-provenance-v1`

## Proposed Schemas

### `assignment_plan_v1`

Top-level fields:

- `status`
- `service`
- `assignment`
- `plan`
- `recommendations`
- `confidence`

`plan` should include:

- `domain`
- `subtasks`
- `required_artifacts`
- `delegation_candidates`
- `local_fallbacks`
- `validation_steps`

### `agent_candidate_v1`

Top-level fields:

- `agent_id`
- `name`
- `source`
- `protocols`
- `capabilities`
- `trust_level`
- `ranking`
- `invocation`
- `notes`

### `delegation_result_v1`

Top-level fields:

- `status`
- `subtask_id`
- `agent`
- `request_summary`
- `artifacts`
- `validation`
- `errors`
- `timing`

### `artifact_provenance_v1`

Top-level fields:

- `artifact_id`
- `kind`
- `producer`
- `inputs`
- `generated_at`
- `validation_status`
- `lineage`

## Delegation Strategy

The app should delegate only when one of these is true:

- an external agent advertises a clearly better-fit specialty than the local workflow
- the local workflow lacks a required capability
- an independent validator is needed before publishing outputs

The local workflow remains the default fallback.

### Initial Delegation Rules

Delegate first:

- evaluation and grading-like validation
- controlled execution or sandboxed testing
- retrieval and memory augmentation

Do not delegate first:

- final repository publishing
- direct Canvas writes beyond the current local flow
- credential-sensitive operations without explicit trust policy

## Candidate External Agent Categories

These are the first capability categories to investigate through AGNTCY discovery.

Important: this list is derived from publicly visible AGNTCY ecosystem participants and category fit. It is not a verified list of currently reachable public endpoints.

### 1. Evaluation Agents

Why they matter:

- validate that generated repos actually satisfy assignment requirements
- score artifact completeness
- catch missing tests, missing report sections, or weak alignment to the brief

Public ecosystem signals:

- Galileo
- Comet / Opik
- Arize
- Vijil
- Traceloop

Target use cases:

- rubric alignment scoring
- repo completeness checks
- report quality evaluation
- agent-output comparison over time

### 2. Execution and Runtime Agents

Why they matter:

- run generated tests, benchmarks, notebooks, and ML training safely
- validate that produced starter repos are actually executable

Public ecosystem signals:

- Dagger
- SmythOS
- Dynamiq
- AG2
- CrewAI
- VoltAgent
- Naptha AI

Target use cases:

- run maze solver tests and benchmarks
- run NSL-KDD training or smoke tests
- execute notebook workflows in controlled environments

### 3. Retrieval and Memory Agents

Why they matter:

- improve assignment grounding beyond Canvas modules and local Chroma
- preserve reusable context across related assignments

Public ecosystem signals:

- LlamaIndex
- Glean
- Weaviate
- Zep

Target use cases:

- domain-specific research augmentation
- persistent assignment memory
- better context routing for reports and code generation

### 4. Identity and Policy Services

Why they matter:

- prevent unsafe delegation
- enforce per-agent trust and data-sharing policy

Public ecosystem signals:

- Ory
- Permit
- Yokai
- Duo

Target use cases:

- trust verification
- delegation allowlists
- policy-based subtask routing

## Discovery Workstream

This workstream should run in parallel with the architecture changes.

### Discovery Sprint A: Build Candidate Inventory

Deliverable: `docs/agntcy-agent-inventory.md`

For each candidate, record:

- organization or agent name
- capability family
- public docs URL
- advertised protocol support
- OASF availability
- MCP availability
- auth model
- likely assignment use case
- privacy risk
- integration priority

Primary data sources:

- AGNTCY Directory
- AGNTCY OASF records
- public MCP metadata
- vendor documentation when directory metadata is incomplete

### Discovery Sprint B: Select Pilot Integrations

Choose three pilots:

- one evaluation agent
- one execution agent
- one retrieval or memory agent

Selection criteria:

- public metadata quality
- realistic authentication path
- low privacy risk
- strong relevance to assignment generation quality

### Discovery Sprint C: Run Bakeoff

Compare these workflows on the same assignments:

- local only
- local plus evaluation
- local plus execution
- local plus retrieval
- local plus evaluation plus execution

Measure:

- test pass rate
- artifact completeness
- report quality
- hallucination rate
- human cleanup time

## Implementation Phases

### Phase 1: Planning and Durable State

Scope:

- add `assignment_plan_v1`
- add `POST /plan`
- add SQLite-backed task store
- add execution-step persistence

Acceptance criteria:

- planning can run without publishing artifacts
- task state survives process restart
- task steps can be listed independently from final result

### Phase 2: Agent Discovery

Scope:

- add registry client abstraction
- add candidate ranking
- add `POST /discover-agents`
- add `plan_assignment` and `discover_agents` MCP tools

Acceptance criteria:

- planner can return ranked delegation candidates for at least one subtask
- discovery results are cached and explain ranking decisions

### Phase 3: Evaluation-Agent Integration

Scope:

- integrate one external evaluation agent
- attach validation results to generated artifacts
- compare local-only vs delegated quality

Acceptance criteria:

- one generated repo can be evaluated by an external agent
- evaluation output is persisted as provenance
- failed evaluations can block auto-publish when configured

### Phase 4: Execution-Agent Integration

Scope:

- integrate one external execution or sandbox agent
- delegate test or benchmark execution
- collect run summaries and logs

Acceptance criteria:

- maze and ML generated projects can be smoke-tested through delegated execution
- execution result is visible in task steps and artifact provenance

### Phase 5: Retrieval-Agent Integration

Scope:

- integrate one external retrieval or memory service
- merge external retrieval with Canvas and Chroma context

Acceptance criteria:

- planner can choose local, external, or merged context sources
- resulting context provenance is visible to downstream consumers

### Phase 6: Trust, Policy, and Evaluation Loops

Scope:

- trust levels for candidate agents
- delegation allowlists
- evaluation scorecards per external agent

Acceptance criteria:

- delegation policy is enforced before outbound calls
- agent scorecards influence future ranking

## Proposed File-Level Implementation Sequence

1. add `app/task_store.py`
2. add `app/planning.py`
3. add `app/registry.py`
4. add `app/provenance.py`
5. add `app/remote_agents.py`
6. update `api.py`
7. update `app/mcp_server.py`
8. update `app/agent.py`
9. add tests:
   - `tests/test_planning.py`
   - `tests/test_registry.py`
   - `tests/test_task_store.py`
   - `tests/test_remote_agents.py`
10. add `docs/agntcy-agent-inventory.md`

## Risks

- public metadata may exist before stable public invocation endpoints do
- some candidate agents may require auth flows that are not automation-friendly
- delegation can expose assignment data to third parties without strict policy
- evaluation agents can improve confidence while still missing course-specific nuances

## Decision Rules

Use an external agent only if at least one of these is true:

- it performs a clearly isolated specialty better than the local app
- its output can be validated independently
- the privacy and trust cost is acceptable

Do not delegate when:

- local execution is already deterministic and sufficient
- required data should not leave the local trust boundary
- the external agent cannot provide stable metadata or reproducible outputs

## Immediate Next Branch

Recommended next implementation branch goal:

- add planning plus durable task state
- define discovery interfaces
- keep real external invocation behind feature flags until the first pilot agent is verified

That sequence keeps the app shippable while opening the path to real AGNTCY-native delegation.