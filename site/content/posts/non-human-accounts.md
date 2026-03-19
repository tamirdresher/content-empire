---
title: "Why Your Side Project Needs a Non-Human Account"
date: 2025-07-26
author: "The Content Empire Team"
tags: ["DevOps", "automation", "security", "side-projects", "best-practices"]
description: "Using personal accounts for CI/CD, deployments, and automation is a ticking time bomb. Here's how to set up non-human (service) accounts properly — even for hobby projects."
---

You built a side project. It has CI/CD, automated deployments, maybe a Discord bot or a scheduled data pipeline. And every single one of those automations runs under **your personal account.** Your personal GitHub token, your personal API key, your personal email.

This is fine until it isn't. And when it breaks, it breaks spectacularly.

## The Horror Stories

Every experienced developer has a version of this story:

**"I rotated my personal GitHub token and broke 4 production services."** The token was embedded in CI configs, webhook URLs, and deployment scripts across multiple repos. Everything stopped at once.

**"I left the company and the nightly data pipeline died."** It used the developer's personal database credentials. Nobody knew until customers started complaining about stale data three days later.

**"My personal API key hit the rate limit because my side project went viral."** The same key was used for both the production app and personal experiments. One success killed both.

## What Is a Non-Human Account?

A non-human account (also called a service account, bot account, or machine identity) is an account that represents your application or automation rather than a person. It has its own:

- **Credentials** — API keys, tokens, SSH keys
- **Permissions** — Scoped to exactly what the automation needs
- **Identity** — Commits, deploys, and actions are attributed to the bot, not you
- **Lifecycle** — Independent of any individual contributor

## Why Even Side Projects Need One

### 1. Credential Isolation

Your personal token typically has permissions far beyond what your CI/CD needs:

```
Your personal GitHub token permissions:
✅ Read/write all repositories (public and private)
✅ Manage organizations
✅ Delete repositories
✅ Admin access to all settings

What your CI pipeline actually needs:
✅ Read/write to ONE specific repository
✅ Create releases
❌ Everything else
```

If your CI token leaks (and CI logs leak tokens more often than you'd think), the blast radius of a scoped bot token is dramatically smaller.

### 2. Audit Trail Clarity

When every automated action is attributed to your personal account, your git log becomes a mess:

```bash
# ❌ Confusing: Which of these did I actually write?
$ git log --oneline
a1b2c3d Update dependencies (me)
d4e5f6g Deploy to production (me)
g7h8i9j Fix typo in README (me)
j0k1l2m Auto-format code (me)
m3n4o5p Bump version to 2.1.0 (me)
```

With a bot account:

```bash
# ✅ Clear: Humans vs. automation are immediately obvious
$ git log --oneline
a1b2c3d Fix typo in README (me)
d4e5f6g Auto-format code (content-empire-bot)
g7h8i9j Deploy to production (content-empire-bot)
j0k1l2m Update dependencies (content-empire-bot)
m3n4o5p Bump version to 2.1.0 (content-empire-bot)
```

### 3. Token Rotation Without Downtime

When it's time to rotate credentials (and you should do this regularly), rotating a bot token affects only automations. Rotating your personal token affects everything you do — IDE, CLI, browser, and every automation you've hooked up.

### 4. Portability

If you bring on a collaborator, transfer the project, or create an organization, bot accounts just keep working. Personal accounts create awkward situations: "Hey, can you not change your password? It'll break our deployment."

## Setting It Up: A Practical Guide

### GitHub: Machine User + Fine-Grained Token

```bash
# 1. Create a new GitHub account for your project
#    (e.g., "myproject-bot@protonmail.com")

# 2. Generate a fine-grained personal access token
#    Settings → Developer settings → Fine-grained tokens

# 3. Scope it tightly:
#    - Repository access: Only select repositories
#    - Permissions:
#      - Contents: Read and write (for pushing code)
#      - Pull requests: Read and write (for PR automation)
#      - Actions: Read (for checking CI status)
#      - Metadata: Read (required)
```

For GitHub Actions specifically, prefer the built-in `GITHUB_TOKEN` or deploy keys:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    steps:
      # Uses the automatic GITHUB_TOKEN — no personal credentials needed
      - uses: actions/checkout@v4
      - run: npm run build
      - uses: actions/deploy-pages@v4
```

### API Keys: Separate Project Keys

Most services let you create multiple API keys. Create one per project:

```bash
# ❌ Don't: One key for everything
OPENAI_API_KEY=sk-personal-key-for-everything

# ✅ Do: Separate keys per project
# In your side project's .env:
OPENAI_API_KEY=sk-proj-myproject-scoped-key

# In your experiments:
OPENAI_API_KEY=sk-proj-experiments-sandbox
```

### Secrets Management

Even for side projects, don't hardcode secrets:

```bash
# Option 1: GitHub Secrets (free, built into Actions)
# Settings → Secrets → Actions → New repository secret

# Option 2: .env files (local development)
echo "API_KEY=sk-secret" >> .env
echo ".env" >> .gitignore

# Option 3: 1Password CLI (if you already use 1Password)
op read "op://Development/MyProject/API_KEY"
```

### Git Commit Identity

Configure your bot's git identity separately:

```bash
# In your CI/CD configuration:
git config user.name "MyProject Bot"
git config user.email "myproject-bot@users.noreply.github.com"

# Commits are now attributed to the bot, not you
git commit -m "chore: automated dependency update"
```

## The Migration Checklist

If you already have automations running under your personal account, here's how to migrate:

```markdown
## Non-Human Account Migration Checklist

### Inventory
- [ ] List all tokens/credentials used in CI/CD pipelines
- [ ] List all API keys in environment variables/secrets
- [ ] List all git commit identities configured in automation
- [ ] List all webhook URLs using personal tokens

### Create Bot Identity
- [ ] Create a dedicated email for the project bot
- [ ] Create GitHub/GitLab account for the bot
- [ ] Generate fine-grained tokens with minimal permissions
- [ ] Create project-specific API keys for external services

### Migrate
- [ ] Replace personal tokens in CI/CD secrets
- [ ] Update webhook URLs with new bot tokens
- [ ] Update git config in CI/CD to use bot identity
- [ ] Update deployment scripts with new credentials
- [ ] Test each pipeline after migration

### Verify
- [ ] Confirm all CI/CD pipelines pass
- [ ] Confirm deployments work with new credentials
- [ ] Confirm git history shows bot identity for new automated commits
- [ ] Revoke old personal tokens used in automation

### Document
- [ ] Document where each credential is used
- [ ] Document rotation schedule (at minimum: quarterly)
- [ ] Set calendar reminders for token rotation
```

## Cost: Exactly $0

Here's the best part — this costs nothing for side projects:

- **GitHub machine user:** Free (GitHub allows multiple accounts for bots)
- **Fine-grained tokens:** Free
- **GitHub Actions secrets:** Free
- **Project-specific API keys:** Free (most services allow multiple keys)
- **Your time:** ~30 minutes for initial setup

Compare that to the cost of a leaked personal token: hours of incident response, potential data exposure, and the existential dread of wondering what an attacker did with admin access to all your repositories.

## The Bottom Line

Using personal accounts for automation is the side project equivalent of technical debt — it works until the moment it doesn't, and then it costs you far more than doing it right would have.

Spend 30 minutes setting up a non-human account for your next project. Future you will be grateful.

---

*Content Empire helps developers build better infrastructure practices, even for side projects. Follow for practical guides with zero fluff.*
