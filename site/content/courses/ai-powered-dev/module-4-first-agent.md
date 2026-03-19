---
title: "Module 4: Building Your First AI Agent"
date: 2025-07-23
weight: 4
author: "The Content Empire Team"
tags: ["AI", "course", "agents", "development"]
description: "Go beyond chat assistants and build an autonomous AI agent that can read codebases, find bugs, write fixes, and verify them — all without human intervention."
---

# Module 4: Building Your First AI Agent

## Learning Objectives

By the end of this module, you will:
- Understand the core agent loop and how it differs from chat assistants
- Implement tool use and function calling for code manipulation
- Build a complete bug-fixing agent from scratch
- Handle agent errors, loops, and safety guardrails
- Deploy your agent as a command-line tool

## 4.1 What Makes an Agent Different from a Chat?

The distinction is critical:

| | Chat Assistant | AI Agent |
|---|---|---|
| **Interaction** | Human asks, AI responds | AI plans and executes autonomously |
| **Tools** | None (text only) | File system, terminal, APIs, browser |
| **Iteration** | One-shot response | Loop until task is complete |
| **Verification** | Human checks output | Agent verifies its own work |
| **Context** | Conversation history | Conversation + environment state |

A chat assistant is like calling a consultant and asking for advice. An agent is like hiring a contractor who shows up, does the work, and verifies it's correct.

### The Agent Loop

Every AI agent follows the same fundamental loop:

```
┌─────────────────────────────────────────┐
│                                         │
│    ┌──────────┐                         │
│    │ OBSERVE  │ ← Read files, run       │
│    │          │   commands, check state  │
│    └────┬─────┘                         │
│         │                               │
│    ┌────▼─────┐                         │
│    │  THINK   │ ← Analyze observations, │
│    │          │   plan next action       │
│    └────┬─────┘                         │
│         │                               │
│    ┌────▼─────┐                         │
│    │   ACT    │ ← Modify files, run     │
│    │          │   tests, make changes   │
│    └────┬─────┘                         │
│         │                               │
│    ┌────▼─────┐                         │
│    │ EVALUATE │ ← Did the action work?  │
│    │          │   Is the task complete?  │
│    └────┬─────┘                         │
│         │                               │
│    No ──┤── Yes → DONE                  │
│         │                               │
└─────────┘ (loop back to OBSERVE)        │
                                          │
     Max iterations reached → STOP        │
──────────────────────────────────────────┘
```

## 4.2 The Tool System

Agents need tools to interact with the world. Let's define a clean tool interface:

```typescript
// tools/types.ts
interface Tool {
    name: string;
    description: string;
    parameters: Record<string, ParameterDef>;
    execute: (params: Record<string, any>) => Promise<ToolResult>;
}

interface ParameterDef {
    type: 'string' | 'number' | 'boolean';
    description: string;
    required: boolean;
}

interface ToolResult {
    success: boolean;
    output: string;
    error?: string;
}
```

### Essential Tools for a Code Agent

```typescript
// tools/read-file.ts
const readFileTool: Tool = {
    name: 'read_file',
    description: 'Read the contents of a file at the given path',
    parameters: {
        path: {
            type: 'string',
            description: 'Relative file path to read',
            required: true
        }
    },
    async execute({ path }) {
        try {
            const content = await fs.readFile(path, 'utf-8');
            return { success: true, output: content };
        } catch (error) {
            return {
                success: false,
                output: '',
                error: `Cannot read file: ${error.message}`
            };
        }
    }
};

// tools/write-file.ts
const writeFileTool: Tool = {
    name: 'write_file',
    description: 'Write content to a file, creating it if needed',
    parameters: {
        path: {
            type: 'string',
            description: 'File path to write to',
            required: true
        },
        content: {
            type: 'string',
            description: 'Content to write',
            required: true
        }
    },
    async execute({ path, content }) {
        try {
            await fs.mkdir(dirname(path), { recursive: true });
            await fs.writeFile(path, content, 'utf-8');
            return { success: true, output: `Written to ${path}` };
        } catch (error) {
            return {
                success: false,
                output: '',
                error: `Cannot write file: ${error.message}`
            };
        }
    }
};

// tools/run-command.ts
const runCommandTool: Tool = {
    name: 'run_command',
    description: 'Run a shell command and return its output',
    parameters: {
        command: {
            type: 'string',
            description: 'Shell command to execute',
            required: true
        }
    },
    async execute({ command }) {
        // Safety: restrict to safe commands
        const allowedPrefixes = [
            'npm test', 'npm run', 'npx',
            'node', 'cat', 'ls', 'find', 'grep',
            'git diff', 'git log', 'git status'
        ];

        const isAllowed = allowedPrefixes.some(
            prefix => command.startsWith(prefix)
        );

        if (!isAllowed) {
            return {
                success: false,
                output: '',
                error: `Command not allowed: ${command}`
            };
        }

        try {
            const output = execSync(command, {
                encoding: 'utf-8',
                timeout: 30_000,
                maxBuffer: 1024 * 1024
            });
            return { success: true, output };
        } catch (error) {
            return {
                success: false,
                output: error.stdout || '',
                error: error.stderr || error.message
            };
        }
    }
};

// tools/search-code.ts
const searchCodeTool: Tool = {
    name: 'search_code',
    description: 'Search for a pattern across all project files',
    parameters: {
        pattern: {
            type: 'string',
            description: 'Text or regex pattern to search for',
            required: true
        },
        filePattern: {
            type: 'string',
            description: 'File glob pattern (e.g., "*.ts")',
            required: false
        }
    },
    async execute({ pattern, filePattern }) {
        const glob = filePattern || '*';
        try {
            const output = execSync(
                `grep -rn "${pattern}" --include="${glob}" .`,
                { encoding: 'utf-8', maxBuffer: 1024 * 1024 }
            );
            return { success: true, output };
        } catch (error) {
            if (error.status === 1) {
                return { success: true, output: 'No matches found' };
            }
            return { success: false, output: '', error: error.message };
        }
    }
};
```

## 4.3 Building the Agent Core

Now let's build the agent that ties everything together:

```typescript
// agent/core.ts
import Anthropic from '@anthropic-ai/sdk';

class BugFixAgent {
    private client: Anthropic;
    private tools: Tool[];
    private maxIterations: number;
    private conversationHistory: Message[];

    constructor(tools: Tool[], maxIterations = 15) {
        this.client = new Anthropic();
        this.tools = tools;
        this.maxIterations = maxIterations;
        this.conversationHistory = [];
    }

    async run(task: string): Promise<AgentResult> {
        console.log(`🤖 Agent starting: ${task}\n`);

        // Initial system prompt
        const systemPrompt = this.buildSystemPrompt();

        // Seed the conversation with the task
        this.conversationHistory.push({
            role: 'user',
            content: task
        });

        for (let i = 0; i < this.maxIterations; i++) {
            console.log(`\n--- Iteration ${i + 1}/${this.maxIterations} ---`);

            // Ask the AI what to do next
            const response = await this.client.messages.create({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 4096,
                system: systemPrompt,
                tools: this.tools.map(t => ({
                    name: t.name,
                    description: t.description,
                    input_schema: {
                        type: 'object' as const,
                        properties: Object.fromEntries(
                            Object.entries(t.parameters).map(
                                ([k, v]) => [k, {
                                    type: v.type,
                                    description: v.description
                                }]
                            )
                        ),
                        required: Object.entries(t.parameters)
                            .filter(([, v]) => v.required)
                            .map(([k]) => k)
                    }
                })),
                messages: this.conversationHistory
            });

            // Check if the agent wants to use tools
            const toolUseBlocks = response.content.filter(
                b => b.type === 'tool_use'
            );
            const textBlocks = response.content.filter(
                b => b.type === 'text'
            );

            // Log any text output
            for (const block of textBlocks) {
                console.log(`💭 ${block.text}`);
            }

            // If no tool calls, the agent is done
            if (toolUseBlocks.length === 0) {
                const finalText = textBlocks
                    .map(b => b.text)
                    .join('\n');
                console.log('\n✅ Agent completed');
                return {
                    success: true,
                    summary: finalText,
                    iterations: i + 1
                };
            }

            // Execute each tool call
            this.conversationHistory.push({
                role: 'assistant',
                content: response.content
            });

            const toolResults = [];
            for (const toolUse of toolUseBlocks) {
                const tool = this.tools.find(
                    t => t.name === toolUse.name
                );
                if (!tool) {
                    toolResults.push({
                        type: 'tool_result' as const,
                        tool_use_id: toolUse.id,
                        content: `Error: Unknown tool ${toolUse.name}`
                    });
                    continue;
                }

                console.log(`🔧 ${toolUse.name}(${
                    JSON.stringify(toolUse.input).substring(0, 100)
                })`);

                const result = await tool.execute(toolUse.input);
                const outputPreview = result.output.substring(0, 200);
                console.log(`   → ${result.success ? '✅' : '❌'} ${
                    outputPreview
                }${result.output.length > 200 ? '...' : ''}`);

                toolResults.push({
                    type: 'tool_result' as const,
                    tool_use_id: toolUse.id,
                    content: result.success
                        ? result.output
                        : `Error: ${result.error}`
                });
            }

            this.conversationHistory.push({
                role: 'user',
                content: toolResults
            });
        }

        console.log('\n⚠️ Agent reached max iterations');
        return {
            success: false,
            summary: 'Reached maximum iterations without completing',
            iterations: this.maxIterations
        };
    }

    private buildSystemPrompt(): string {
        return `You are a senior software engineer AI agent.
Your job is to find and fix bugs in codebases.

## How you work:
1. OBSERVE: Read relevant files and understand the codebase
2. THINK: Analyze the problem and plan your fix
3. ACT: Make the necessary code changes
4. VERIFY: Run tests to confirm your fix works

## Rules:
- Always read the relevant files before making changes
- Make minimal, focused changes — don't refactor unrelated code
- Run tests after making changes to verify your fix
- If tests fail after your change, analyze why and fix it
- If you're stuck after 3 attempts, explain what you tried
- Never delete or overwrite test files without reading them first

## Safety:
- Only modify files in the project directory
- Never run destructive commands (rm -rf, drop database, etc.)
- If unsure about a change, explain your reasoning first`;
    }
}
```

## 4.4 Running the Agent

```typescript
// run-agent.ts
const tools = [
    readFileTool,
    writeFileTool,
    runCommandTool,
    searchCodeTool
];

const agent = new BugFixAgent(tools, 15);

// Example: Fix a failing test
const result = await agent.run(`
The test suite has a failing test. Here's the error:

$ npm test
FAIL src/utils/pagination.test.ts
  ✕ handles page beyond available data
    Expected: []
    Received: undefined

Please:
1. Read the test file to understand what's expected
2. Read the source file to find the bug
3. Fix the bug
4. Run the tests to verify the fix
`);

console.log('\n📊 Result:', result);
```

### Example Agent Execution Trace

```
🤖 Agent starting: Fix failing pagination test

--- Iteration 1/15 ---
💭 Let me start by reading the failing test to understand the expected behavior.
🔧 read_file({"path": "src/utils/pagination.test.ts"})
   → ✅ import { describe, it, expect } from 'vitest'...

--- Iteration 2/15 ---
💭 Now let me read the source file.
🔧 read_file({"path": "src/utils/pagination.ts"})
   → ✅ export function paginate<T>(items: T[], page: number...

--- Iteration 3/15 ---
💭 I found the bug. When the page is beyond available data,
   items.slice(start, end) returns an empty array [],
   but the function wraps it in an object where data could be
   undefined if totalPages is 0. The issue is that
   Math.ceil(0 / pageSize) returns 0, and the hasNext
   calculation is wrong for this edge case. Let me fix it.
🔧 write_file({"path": "src/utils/pagination.ts", "content": "..."})
   → ✅ Written to src/utils/pagination.ts

--- Iteration 4/15 ---
🔧 run_command({"command": "npm test"})
   → ✅ PASS src/utils/pagination.test.ts (12 tests passed)

💭 All tests pass now. The bug was in the edge case handling
   when the requested page exceeds available pages.

✅ Agent completed
```

## 4.5 Error Handling and Safety

### Preventing Infinite Loops

Agents can get stuck. Add detection:

```typescript
class LoopDetector {
    private actions: string[] = [];
    private maxRepeats = 3;

    recordAction(action: string): boolean {
        this.actions.push(action);

        // Check last N actions for repetition
        if (this.actions.length >= this.maxRepeats) {
            const recent = this.actions.slice(-this.maxRepeats);
            const allSame = recent.every(a => a === recent[0]);
            if (allSame) {
                console.warn('⚠️ Loop detected: same action repeated');
                return true; // is looping
            }
        }

        return false; // not looping
    }
}
```

### Sandboxing

Run the agent in a restricted environment:

```typescript
// Restrict file access to project directory only
function isPathSafe(filepath: string): boolean {
    const resolved = path.resolve(filepath);
    const projectRoot = path.resolve('.');
    return resolved.startsWith(projectRoot);
}

// Restrict command execution
const BLOCKED_COMMANDS = [
    'rm -rf', 'rm -r /',
    'sudo', 'chmod 777',
    'curl | sh', 'wget | sh',
    'DROP TABLE', 'DELETE FROM',
    'format', 'fdisk'
];

function isCommandSafe(command: string): boolean {
    return !BLOCKED_COMMANDS.some(blocked =>
        command.toLowerCase().includes(blocked.toLowerCase())
    );
}
```

### Cost Controls

```typescript
class CostTracker {
    private totalTokens = 0;
    private maxTokens: number;

    constructor(maxBudgetUSD: number) {
        // Approximate: $3 per 1M tokens for Claude Sonnet
        this.maxTokens = maxBudgetUSD * 333_333;
    }

    addUsage(inputTokens: number, outputTokens: number): boolean {
        this.totalTokens += inputTokens + outputTokens;
        if (this.totalTokens > this.maxTokens) {
            console.warn('💰 Budget exceeded!');
            return false; // over budget
        }
        return true; // within budget
    }
}
```

## 4.6 Hands-On Exercise: Build and Run Your Agent

### Exercise: The Bug Hunt Challenge

We've prepared a repository with 5 intentional bugs:

1. **Off-by-one error** in a loop
2. **Null reference** on optional field access
3. **Race condition** in an async function
4. **SQL injection** vulnerability
5. **Incorrect error handling** that swallows exceptions

Your task:
1. Clone the starter repo
2. Set up the agent with the tools from this module
3. Run the agent against each bug, one at a time
4. Evaluate: Which bugs did it fix correctly? Which did it struggle with?
5. Improve your system prompt based on the results

### Evaluation Criteria

For each bug fix, score:
- **Detection** (0-2): Did the agent find the bug?
- **Fix Quality** (0-3): Was the fix correct, minimal, and idiomatic?
- **Verification** (0-2): Did the agent verify its fix with tests?
- **Efficiency** (0-3): How many iterations did it take?

A score of 8+ out of 10 per bug = your agent is production-ready for simple fixes.

## Key Takeaways

1. Agents differ from chat assistants in their ability to take actions and verify results autonomously
2. The agent loop (Observe → Think → Act → Evaluate) is the universal pattern for all AI agents
3. Tool design is critical — well-defined, focused tools produce better agent behavior
4. Safety guardrails (iteration limits, sandboxing, cost controls) are non-negotiable
5. Start with simple, well-scoped tasks before attempting complex multi-file changes

## Next Module

In **Module 5: Multi-Agent Orchestration**, we'll take everything we've built and scale it up — running multiple specialized agents that collaborate on larger tasks.

---

*Continue to [Module 5: Multi-Agent Orchestration →](../module-5-multi-agent/)*
