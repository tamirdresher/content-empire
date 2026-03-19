---
title: "Module 3: AI-Powered Code Review and Testing"
date: 2025-07-23
weight: 3
author: "The Content Empire Team"
tags: ["AI", "course", "code-review", "testing"]
description: "Build automated code review bots and AI-driven test generation pipelines that catch bugs before humans even look at the code."
---

# Module 3: AI-Powered Code Review and Testing

## Learning Objectives

By the end of this module, you will:
- Understand how AI can systematically review code changes
- Build an automated PR review bot using AI
- Generate comprehensive test suites with AI assistance
- Use AI for security vulnerability detection
- Know the limits of AI code review and when human review is still essential

## 3.1 The Case for AI Code Review

Manual code review is one of the biggest bottlenecks in software development:

- Average PR review wait time: **4-6 hours** (many teams report 24+ hours)
- Average reviewer attention span per PR: **15-20 minutes**
- Bug detection rate in manual review: **25-40%** of introduced bugs
- Reviewer fatigue: Quality drops sharply after the third PR in a session

AI doesn't replace human reviewers — it acts as a **first-pass filter** that catches routine issues so human reviewers can focus on architecture, design, and business logic.

```
Traditional Review Pipeline:
Developer → PR → [Wait 4-24 hours] → Human Review → Fix → Re-review

AI-Augmented Review Pipeline:
Developer → PR → [Instant] AI Review → Fix Obvious Issues → Human Review
                                          ↓
                                    (30-50% of issues
                                     caught before human
                                     ever looks at the PR)
```

## 3.2 Building a PR Review Bot

Let's build a GitHub Actions workflow that reviews every PR automatically.

### Architecture

```
GitHub PR Event
      │
      ▼
GitHub Action Triggered
      │
      ▼
Collect Changed Files & Diffs
      │
      ▼
Send to AI with Review Prompt
      │
      ▼
Parse AI Response
      │
      ▼
Post Inline Comments on PR
```

### Step 1: The GitHub Action Workflow

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Get changed files
        id: changes
        run: |
          DIFF=$(git diff origin/${{ github.base_ref }}...HEAD --unified=5)
          echo "$DIFF" > /tmp/pr-diff.txt
          echo "diff_file=/tmp/pr-diff.txt" >> $GITHUB_OUTPUT

      - name: Run AI review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: node scripts/ai-review.js
```

### Step 2: The Review Script

```javascript
// scripts/ai-review.js
import Anthropic from '@anthropic-ai/sdk';
import { readFileSync } from 'fs';
import { execSync } from 'child_process';

const anthropic = new Anthropic();

async function reviewPR() {
    // Get the diff
    const diff = execSync(
        'git diff origin/main...HEAD --unified=5',
        { encoding: 'utf-8', maxBuffer: 1024 * 1024 }
    );

    if (!diff.trim()) {
        console.log('No changes to review');
        return;
    }

    // Build the review prompt
    const prompt = `You are an expert code reviewer. Review the following
code diff and identify ONLY genuinely important issues:

## What to flag:
- Bugs and logic errors
- Security vulnerabilities (SQL injection, XSS, auth bypass)
- Performance issues (O(n²) in hot paths, memory leaks, missing indexes)
- Race conditions and concurrency issues
- Missing error handling for critical paths
- Breaking API changes without documentation

## What NOT to flag:
- Style preferences (formatting, naming conventions)
- Minor optimizations that don't matter at current scale
- "Consider using X instead of Y" suggestions without clear benefit
- Anything that a linter would catch

## Output format:
For each issue, respond with:
FILE: <filename>
LINE: <line number in the new code>
SEVERITY: critical | warning | info
ISSUE: <brief description>
SUGGESTION: <how to fix it>
---

If there are no significant issues, respond with:
LGTM: No significant issues found.

## Diff to review:
\`\`\`
${diff.substring(0, 30000)}
\`\`\``;

    const response = await anthropic.messages.create({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4096,
        messages: [{ role: 'user', content: prompt }]
    });

    const reviewText = response.content[0].text;
    console.log('AI Review Result:');
    console.log(reviewText);

    // Post as PR comment
    await postReviewComment(reviewText);
}

async function postReviewComment(review) {
    const prNumber = process.env.PR_NUMBER;
    const token = process.env.GITHUB_TOKEN;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    const response = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/issues/${prNumber}/comments`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github+json',
            },
            body: JSON.stringify({
                body: `## 🤖 AI Code Review\n\n${review}\n\n---\n*Automated review by Content Empire AI Review Bot*`
            })
        }
    );

    if (response.ok) {
        console.log('Review comment posted successfully');
    } else {
        console.error('Failed to post comment:', await response.text());
    }
}

reviewPR().catch(console.error);
```

### Step 3: Making It Smarter with Project Context

The basic reviewer works, but providing project context dramatically improves quality:

```javascript
// Enhance the prompt with project-specific context
function buildContextualPrompt(diff) {
    const packageJson = safeReadFile('package.json');
    const tsConfig = safeReadFile('tsconfig.json');
    const architecture = safeReadFile('ARCHITECTURE.md');

    return `
## Project Context
- Tech Stack: ${extractTechStack(packageJson)}
- TypeScript Config: ${summarizeTsConfig(tsConfig)}
- Architecture: ${architecture?.substring(0, 2000) || 'Not available'}

## Team Conventions
- We use Result<T, E> types instead of throwing exceptions
- All database access goes through repository classes
- HTTP handlers must validate input with Zod schemas
- All public functions require JSDoc comments

## Review the following diff with this context in mind:
\`\`\`
${diff}
\`\`\`
`;
}
```

## 3.3 AI-Driven Test Generation

### The Test Generation Pipeline

AI is remarkably good at generating test cases — especially for:
- Edge cases humans forget
- Boundary value testing
- Error path coverage
- Integration test scaffolding

```typescript
// test-generator.ts
import Anthropic from '@anthropic-ai/sdk';
import * as fs from 'fs';

async function generateTests(sourceFile: string): Promise<string> {
    const source = fs.readFileSync(sourceFile, 'utf-8');
    const existingTests = findExistingTests(sourceFile);

    const anthropic = new Anthropic();
    const response = await anthropic.messages.create({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4096,
        messages: [{
            role: 'user',
            content: `Generate comprehensive unit tests for this code.

## Source Code:
\`\`\`typescript
${source}
\`\`\`

## Existing Tests (don't duplicate):
\`\`\`typescript
${existingTests || 'No existing tests'}
\`\`\`

## Requirements:
- Use Vitest syntax (describe, it, expect)
- Test happy paths, error paths, edge cases, and boundary values
- Mock external dependencies
- Each test should be independent
- Use descriptive test names that explain the expected behavior
- Include at least one test for:
  - Normal operation
  - Empty/null input
  - Boundary values
  - Error handling
  - Concurrent access (if applicable)

## Output:
Return ONLY the test file contents, no explanation.`
        }]
    });

    return response.content[0].text;
}
```

### Example: Generated Tests

Given this input function:

```typescript
// src/utils/pagination.ts
export function paginate<T>(
    items: T[],
    page: number,
    pageSize: number
): PaginationResult<T> {
    if (page < 1) throw new Error('Page must be >= 1');
    if (pageSize < 1) throw new Error('Page size must be >= 1');

    const totalItems = items.length;
    const totalPages = Math.ceil(totalItems / pageSize);
    const start = (page - 1) * pageSize;
    const end = start + pageSize;

    return {
        data: items.slice(start, end),
        pagination: {
            page,
            pageSize,
            totalItems,
            totalPages,
            hasNext: page < totalPages,
            hasPrevious: page > 1
        }
    };
}
```

AI generates:

```typescript
// src/utils/pagination.test.ts
import { describe, it, expect } from 'vitest';
import { paginate } from './pagination';

describe('paginate', () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

    describe('happy path', () => {
        it('returns the correct page of items', () => {
            const result = paginate(items, 1, 3);
            expect(result.data).toEqual([1, 2, 3]);
            expect(result.pagination.page).toBe(1);
            expect(result.pagination.totalPages).toBe(4);
        });

        it('returns the last page with remaining items', () => {
            const result = paginate(items, 4, 3);
            expect(result.data).toEqual([10]);
            expect(result.pagination.hasNext).toBe(false);
            expect(result.pagination.hasPrevious).toBe(true);
        });
    });

    describe('boundary values', () => {
        it('handles page size equal to total items', () => {
            const result = paginate(items, 1, 10);
            expect(result.data).toEqual(items);
            expect(result.pagination.totalPages).toBe(1);
            expect(result.pagination.hasNext).toBe(false);
            expect(result.pagination.hasPrevious).toBe(false);
        });

        it('handles page size of 1', () => {
            const result = paginate(items, 5, 1);
            expect(result.data).toEqual([5]);
            expect(result.pagination.totalPages).toBe(10);
        });

        it('handles page beyond available data', () => {
            const result = paginate(items, 100, 3);
            expect(result.data).toEqual([]);
            expect(result.pagination.hasNext).toBe(false);
        });
    });

    describe('empty input', () => {
        it('handles empty array', () => {
            const result = paginate([], 1, 10);
            expect(result.data).toEqual([]);
            expect(result.pagination.totalItems).toBe(0);
            expect(result.pagination.totalPages).toBe(0);
        });
    });

    describe('error handling', () => {
        it('throws for page < 1', () => {
            expect(() => paginate(items, 0, 10))
                .toThrow('Page must be >= 1');
        });

        it('throws for negative page', () => {
            expect(() => paginate(items, -1, 10))
                .toThrow('Page must be >= 1');
        });

        it('throws for pageSize < 1', () => {
            expect(() => paginate(items, 1, 0))
                .toThrow('Page size must be >= 1');
        });
    });

    describe('navigation flags', () => {
        it('hasNext is true when more pages exist', () => {
            const result = paginate(items, 1, 3);
            expect(result.pagination.hasNext).toBe(true);
        });

        it('hasPrevious is false on first page', () => {
            const result = paginate(items, 1, 3);
            expect(result.pagination.hasPrevious).toBe(false);
        });

        it('hasPrevious is true after first page', () => {
            const result = paginate(items, 2, 3);
            expect(result.pagination.hasPrevious).toBe(true);
        });
    });
});
```

## 3.4 Security Scanning with AI

AI can identify security patterns that traditional SAST tools miss:

```typescript
const securityPrompt = `
Review this code for security vulnerabilities.
Focus on OWASP Top 10 categories:

1. Injection (SQL, NoSQL, OS command, LDAP)
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities (XXE)
5. Broken Access Control
6. Security Misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging & Monitoring

For each finding:
- Describe the vulnerability
- Explain the attack scenario
- Provide the fix with code

Code to review:
\`\`\`
${code}
\`\`\`
`;
```

## 3.5 Hands-On Exercise: Build Your Review Pipeline

### Exercise: Set Up AI Review for Your Project

1. **Fork the starter repo** (provided in course materials)
2. **Add the AI review GitHub Action** from Section 3.2
3. **Create a PR with intentional bugs:**
   - SQL injection vulnerability
   - Missing null check
   - Off-by-one error in pagination
   - Hardcoded secret
4. **Run the AI review** and evaluate what it catches
5. **Improve the prompt** based on what it missed

### Bonus Exercise: Test Generation

1. Pick three functions in your codebase that lack tests
2. Use the test generator from Section 3.3
3. Run the generated tests — how many pass immediately?
4. Fix the ones that don't pass
5. Measure: What's the coverage increase?

## 3.6 Limits of AI Code Review

Be honest about what AI review can't do:

| AI Review Strengths | AI Review Weaknesses |
|---------------------|---------------------|
| Pattern matching (common bugs) | Architectural judgment |
| Security vulnerability detection | Business logic validation |
| Style consistency | Performance in specific context |
| Test coverage gaps | Team dynamics / PR etiquette |
| Documentation completeness | Cross-service implications |

**The golden rule:** AI review is a first pass. Human review is the final pass. Never merge a PR that only had AI review.

## Key Takeaways

1. AI code review catches 30-50% of issues before humans review — saving reviewer time and attention
2. The review prompt quality directly determines review quality — invest time in crafting your prompt
3. AI-generated tests are excellent for coverage but need human review for correctness of assertions
4. Security scanning with AI catches pattern-based vulnerabilities effectively
5. Always keep human reviewers in the loop — AI augments, it doesn't replace

## Next Module

In **Module 4: Building Your First AI Agent**, we'll go beyond passive review tools and build an agent that can actively find and fix bugs in your codebase.

---

*Continue to [Module 4: Building Your First AI Agent →](../module-4-first-agent/)*
