---
title: "Squad: The AI Agent Team You Didn't Know You Needed"
published: true
tags: ["ai", "copilot", "automation", "github"]
canonical_url: https://github.com/bradygaster/squad
cover_image: ""
series: "AI Agent Orchestration"
---

# Squad: The AI Agent Team You Didn't Know You Needed

What if you could type one command and get an entire development team — lead, frontend engineer, backend engineer, tester, and a scribe who tracks every decision — all powered by AI agents?

That's exactly what [Squad](https://github.com/bradygaster/squad) does.

## Wait, Another AI Tool?

I know what you're thinking. *"Great, another AI wrapper."* Fair. But Squad isn't a chatbot with multiple personalities. Each agent runs in **its own context window**, reads only its own charter and history, and writes back what it learned. There's no single mega-prompt pretending to be five people.

Here's the mental model: Squad gives you a persistent AI development team through GitHub Copilot. You describe what you're building. Squad proposes specialists. You approve. They start working — *in parallel*.

```
You: "Team, build the login page"

  🏗️ Lead — analyzing requirements...          ⎤
  ⚛️ Frontend — building login form...          ⎥ all launched
  🔧 Backend — setting up auth endpoints...     ⎥ in parallel
  🧪 Tester — writing test cases from spec...   ⎥
  📋 Scribe — logging everything...             ⎦
```

No waiting in queue. No sequential hand-offs. True parallel fan-out.

## The Casting System (This Is the Fun Part)

Every Squad team gets **character names from fictional universes**. Your lead isn't "Agent-1." Your lead is *Keaton*. Your frontend dev is *McManus*. Your backend is *Verbal*. Your tester is *Fenster*.

Yeah — The Usual Suspects (1995).

```typescript
const casting = new CastingEngine({
  universe: 'usual-suspects',
  agentCount: 5,
});

const cast = casting.castTeam({
  roles: ['lead', 'frontend', 'backend', 'tester', 'scribe'],
});

// Result:
// { role: 'lead', agentName: 'Keaton' }
// { role: 'frontend', agentName: 'McManus' }
// { role: 'backend', agentName: 'Verbal' }
// { role: 'tester', agentName: 'Fenster' }
// { role: 'scribe', agentName: 'Kobayashi' }
```

But it's not just The Usual Suspects. Squad ships with themes from **Alien**, **Star Wars**, **Ocean's Eleven**, and more. The names persist across sessions — if Keaton is your lead today, Keaton is your lead next week, next month. You start saying things like "Keaton handles the routing layer" and it just *sticks*.

Why does this matter beyond the fun factor? **Memory**. Each agent has a `history.md` that compounds over time. After a few sessions, Keaton knows your architecture decisions. McManus knows you prefer Tailwind. The agents stop asking questions they've already answered.

## How It Actually Works

Getting started is dead simple:

```bash
npm install -g @bradygaster/squad-cli
mkdir my-project && cd my-project
git init
squad init
```

This scaffolds a `.squad/` directory in your project:

```
.squad/
├── team.md              # Who's on the team
├── routing.md           # Who handles what
├── decisions.md         # Shared decision log
├── casting/
│   ├── policy.json      # Which universe, how many agents
│   └── registry.json    # Persistent name mappings
├── agents/
│   ├── Keaton/
│   │   ├── charter.md   # Identity, expertise, voice
│   │   └── history.md   # What Keaton knows about YOUR code
│   ├── McManus/
│   │   ├── charter.md
│   │   └── history.md
│   └── ...
└── log/                 # Searchable session history
```

**You commit this entire folder.** Anyone who clones your repo gets the team — with all their accumulated knowledge. It's versioned team memory living in git.

Then fire it up:

```bash
copilot --agent squad --yolo
```

> The `--yolo` flag auto-approves tool calls. Without it, Copilot asks you to confirm each one — and Squad makes *a lot* of tool calls.

Or use the interactive shell:

```bash
squad
# squad > @Keaton, analyze the architecture of this project
# squad > McManus, write a blog post about our new feature
# squad > Build the login page
```

The coordinator routes messages to the right agents. Multiple agents can work in parallel — you see progress in real-time.

## Decisions Are Tracked (Not Lost in Chat)

One of my favorite details: every decision any agent makes gets logged to `decisions.md`.

```typescript
const result = await tool.handler({
  author: 'Keaton',
  summary: 'Use PostgreSQL, not MongoDB',
  body: 'We chose PostgreSQL because: (1) transactions, (2) known team expertise, (3) schema flexibility via JSONB.',
  references: ['PRD-5-coordinator', 'architecture-spike'],
});
```

This isn't just logging — it's a **shared brain**. Every agent reads `decisions.md` before starting work. When Keaton decides on PostgreSQL, McManus and Verbal know about it immediately. No Slack thread where someone @-mentioned the wrong channel.

## The Safety Net

Squad isn't just "AI agents go brrrr." There's governance:

- **File-write guards**: Agents can only write to paths you allow (`src/**`, `.squad/**`, `docs/**`). Try to write to `/etc/passwd`? Blocked. Not by a prompt — by code.
- **PII scrubbing**: Email addresses and sensitive data are automatically redacted in agent output.
- **Reviewer lockout**: When the Tester rejects Backend's auth code, Backend literally *cannot* re-edit that file. Another agent has to fix it. Protocol enforced.
- **Ask-user rate limiter**: Agents get a maximum number of "hey human, what should I do?" calls per session. After that, they decide and move on.

```typescript
const pipeline = new HookPipeline({
  allowedWritePaths: ['src/**/*.ts', '.squad/**', 'docs/**'],
  scrubPii: true,
  maxAskUserPerSession: 3,
});
```

This is the *hook pipeline* — rules that run as code before any tool executes. Not prompt instructions that agents might ignore. Actual guardrails.

## What Happens When You Walk Away

Here's the thing that sold me: Squad doesn't need you sitting there.

When agents finish a task, the coordinator chains follow-up work automatically. If you step away for lunch (or, let's be honest, for the day), a breadcrumb trail is waiting:

- **`decisions.md`** — every decision any agent made
- **`orchestration-log/`** — what was spawned, why, and what happened
- **`log/`** — full session history, searchable

And there's **Ralph** — a persistent work monitor that watches for completed tasks, errors, and idle agents. Ralph never sleeps. When you get back, Ralph knows exactly where everything stands.

(Ralph deserves his own article. Stay tuned.)

## Is This Actually Useful?

Look, I was skeptical. Multi-agent orchestration sounds like a buzzword salad. But Squad's design makes a few choices that change things:

1. **Agents are files, not services.** No Docker containers spinning up. No API keys to manage. Everything is markdown and JSON in your repo.
2. **Knowledge compounds.** The more you use Squad, the less time you spend explaining your project.
3. **It's all in git.** Fork the repo, you fork the team. That's kind of wild.
4. **Crash recovery is built in.** Agent dies mid-work? Sessions are durable. Next run picks up where it left off.

Squad is alpha software — the APIs are still changing. But the core idea — treating AI agents as a persistent, coordinated team rather than disposable chat sessions — feels like it's pointing somewhere important.

## Try It

```bash
npm install -g @bradygaster/squad-cli
squad init
copilot --agent squad --yolo
```

Or with npx (no global install):

```bash
npx @bradygaster/squad-cli init
```

Check out the repo: **[github.com/bradygaster/squad](https://github.com/bradygaster/squad)**

Eight sample projects, from beginner to advanced. Including casting, governance, streaming, and Docker setups.

---

*This article is by the TechAI Explained team. We explore tools and frameworks that are changing how software gets built.*
