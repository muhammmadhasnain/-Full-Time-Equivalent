c---
description: "Task list for AI Employee Foundation feature implementation"
---

# Tasks: AI Employee Foundation

**Input**: Design documents from `/specs/001-ai-employee-foundation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per implementation plan
- [X] T002 [P] Create requirements.txt with python dependencies
- [X] T003 [P] Create .env.example file with required environment variables
- [X] T004 [P] Create config.yaml template for application configuration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Constitutional Compliance**: All foundational components must adhere to constitutional principles:

- [X] T005 Setup vault structure with local-first architecture and privacy focus
- [X] T006 [P] Implement authentication/authorization framework with secure credential management
- [X] T007 [P] Setup vault directory structure per specification
- [X] T008 Create base models/entities that all stories depend on with traceable automation logic
- [X] T009 Configure error handling and logging infrastructure for accuracy and reproducibility
- [X] T010 Setup environment configuration management with local execution priority
- [X] T011 Implement audit trail system for all automated actions (compliance with constitutional principle of traceable automation)
- [X] T012 Configure secure credential storage using OS keyring or encrypted .env file with access controls
- [X] T013 [P] Create constants.py with application constants
- [X] T014 [P] Create exceptions.py with custom exceptions
- [X] T015 [P] Create utils.py with utility functions
- [X] T016 [P] Create vault.py model with vault operations

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Local Obsidian Vault Setup (Priority: P1) 🎯 MVP

**Goal**: Create properly structured Obsidian vault with required folder organization that supports AI automation workflows

**Independent Test**: The vault can be created with required folder structure (/Inbox, /Needs_Action, /Plans, /Pending_Approval, /Approved, /Done) and can be opened in Obsidian. The Dashboard.md file is initialized and accessible.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

- [ ] T017 [P] [US1] Unit test for vault creation in tests/unit/test_models/test_vault.py
- [ ] T018 [P] [US1] Integration test for vault CRUD operations in tests/integration/test_vault_ops.py

### Implementation for User Story 1

- [X] T019 [P] [US1] Create action_file.py model in src/models/action_file.py
- [X] T020 [P] [US1] Create plan_file.py model in src/models/plan_file.py
- [X] T021 [P] [US1] Create approval_file.py model in src/models/approval_file.py
- [X] T022 [US1] Create CLI vault commands in src/cli/commands/vault_cmd.py
- [X] T023 [US1] Implement vault initialization command in src/cli/commands/vault_cmd.py
- [X] T024 [US1] Create Dashboard.md with initial content in src/services/vault.py
- [X] T025 [US1] Update CLI main module to include vault commands in src/cli/main.py
- [X] T026 [US1] Add vault initialization to quickstart guide in README.md

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Watcher Implementation (Priority: P2)

**Goal**: Implement Gmail Watcher to monitor external inputs and create action files in /Needs_Action folder

**Independent Test**: The watcher can be started and listens for the selected input source (Gmail). When an event occurs, a properly formatted action file appears in /Needs_Action.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T027 [P] [US2] Unit test for Gmail watcher in tests/unit/test_services/test_gmail_watcher.py
- [ ] T028 [P] [US2] Integration test for watcher functionality in tests/integration/test_watcher.py

### Implementation for User Story 2

- [X] T029 [P] [US2] Create gmail_watcher.py service in src/services/gmail_watcher.py
- [X] T030 [P] [US2] Create file_monitor.py service in src/services/file_monitor.py
- [X] T031 [US2] Implement Gmail OAuth authentication in src/services/gmail_watcher.py
- [X] T032 [US2] Implement email monitoring logic in src/services/gmail_watcher.py
- [X] T033 [US2] Create action files in YAML format in src/services/gmail_watcher.py
- [X] T034 [US2] Add CLI commands for watcher control in src/cli/commands/watch_cmd.py
- [X] T035 [US2] Update orchestrator to manage watcher lifecycle in src/orchestrator.py
- [X] T036 [US2] Implement action file validation in src/models/action_file.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Claude Code Read-Write Loop (Priority: P3)

**Goal**: Implement Claude Code integration to read action files from /Needs_Action and create Plan.md files

**Independent Test**: Claude Code can read an action file from /Needs_Action and produce a structured Plan.md file with appropriate content.

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T037 [P] [US3] Unit test for Claude service in tests/unit/test_services/test_claude_service.py
- [ ] T038 [P] [US3] Integration test for Claude loop in tests/integration/test_claude_loop.py

### Implementation for User Story 3

- [X] T039 [P] [US3] Create claude_service.py in src/services/claude_service.py
- [X] T040 [US3] Implement Claude Code integration to process action files
- [X] T041 [US3] Create Plan.md files with structured content in src/services/claude_service.py
- [X] T042 [US3] Implement Plan.md schema with YAML frontmatter in src/models/plan_file.py
- [X] T043 [US3] Add file system monitoring for action files in src/services/file_monitor.py
- [X] T044 [US3] Update orchestrator to manage Claude service in src/orchestrator.py
- [X] T045 [US3] Validate Plan.md creation and content in src/services/claude_service.py

**Checkpoint**: At this point, User Stories 1, 2 AND 3 should all work independently

---

## Phase 6: User Story 4 - Human-in-the-Loop Approval System (Priority: P4)

**Goal**: Create approval system that creates approval files in /Pending_Approval and only executes actions after they are moved to /Approved

**Independent Test**: An approval file can be created in /Pending_Approval, and when moved to /Approved, the corresponding action is executed safely.

### Tests for User Story 4 (OPTIONAL - only if tests requested) ⚠️

- [ ] T046 [P] [US4] Unit test for approval system in tests/unit/test_services/test_approval_system.py
- [ ] T047 [P] [US4] Integration test for approval workflow in tests/integration/test_approval_workflow.py

### Implementation for User Story 4

- [X] T048 [P] [US4] Create mcp_stub.py service for dry-run actions in src/services/mcp_stub.py
- [X] T049 [US4] Implement approval file creation triggered by claude_service when plan requires human approval in src/services/claude_service.py
- [X] T050 [US4] Implement approval file monitoring in src/services/file_monitor.py
- [X] T051 [US4] Create approval file format in Markdown with action details in src/models/approval_file.py
- [X] T052 [US4] Implement dry-run execution with "would send" logging in src/services/mcp_stub.py
- [X] T053 [US4] Add execution logic for approved actions in src/orchestrator.py
- [X] T054 [US4] Implement file movement validation in src/services/file_monitor.py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T055 [P] Update README.md with complete setup and usage instructions
- [X] T056 [P] Documentation updates in docs/
- [X] T057 Code cleanup and refactoring
- [X] T058 Performance optimization across all stories
- [ ] T059 [P] Additional unit tests (if requested) in tests/unit/
- [X] T060 Security hardening
- [X] T061 Update quickstart.md validation
- [X] T062 Add logging service for comprehensive audit trails in src/services/logging_service.py
- [X] T063 Update Dashboard.md metrics in src/services/vault.py
- [X] T064 Implement atomic file operations with locking mechanisms

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - May integrate with US1/US2/US3 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Unit test for vault creation in tests/unit/test_models/test_vault.py"
Task: "Integration test for vault CRUD operations in tests/integration/test_vault_ops.py"

# Launch all models for User Story 1 together:
Task: "Create action_file.py model in src/models/action_file.py"
Task: "Create plan_file.py model in src/models/plan_file.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence