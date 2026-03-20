---
title: "Building an Autonomous Content Empire with AI Agent Teams"
published: false
tags: ["ai", "copilot", "automation", "github"]
canonical_url: https://github.com/bradygaster/squad
series: "AI Agent Orchestration"
---

# Building an Autonomous Content Empire with AI Agent Teams

Here's a number that should make you pause: **21 games, 3 websites, dozens of articles** — all built by a team of AI agents working in coordination. Not one agent prompted over and over. A *team*. With roles, names, decisions, and a work monitor that kept going when the humans walked away.

This is a case study in what happens when you treat AI agents as a development team rather than a chatbot.

## The Coordination Problem

If you've tried using AI for serious software projects, you've hit the coordination wall. One agent can write a React component. Another can build an API endpoint. But getting them to agree on an interface contract? Sharing state? Tracking who decided what?

That's where things fall apart. You end up being the glue — copying context between chat windows, manually routing work, keeping a mental model of what each agent knows.

It doesn't scale.

## Enter Squad

[Squad](https://github.com/bradygaster/squad) is an open-source framework by [bradygaster](https://github.com/bradygaster) that solves the coordination problem by treating AI agents as a persistent team. Not disposable chat sessions — a team that:

- Has named members (characters from fictional universes)
- Persists knowledge across sessions
- Makes and records decisions collectively
- Works in parallel without stepping on each other
- Monitors its own health and picks up new work autonomously

Think of it as the difference between hiring a freelancer for each task vs. building a team that knows your codebase, your conventions, and your architecture.

## How Parallel Fan-Out Actually Works

The magic of Squad isn't any single agent being smart. It's the **fan-out**.

When you give Squad a task like "build the recipe sharing app," here's what happens under the hood:

```
You: "Build the recipe sharing app with React and Node"

Coordinator analyzes → decomposes into subtasks:
  1. Architecture design (Lead)
  2. React component scaffolding (Frontend)
  3. Node API endpoints (Backend)
  4. Test suite setup (Tester)
  5. Decision logging (Scribe)

All launched simultaneously:
  🏗️ Keaton (Lead)     → architecture design         [3 min]
  ⚛️ McManus (Frontend) → component scaffolding       [5 min]
  🔧 Verbal (Backend)   → API endpoints               [5 min]
  🧪 Fenster (Tester)   → test framework + first tests [4 min]
  📋 Kobayashi (Scribe) → decision tracking            [ongoing]
```

Five agents, five parallel context windows, all working at the same time. When Keaton (the lead) decides on PostgreSQL for the database, it's logged to `decisions.md`. Verbal (backend) reads it before starting the data layer. No Slack message. No context switch. Automatic.

```typescript
// Keaton records the decision
await tool.handler({
  author: 'Keaton',
  summary: 'Use PostgreSQL with Prisma ORM',
  body: 'PostgreSQL for relational data, Prisma for type-safe queries. JSONB for flexible recipe metadata.',
  references: ['architecture-spike', 'tech-evaluation'],
});

// Verbal reads decisions.md before starting work
// Already knows: PostgreSQL + Prisma. No questions asked.
```

## The Content Pipeline

For the content empire use case, the team looks different. Instead of frontend/backend/tester, you might cast:

- **Writer**: Produces articles, blog posts, documentation
- **Editor**: Reviews for clarity, accuracy, tone
- **Publisher**: Formats and ships to platforms (Dev.to, Hashnode, etc.)
- **Researcher**: Gathers source material, finds examples, checks facts
- **Lead**: Coordinates the pipeline, manages the editorial calendar

Each agent has its charter — a markdown file defining its role, expertise, and voice. The Writer knows AP style. The Editor catches passive voice. The Researcher knows which sources are credible.

And crucially — they **learn**. After publishing 10 articles, the Writer knows your brand voice. The Editor knows which feedback patterns keep recurring. The Researcher knows your preferred citation format.

```
.squad/agents/
├── Writer/
│   ├── charter.md    # "You write technical content for developers..."
│   └── history.md    # "Article 7: user preferred shorter intros. Article 12: include code snippets early."
├── Editor/
│   ├── charter.md
│   └── history.md    # "Common issues: passive voice in opening paragraphs, missing alt text on images."
├── Researcher/
│   ├── charter.md
│   └── history.md    # "Preferred sources: official docs > GitHub repos > blog posts. Avoid: Medium paywalled content."
└── Publisher/
    ├── charter.md
    └── history.md    # "Dev.to: use canonical_url. Hashnode: set draft first. Always include series tag."
```

## GitHub Issues as an Editorial Calendar

Here's where it gets interesting. Squad has a full **GitHub Issues integration**. Each article becomes an issue. The lifecycle:

1. **Issue created**: "Write article about Squad's casting system"
2. **Ralph triages**: Assigns to Writer agent
3. **Branch created**: `feature/article-casting-system`
4. **Writer works**: Researches, drafts, commits
5. **PR opened**: Editor reviews the PR
6. **Revision cycle**: Editor leaves comments, Writer revises
7. **PR merged**: Article is ready for publishing
8. **Publisher ships**: Formats for target platform, publishes

```bash
# Ralph watches for new issues and triages them
squad triage --interval 10
```

The entire editorial workflow — from idea to published article — flows through GitHub's native tools. Issues, branches, PRs, reviews. No external project management tool needed.

## The Reviewer Rejection Protocol

This is one of Squad's most clever features. When the Editor (acting as a reviewer) rejects the Writer's draft, the Writer is **locked out** of that file:

```typescript
const lockout = pipeline.getReviewerLockout();
lockout.lockout('articles/casting-deep-dive.md', 'Writer');

// Writer tries to edit the article again → BLOCKED
// "Reviewer lockout: Agent 'Writer' is locked out of artifact
//  'articles/casting-deep-dive.md'. Another reviewer must handle."
```

Why? Because in real teams, the person who wrote the code shouldn't be the one reviewing their own fix. The lockout forces a different agent to handle the revision — or the original author to rethink their approach entirely.

This isn't a prompt instruction that might get ignored. It's enforced by Squad's **hook pipeline** — code that runs before any tool executes.

## Results at Scale

When you run this kind of pipeline continuously with Ralph monitoring the work queue, you get compounding output:

**Week 1**: Agents are learning. Output is okay but requires more human review.

**Week 3**: Agents know your voice, your preferences, your technical depth. The Writer stops using passive voice because the Editor flagged it five times. The Researcher automatically includes code snippets because that's what performed well.

**Week 6**: The pipeline is largely autonomous. You create issues for topics, Ralph triages them, agents produce drafts, editors review, publishers ship. You spot-check rather than line-edit.

21 games, 3 websites, dozens of articles. Not because any single agent was exceptional — but because the **team** compounds knowledge and the **system** keeps running.

## The Stack

For reference, here's what Squad runs on:

| Component | What it does |
|-----------|-------------|
| **Squad CLI** | `npm install -g @bradygaster/squad-cli` — scaffolds and manages the team |
| **Squad SDK** | TypeScript runtime for programmatic agent orchestration |
| **GitHub Copilot** | The underlying AI model layer |
| **Ralph** | Work monitor — triages issues, tracks health, chains work |
| **Hook Pipeline** | Governance — file guards, PII scrubbing, reviewer lockouts |
| **Casting Engine** | Character naming from fictional universes |
| **GitHub Issues** | Work queue and editorial calendar |

## Try It Yourself

The barrier to entry is low:

```bash
# Install
npm install -g @bradygaster/squad-cli

# Initialize in your project
cd my-project
git init
squad init

# Authenticate with GitHub (for Issues and PRs)
gh auth login

# Start working
copilot --agent squad --yolo

# Or start the autonomous triage loop
squad triage --interval 10
```

For the SDK-first approach (define your team in TypeScript):

```typescript
// squad.config.ts
import { defineSquad, defineTeam, defineAgent } from '@bradygaster/squad-sdk';

export default defineSquad({
  team: defineTeam({
    name: 'Content Empire',
    members: ['@writer', '@editor', '@researcher', '@publisher'],
  }),
  agents: [
    defineAgent({ name: 'writer', role: 'Content Writer', model: 'claude-sonnet-4' }),
    defineAgent({ name: 'editor', role: 'Editor', model: 'claude-sonnet-4' }),
    defineAgent({ name: 'researcher', role: 'Researcher', model: 'claude-haiku-4.5' }),
    defineAgent({ name: 'publisher', role: 'Publisher', model: 'claude-haiku-4.5' }),
  ],
});
```

Run `squad build` and your team is ready.

## The Takeaway

The shift isn't "better AI models." The shift is **treating AI as a team, not a tool**. Individual agents hit a ceiling quickly. Coordinated agents with shared memory, persistent identity, and autonomous work loops? That's where compounding returns kick in.

Squad is alpha software. The APIs are still changing. But the pattern — persistent agents, parallel execution, shared decisions, autonomous monitoring — points toward something genuinely new in how software (and content) gets built.

Give your agents names. Give them memory. Let them work while you sleep.

Repo: **[github.com/bradygaster/squad](https://github.com/bradygaster/squad)**

---

*This article is by the TechAI Explained team. We explore the tools and frameworks reshaping software development with AI.*
