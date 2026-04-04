## Content Empire — Agent Instructions

### First-Time Machine Setup
1. Check if this machine is already set up for the Content Empire brand
2. Read STATUS.md for full project context before doing any work

### Key Files to Read
- STATUS.md — Full project status, what's built, what's pending
- BRAND-PLAN.md — Revenue strategy, distribution channels, content calendar

### Core Rules
- NEVER mention "Tamir Dresher" — this brand is independent
- All content in English AND Hebrew
- Read STATUS.md before doing any work
- Check GitHub issues for tracked tasks

### Session History
- See techai-explained repo SESSION-LOG-2026-03-19-20.md for the full March 19-20 launch session log
- This repo handles: articles, AI dev course, written content distribution
- Gumroad products: AI Dev Course ($19.99, ID: jnmqpd), K8s Course ($14.99, ID: nnefv)
- Email: contentempire@sharebot.net (stored as BRAND_EMAIL secret)


## GitHub Organization

This repo is forked into **github.com/content-empire-pub/content-empire** — the brand's independent org.

**Remotes:**
- `origin` → tdsquadAI/content-empire (primary)
- `org` → content-empire-pub/content-empire (org, primary going forward)

**Push to BOTH remotes:** `git push origin main && git push org main`

**GitHub Actions Secrets (on org repo):**
- `BRAND_EMAIL` — contentempire@sharebot.net
- `BRAND_NAME` — Content Empire
- `GUMROAD_STORE_URL` — Gumroad storefront
- `GUMROAD_AI_COURSE_ID` — AI course product ID

**Pages URL:** content-empire-pub.github.io/content-empire

**⚠️ NEVER reference personal identities in any public-facing content. Use the brand name only.**

## Credential Access (Cross-Machine)

**⚠️ IMPORTANT: At session start, ALWAYS run this to load brand config:**
```
gh variable list --repo content-empire-pub/content-empire --json name,value
```

All config AND passwords are stored as **GitHub Variables** (fully readable).

**Read a single value:**
```
gh variable get BRAND_EMAIL --repo content-empire-pub/content-empire
```

**In GitHub Actions workflows:**
- Variables: `${{ vars.BRAND_NAME }}`
- Secrets: `${{ secrets.MAIL_TM_PASSWORD }}` (also available as variables)

**To add/update a value:**
```
gh variable set NEW_KEY --repo content-empire-pub/content-empire --body "value"
```

**Never commit credentials to the repo.** Always use GitHub Variables.

