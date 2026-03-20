---
title: "How Squad's Ralph Keeps Your AI Team Working While You Sleep"
published: false
tags: ["ai", "copilot", "automation", "github"]
canonical_url: https://github.com/bradygaster/squad
series: "AI Agent Orchestration"
---

# How Squad's Ralph Keeps Your AI Team Working While You Sleep

You've got an AI development team. Five agents, all named after characters from The Usual Suspects, each with their own context and charter. The lead analyzes requirements, the frontend builds UI, the backend writes APIs, the tester writes tests, and the scribe tracks every decision.

Cool. But what happens when you close your laptop?

Meet **Ralph**.

## The Problem With Attended AI

Most AI coding tools have a fundamental limitation: they need *you* there. You prompt, they respond, you review, you prompt again. It's productive — but it's still synchronous. You are the bottleneck.

[Squad](https://github.com/bradygaster/squad) — the AI agent team framework built on GitHub Copilot — doesn't have this constraint. Agents work in parallel, make decisions, hand off tasks to each other, and keep going. But *someone* needs to watch the machine.

That's Ralph.

## What Ralph Actually Is

Ralph isn't another AI agent doing coding work. He's a **persistent monitoring session** — a work monitor that subscribes to events across all agents and keeps the whole system healthy.

```typescript
const ralph = new RalphMonitor({
  teamRoot: '.squad',
  healthCheckInterval: 30000,  // Every 30 seconds
  statePath: '.squad/ralph-state.json',
});

ralph.subscribe('agent:task-complete', (event) => {
  console.log(`✅ ${event.agentName} finished: ${event.task}`);
});

ralph.subscribe('agent:error', (event) => {
  console.log(`❌ ${event.agentName} failed: ${event.error}`);
});

await ralph.start();
```

Think of Ralph as your team's ops person. He doesn't write code. He makes sure everyone else *can* write code, and that nothing falls through the cracks.

## The Work Loop

Here's how Ralph fits into the bigger picture:

```
┌─────────────────────────────────────────┐
│  GitHub Issues (work source)            │
│  "Build user authentication"            │
│  "Fix dark mode toggle"                 │
│  "Add search to recipe list"            │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Ralph (work monitor)                   │
│  - Watches for new/updated issues       │
│  - Triages work to the right agents     │
│  - Monitors agent health                │
│  - Tracks completion                    │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │ Keaton │ │McManus │ │Verbal  │
   │ (lead) │ │(front) │ │(back)  │
   └────────┘ └────────┘ └────────┘
```

### GitHub Issues as Work Items

Squad has a full **GitHub Issues mode**. Create an issue, and Ralph picks it up. The lifecycle looks like this:

1. **Issue created** → Ralph detects it via polling
2. **Triage** → Ralph (or the coordinator) assigns it to the right agent based on routing rules
3. **Branch created** → The assigned agent creates a feature branch
4. **Work happens** → The agent codes, commits, and opens a PR
5. **Review** → The Tester agent reviews the PR
6. **Merge** → PR gets merged, issue closes

```bash
# Start the triage loop
squad triage --interval 10
```

This runs Ralph's triage watch, polling for issues every 10 minutes (configurable). You can set up labels, priorities, and routing rules so specific issue types go to specific agents.

The key insight: **you don't need to be there for any of this.**

## Idle-Watch: Keeping Agents Productive

Ralph doesn't just watch for new work. He watches for *idle* agents. If an agent finishes a task and has nothing in its queue, Ralph can:

- Pull the next issue from GitHub
- Check if any blocked tasks are now unblocked
- Chain follow-up work from completed tasks

This is the "continuous work" loop that makes Squad genuinely autonomous. It's not "do one thing and stop." It's "keep going until the work queue is empty."

## Health Monitoring

Every 30 seconds (configurable), Ralph runs health checks on the session pool:

```typescript
const result = await tool.handler({
  agentName: 'Keaton',
  status: 'active',
  verbose: true,
});
// Returns: { poolSize: 5, activeSessions: 3, sessionsByAgent: {...} }
```

Ralph tracks:
- **Active sessions**: Who's currently working?
- **Stalled agents**: Has someone been on the same task too long?
- **Crashed sessions**: Did something die silently?
- **Queue depth**: How much work is pending vs. in progress?

If an agent crashes (network hiccup, model timeout), Ralph knows. And because Squad has **persistent sessions**, the crashed agent can resume from its last checkpoint:

```typescript
const resumed = await client.resumeSession(
  '.squad/sessions/backend-auth-001.json'
);
// Backend wakes up knowing:
// - What the task was
// - What it already wrote
// - Where it was in the work
// - No repetition, no lost context
```

## State Persistence

Ralph's own state is durable too. Everything gets written to `.squad/ralph-state.json`:

- Current work queue
- Agent health snapshots
- Issue-to-agent assignments
- Completion history

This means if *Ralph himself* restarts, he doesn't lose track. He reads his state file and picks up where he left off. It's turtles all the way down — even the monitor is crash-recoverable.

## The Decision Trail

One of the most underrated aspects of Ralph's integration: **decisions cascade**.

When Keaton (the lead) makes an architecture decision — say, "we're using PostgreSQL, not MongoDB" — it gets logged to `decisions.md`. Every agent reads this file before starting work. But Ralph plays a role too: when triaging new work, Ralph can check decisions for context.

Issue: "Add data export feature"
Ralph: *reads decisions.md — team decided on PostgreSQL. Routes to Verbal (backend) with context: "Use PostgreSQL. See decision from June 12."*

The agents don't just work — they work *informed*. And the information accumulates over time in git-versioned files that anyone on your team can read.

## Setting It Up

If you're already using Squad, Ralph integration is straightforward:

```bash
# Make sure you're authenticated with GitHub
gh auth login

# Initialize Squad in your project
squad init

# Start the triage loop (Ralph watching issues)
squad triage --interval 10
```

For the SDK-level integration:

```typescript
// squad.config.ts
import { defineSquad, defineTeam, defineAgent } from '@bradygaster/squad-sdk';

export default defineSquad({
  team: defineTeam({
    name: 'Platform Squad',
    members: ['@keaton', '@mcmanus', '@verbal', '@fenster'],
  }),
  agents: [
    defineAgent({ name: 'keaton', role: 'Lead', model: 'claude-sonnet-4' }),
    defineAgent({ name: 'mcmanus', role: 'Frontend', model: 'claude-sonnet-4' }),
    defineAgent({ name: 'verbal', role: 'Backend', model: 'claude-sonnet-4' }),
    defineAgent({ name: 'fenster', role: 'Tester', model: 'claude-haiku-4.5' }),
  ],
});
```

## Why This Matters

The gap between "AI assistant" and "AI team member" is autonomy. An assistant waits for instructions. A team member picks up work, coordinates with peers, and keeps going when you're not looking.

Ralph is the infrastructure that makes team-level autonomy possible. Without Ralph:
- Agents finish a task and stop
- Crashes go unnoticed
- Work piles up in GitHub Issues with no one triaging
- You have to manually kick off each work cycle

With Ralph:
- Agents finish a task and start the next one
- Crashes trigger recovery
- Issues are triaged automatically
- Work flows continuously

Is it perfect? No — it's alpha software. But the architecture is sound. And if you've ever wished your AI tools could keep working after you close your laptop, Ralph is worth exploring.

## Try It

```bash
npm install -g @bradygaster/squad-cli
squad init
squad triage --interval 10
```

Repo: **[github.com/bradygaster/squad](https://github.com/bradygaster/squad)**

---

*This article is by the TechAI Explained team. We dig into developer tools that push the boundaries of what's possible with AI.*
