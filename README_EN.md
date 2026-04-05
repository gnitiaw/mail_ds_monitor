### Overview

`mail_ds_monitor` is a development workspace repository built around email-monitoring-related business scenarios.  
It is used to manage:

- `back_end`: back-end project
- `front_end`: front-end project

This repository stores not only source code, but also key documents and process conventions to ensure the workflow is traceable, reviewable, testable, and reversible.

### Workspace Positioning

The goal of this repository is not just to host front-end and back-end code, but to establish a standardized engineering workflow, including:

- feature request intake and decomposition
- feature documentation
- API contract design and confirmation
- contract-based parallel development
- integration testing
- review conclusions
- release note management

### Standard Development Workflow

1. Propose a new feature  
2. Create feature documentation in `docs/features/`  
3. Create API contracts in `docs/contracts/`  
4. Confirm requirements and contracts  
5. Implement the back end  
6. Implement the front end  
7. Run integration testing  
8. Review  
9. Merge and release  

### Repository Structure

```text
mail_ds_monitor/
├─ .claude/
├─ back_end/              # Back-end project
├─ front_end/             # Front-end project
├─ docs/
│  ├─ features/           # Feature specifications
│  ├─ contracts/          # API contracts
│  ├─ reviews/            # Review conclusions
│  └─ release-notes/      # Release notes
├─ scripts/               # Workspace scripts
├─ AGENTS.md
└─ README.md
```

### Conventions

- No formal coding before feature documentation and API contracts are completed
- Front-end and back-end development must follow the agreed contracts
- All changes must be reviewable, testable, and reversible

### Key Characteristics

- Organized as a front-end / back-end workspace
- Emphasizes documentation-first and contract-first development
- Clear workflow for collaboration, maintenance, and governance
- Covers the full lifecycle from feature planning to release
- Suitable as a practical lightweight engineering workspace example

### How Codex Is Used

OpenAI Codex is continuously used in this project for:

- feature design and implementation
- documentation support
- API contract drafting
- code optimization and refactoring
- review assistance
- workspace collaboration

**This project is built and maintained with the help of OpenAI Codex.**

### Usage

This repository is a workspace repository.  
The actual runtime commands depend on the `back_end` and `front_end` subprojects.

Typical usage:

#### 1. Clone the repository

```bash
git clone https://github.com/gnitiaw/mail_ds_monitor.git
cd mail_ds_monitor
```

#### 2. Review feature docs and API contracts

Start with:

- `docs/features/`
- `docs/contracts/`

#### 3. Work inside the subprojects

Back end:

```bash
cd back_end
```

Front end:

```bash
cd front_end
```

#### 4. Complete integration, review, and release documentation

After development, update:

- `docs/reviews/`
- `docs/release-notes/`

### Value of the Repository

This repository can serve as a reference for:

- unified workspace management for front-end/back-end projects
- documentation-first / contract-first development
- AI-assisted engineering workflows
- real-world Codex-supported software development

### Recommended GitHub Topics

Recommended topics:

- `ai-assisted-development`
- `codex`
- `automation`
- `monitoring`
- `frontend-backend-workspace`
- `contract-first`

### Maintainer Note

I am the core maintainer of this project.  
This repository has evolved from real work needs, and Codex has been used throughout the lifecycle from initial build-out to ongoing iteration and review.
