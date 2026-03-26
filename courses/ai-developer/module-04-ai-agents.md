---
title: "Building Your First AI Agent"
module: 4
course: "AI-Powered Developer"
author: "Content Empire Team"
estimated_time: "120 minutes"
difficulty: "Intermediate"
prerequisites:
  - "Module 1: Setting Up Your AI Development Environment"
  - "Module 2: Prompt Engineering for Developers"
  - "Module 3: AI-Powered Code Review and Testing"
---

# Module 4: Building Your First AI Agent

Everyone is talking about AI agents. Most explanations are vague. This module is not vague. You will build an agent from scratch, understand exactly how it works, add memory to it, and end up with a code review agent that does real work.

By the end of this module you'll have:
- A working file organizer agent in Python (~150 lines)
- An agent with persistent memory using SQLite
- A code review agent that reads your git commits and posts structured feedback
- A clear mental model of when to use agents vs. simpler LLM calls

---

## Section 1: What Is an AI Agent (For Real)

Let's cut through the hype with a precise definition.

**An AI agent is an LLM that has access to tools and runs in a loop until it decides it's done.**

That's it. The components:

| Component | What it is | Example |
|-----------|-----------|---------|
| **LLM** | The reasoning engine | GPT-4o, Claude 3.5, Gemini |
| **Tools** | Functions the LLM can call | `read_file()`, `search_web()`, `run_sql()` |
| **Memory** | State that persists across steps | Conversation history, vector DB, SQLite |
| **Loop** | The execution cycle | Reason → Act → Observe → Reason again |

### Agents vs. Chatbots

A chatbot takes input and returns output. One round trip. Done.

An agent takes a goal and keeps working until it achieves it — calling tools, observing results, adjusting its approach, and calling more tools. It's the difference between asking someone a question and giving them a task.

```
Chatbot: "Write me a test for this function" → returns test → done

Agent: "Increase test coverage for the authentication module to 80%"
  → reads current coverage report
  → identifies uncovered functions
  → generates tests for function 1
  → runs tests, observes 2 failures
  → fixes the failing tests
  → generates tests for function 2
  → runs all tests, observes 80% coverage achieved
  → reports completion with summary
```

The agent orchestrates a multi-step process with feedback. The chatbot answers a question.

### The ReAct Loop

The most important architecture to understand is ReAct (Reasoning + Acting). It was introduced in a 2022 paper and is the foundation of most production agents today.

Each cycle:

1. **Reason:** "What do I need to do to make progress toward my goal?"
2. **Act:** Call a tool
3. **Observe:** Read the tool's output
4. **Repeat** until the goal is achieved or an exit condition is hit

In code, this looks like:

```python
while not done:
    thought = llm.think(goal, history, available_tools)
    
    if thought.is_final_answer:
        return thought.answer
    
    tool_result = execute_tool(thought.tool_name, thought.tool_args)
    history.append({"tool": thought.tool_name, "result": tool_result})
```

Simple. Powerful. The implementation in Section 2 will make this concrete.

### When to Use Agents vs. Simple LLM Calls

Agents are not always better. They're more complex, slower, and more expensive. Use them when:

**Use an agent when:**
- The task requires multiple steps with unknown branching (you don't know upfront what steps will be needed)
- Each step's output determines what to do next
- The task involves interacting with external systems (files, APIs, databases)
- The task is too long to fit in a single prompt

**Use a simple LLM call when:**
- The task is a single transformation: summarize this, translate this, classify this
- All information needed is available upfront
- You need sub-second latency
- The scope is bounded and predictable

Agents have overhead: multiple LLM calls, tool execution time, orchestration logic. A task that needs one good prompt does not need an agent.

⚠️ **Warning:** The biggest mistake developers make with agents is using them for tasks that don't need them. If your "agent" always calls the same three tools in the same order, it's not an agent — it's a pipeline. Build a pipeline.

---

## Section 2: Your First Agent — File Organizer

We're going to build a practical agent that organizes files in a directory. It reads what's there, categorizes files, and moves them into organized subdirectories. Real problem, real code, real agent.

### The Architecture

```
Goal: "Organize the files in ~/Downloads"
  ↓
Agent starts loop
  ↓
[Step 1] list_files(path="~/Downloads") 
  → returns: ["report_q4.pdf", "photo_vacation.jpg", "script.py", ...]
  ↓
[Step 2] For each file: categorize based on extension/name
  → documents: [report_q4.pdf, invoice_jan.pdf]
  → images: [photo_vacation.jpg, screenshot_2024.png]
  → code: [script.py, app.js]
  ↓
[Step 3] move_file() for each file to its category folder
  ↓
[Step 4] report what was done
  ↓
Done
```

### The Tools

Each tool is a Python function with a clear input/output contract:

```python
import os
import shutil
import json
from pathlib import Path
from typing import Any

def list_files(path: str) -> dict[str, Any]:
    """List all files in a directory (non-recursive)."""
    try:
        target = Path(path).expanduser()
        if not target.exists():
            return {"error": f"Path does not exist: {path}"}
        if not target.is_dir():
            return {"error": f"Path is not a directory: {path}"}
        
        files = []
        for item in target.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "extension": item.suffix.lower(),
                    "size_kb": round(item.stat().st_size / 1024, 1),
                    "path": str(item)
                })
        
        return {"files": files, "count": len(files), "directory": str(target)}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}

def read_file(path: str, max_chars: int = 500) -> dict[str, Any]:
    """Read the first max_chars of a file to help categorize it."""
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        return {
            "content": content[:max_chars],
            "truncated": len(content) > max_chars
        }
    except Exception as e:
        return {"error": str(e)}

def create_directory(path: str) -> dict[str, Any]:
    """Create a directory if it doesn't exist."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return {"created": path, "success": True}
    except Exception as e:
        return {"error": str(e)}

def move_file(source: str, destination: str) -> dict[str, Any]:
    """Move a file to a new location. Creates destination directory if needed."""
    try:
        src = Path(source)
        dst = Path(destination)
        
        if not src.exists():
            return {"error": f"Source file does not exist: {source}"}
        
        # Create destination directory if needed
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle name conflicts
        if dst.exists():
            stem = dst.stem
            suffix = dst.suffix
            counter = 1
            while dst.exists():
                dst = dst.parent / f"{stem}_{counter}{suffix}"
                counter += 1
        
        shutil.move(str(src), str(dst))
        return {"moved": {"from": source, "to": str(dst)}, "success": True}
    except Exception as e:
        return {"error": str(e)}
```

### The Agent Core

```python
import openai
import json
from typing import Any

# Tool registry — maps tool names to functions
TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "create_directory": create_directory,
    "move_file": move_file,
}

# Tool schemas for the LLM
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the beginning of a file to understand its content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "max_chars": {"type": "integer", "description": "Maximum characters to read (default 500)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move a file to a new location",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Current file path"},
                    "destination": {"type": "string", "description": "Target file path (including filename)"}
                },
                "required": ["source", "destination"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a file organization agent. Your job is to organize files 
in a directory into logical subdirectories.

Organization rules:
- Documents (pdf, doc, docx, txt, md): move to {base}/documents/
- Images (jpg, jpeg, png, gif, webp, svg): move to {base}/images/
- Code (py, js, ts, go, rs, java, cpp, c, sh): move to {base}/code/
- Data (csv, json, xml, yaml, sql): move to {base}/data/
- Archives (zip, tar, gz, rar): move to {base}/archives/
- Everything else: move to {base}/other/

Process:
1. List the files in the target directory
2. For each file, determine its category based on extension (read file content if extension is ambiguous)
3. Create the necessary subdirectories
4. Move each file to its category directory
5. Report a summary of what was moved

Do not move directories, only files. Skip files that are already in a category subdirectory.
"""

def run_agent(goal: str, max_steps: int = 50) -> str:
    """Run the file organizer agent until it completes or hits max_steps."""
    client = openai.OpenAI()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal}
    ]
    
    step = 0
    while step < max_steps:
        step += 1
        print(f"\n[Step {step}] Calling LLM...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        messages.append(message)
        
        # No tool calls = agent is done
        if not message.tool_calls:
            print(f"\n✅ Agent completed after {step} steps")
            return message.content
        
        # Execute each tool call
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            print(f"  → Calling {func_name}({func_args})")
            
            if func_name not in TOOLS:
                result = {"error": f"Unknown tool: {func_name}"}
            else:
                result = TOOLS[func_name](**func_args)
            
            print(f"  ← Result: {json.dumps(result)[:200]}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
    
    return f"Agent stopped after {max_steps} steps without completing."

# Run it
if __name__ == "__main__":
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "~/Downloads"
    result = run_agent(f"Organize the files in {target_dir}")
    print("\n" + "="*50)
    print("AGENT REPORT:")
    print(result)
```

### Testing and Debugging Your Agent

Before pointing this at real files, test it against a sandbox:

```bash
# Create test directory
mkdir -p /tmp/test-organizer
touch /tmp/test-organizer/report.pdf
touch /tmp/test-organizer/photo.jpg
touch /tmp/test-organizer/script.py
touch /tmp/test-organizer/data.csv

python agent.py /tmp/test-organizer
```

For debugging, add verbose logging to the tool calls:

```python
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
```

💡 **Pro Tip:** Always test agents on a copy of real data first. Even a well-behaved file-moving agent can cause chaos if it misidentifies a critical config file as "other."

⚠️ **Warning:** The `move_file` tool is destructive. Add a `dry_run=True` parameter when testing so you can see what *would* happen without actually moving anything. Implement dry run by returning the planned action without executing `shutil.move`.

---

## Section 3: Adding Memory to Your Agent

The file organizer above is stateless. Each time you run it, it starts fresh. For many tasks, that's fine. But some agents need to remember things across sessions.

### Why Stateless Agents Have Limits

Consider an agent that monitors a directory for new files and organizes them daily. Stateless problems:

- It doesn't know which files it's already processed
- It doesn't remember user preferences ("I told it last week to put screenshots in screenshots/, not images/")
- It can't learn from corrections
- It can't track what it's done for reporting

Memory fixes all of these.

### Short-Term Memory: Conversation History

You already have this — it's the `messages` list in the agent loop. The LLM sees the full conversation history on each call, which means it "remembers" everything that happened in the current session.

The limitation: context windows have limits. Long-running agents need to manage what stays in the conversation history.

```python
def trim_messages(messages: list, max_tokens: int = 8000) -> list:
    """Keep system message and most recent messages within token budget."""
    system_messages = [m for m in messages if m.get("role") == "system"]
    other_messages = [m for m in messages if m.get("role") != "system"]
    
    # Rough token estimate: 4 chars per token
    current_tokens = sum(len(str(m)) // 4 for m in other_messages)
    
    while current_tokens > max_tokens and len(other_messages) > 2:
        removed = other_messages.pop(0)  # Remove oldest non-system message
        current_tokens -= len(str(removed)) // 4
    
    return system_messages + other_messages
```

### Long-Term Memory: SQLite

For persistent memory across sessions, SQLite is the right tool for most agents. It's simple, embedded, and doesn't require infrastructure.

```python
import sqlite3
from datetime import datetime
import json
from pathlib import Path

class AgentMemory:
    def __init__(self, db_path: str = "~/.agent_memory.db"):
        self.db_path = Path(db_path).expanduser()
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_path)
                );
                
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
    
    def mark_processed(self, file_path: str, destination: str):
        """Record that a file has been processed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO processed_files (file_path, destination) VALUES (?, ?)",
                (file_path, destination)
            )
    
    def is_processed(self, file_path: str) -> bool:
        """Check if a file has already been processed."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT 1 FROM processed_files WHERE file_path = ?",
                (file_path,)
            ).fetchone()
            return result is not None
    
    def set_preference(self, key: str, value: str):
        """Store a user preference."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat())
            )
    
    def get_preference(self, key: str, default: str = None) -> str | None:
        """Retrieve a user preference."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT value FROM user_preferences WHERE key = ?",
                (key,)
            ).fetchone()
            return result[0] if result else default
    
    def log_action(self, action: str, details: dict = None):
        """Log an agent action for auditing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO action_log (action, details) VALUES (?, ?)",
                (action, json.dumps(details) if details else None)
            )
    
    def get_recent_actions(self, limit: int = 20) -> list[dict]:
        """Get recent agent actions for context."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT action, details, timestamp FROM action_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [{"action": r[0], "details": json.loads(r[1]) if r[1] else None, "timestamp": r[2]} for r in rows]
    
    def get_preferences_summary(self) -> str:
        """Return all preferences as a formatted string for context injection."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
            if not rows:
                return "No preferences stored."
            return "\n".join(f"- {k}: {v}" for k, v in rows)
```

### Injecting Memory Into the Agent

Now wire the memory into the agent:

```python
def run_agent_with_memory(goal: str, memory: AgentMemory, max_steps: int = 50) -> str:
    client = openai.OpenAI()
    
    # Build context from memory
    recent_actions = memory.get_recent_actions(10)
    preferences = memory.get_preferences_summary()
    
    context = f"""
User preferences:
{preferences}

Recent actions (for context, avoid repeating them):
{json.dumps(recent_actions, indent=2) if recent_actions else "None"}
"""
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context from previous sessions:\n{context}\n\nTask: {goal}"}
    ]
    
    # ... rest of the agent loop, but log actions to memory
    # memory.log_action("move_file", {"from": source, "to": dest})
    # memory.mark_processed(file_path, destination)
```

### Persistent State Across Sessions

The agent now remembers:
- Which files it has already processed (no double-processing)
- User preferences set by conversation ("always put screenshots in ~/screenshots")
- A complete audit log of every action taken

To set a preference from a user interaction:

```python
# User says: "Put screenshots in ~/screenshots, not images"
# Add this to your move_file tool's logic:
memory.set_preference("screenshots_dir", "~/screenshots")
```

💡 **Pro Tip:** Keep memory schemas simple. Every column you add is a column you'll have to migrate later. Start with action logs and a key-value preferences table. Add structure only when you have a specific query you need to answer.

---

## Section 4: Tool Design Patterns

How you design tools determines whether your agent is reliable or chaotic. These patterns are from production experience.

### One Tool Should Do One Thing

Resist the temptation to make a "smart" tool that handles multiple cases.

❌ **Wrong:**
```python
def manage_files(operation: str, source: str, destination: str = None):
    """Handles list, read, move, delete, copy operations."""
    if operation == "list":
        return list_files(source)
    elif operation == "move":
        return move_file(source, destination)
    # ... etc
```

This forces the LLM to remember an extra `operation` parameter and gives it a bigger surface area for errors.

✅ **Right:** Separate tools for each operation. The LLM selects the right tool. That's what tools are for.

### Input/Output Schema Design

Keep inputs and outputs simple and explicit:

```python
# Bad: accepts arbitrary kwargs, output is unpredictable
def process(action: str, **kwargs) -> Any:
    ...

# Good: explicit types, predictable return shape
def search_files(directory: str, pattern: str, case_sensitive: bool = False) -> dict:
    """
    Returns: {"matches": [{"path": str, "name": str}], "count": int}
    Or on error: {"error": str}
    """
    ...
```

Always return a dict. Always include an `error` key when something goes wrong instead of raising exceptions. The LLM needs to read the output and decide what to do — a Python exception kills the agent, while an error in the return value lets the agent recover.

### Error Handling in Tools

```python
def move_file(source: str, destination: str) -> dict:
    try:
        # ... implementation
        return {"success": True, "moved_to": str(final_destination)}
    except PermissionError:
        return {
            "error": "Permission denied",
            "source": source,
            "suggestion": "Check file permissions or run with elevated privileges"
        }
    except FileNotFoundError:
        return {
            "error": "Source file not found",
            "source": source,
            "suggestion": "Verify the file path with list_files first"
        }
    except Exception as e:
        return {"error": f"Unexpected error: {type(e).__name__}: {str(e)}"}
```

The `suggestion` field is a technique worth using: it tells the LLM what to try next, improving recovery from errors.

### When to Combine Tools vs. Keep Them Separate

**Keep separate when:** The operations are independently useful, have different failure modes, or have different permission requirements.

**Consider combining when:** Two tools are always called together with no logic between them, and combining them would reduce round-trips significantly.

A `read_and_categorize_file` tool (reads + categorizes in one call) is reasonable if you're always categorizing right after reading and the categorization logic is deterministic.

### Security: Tools With Dangerous Permissions

Some tools have irreversible effects: deleting files, sending emails, executing shell commands. Apply these constraints:

1. **Add confirmation for destructive operations:**
```python
def delete_file(path: str, confirmed: bool = False) -> dict:
    if not confirmed:
        return {
            "requires_confirmation": True,
            "message": f"This will permanently delete {path}. Call again with confirmed=True to proceed.",
            "path": path
        }
    # ... actual deletion
```

2. **Scope dangerous tools tightly:**
```python
def run_shell_command(command: str, allowed_commands: list[str] = None) -> dict:
    """Only allows commands in the allowed_commands allowlist."""
    allowed = allowed_commands or ["git status", "git log", "git diff"]
    if not any(command.startswith(allowed_cmd) for allowed_cmd in allowed):
        return {"error": f"Command not allowed. Allowed commands: {allowed}"}
    # ... execute
```

3. **Log everything:**
```python
# In every destructive tool
memory.log_action("delete_file", {"path": path, "timestamp": datetime.now().isoformat()})
```

⚠️ **Warning:** Never give an agent a tool that can execute arbitrary shell commands without an explicit allowlist and logging. An LLM that can run `rm -rf /` is a very expensive accident.

---

## Section 5: Real Production Agent Example

Here's how the file organizer concepts scale up to a real production agent: the code review agent. This ties directly to Module 3's GitHub Actions workflow.

### The Code Review Agent

This agent reads open PRs, analyzes the code changes, and posts structured review comments.

```python
import os
import subprocess
import openai
from github import Github, GithubException

REVIEW_AGENT_SYSTEM = """You are an expert code reviewer. Your job is to:
1. Get the list of open pull requests
2. For each PR, retrieve the diff
3. Analyze the diff for security, performance, and correctness issues
4. Post a structured review comment

You must review every open PR. Work through them one at a time.
Format each review with: ## 🔍 AI Code Review, Critical Issues, Suggestions, What Looks Good.
"""

REVIEW_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_open_prs",
            "description": "List all open pull requests in the repository",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pr_diff",
            "description": "Get the diff for a specific pull request",
            "parameters": {
                "type": "object",
                "properties": {
                    "pr_number": {"type": "integer", "description": "The PR number"}
                },
                "required": ["pr_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "post_review_comment",
            "description": "Post a review comment on a pull request",
            "parameters": {
                "type": "object",
                "properties": {
                    "pr_number": {"type": "integer"},
                    "comment": {"type": "string", "description": "The review comment in markdown"}
                },
                "required": ["pr_number", "comment"]
            }
        }
    }
]

class CodeReviewAgent:
    def __init__(self, repo_name: str, github_token: str, openai_key: str):
        self.gh = Github(github_token)
        self.repo = self.gh.get_repo(repo_name)
        self.client = openai.OpenAI(api_key=openai_key)
        self._reviewed_this_session = set()  # Simple in-memory dedup
    
    def list_open_prs(self) -> dict:
        try:
            prs = self.repo.get_pulls(state="open")
            return {
                "prs": [
                    {"number": pr.number, "title": pr.title, "author": pr.user.login}
                    for pr in prs
                ]
            }
        except GithubException as e:
            return {"error": str(e)}
    
    def get_pr_diff(self, pr_number: int) -> dict:
        try:
            pr = self.repo.get_pull(pr_number)
            files = pr.get_files()
            
            diff_text = ""
            total_additions = 0
            
            for f in files:
                total_additions += f.additions
                if f.patch:  # Binary files have no patch
                    diff_text += f"\n--- {f.filename}\n{f.patch}\n"
            
            # Truncate large diffs to fit context window
            if len(diff_text) > 15000:
                diff_text = diff_text[:15000] + "\n... (diff truncated)"
            
            return {
                "pr_number": pr_number,
                "title": pr.title,
                "diff": diff_text,
                "files_changed": pr.changed_files,
                "additions": total_additions
            }
        except GithubException as e:
            return {"error": str(e)}
    
    def post_review_comment(self, pr_number: int, comment: str) -> dict:
        try:
            # Check if we already reviewed this PR this session
            if pr_number in self._reviewed_this_session:
                return {"skipped": True, "reason": "Already reviewed this PR this session"}
            
            pr = self.repo.get_pull(pr_number)
            
            # Delete previous bot reviews
            for existing in pr.get_issue_comments():
                if "AI Code Review" in existing.body:
                    try:
                        existing.delete()
                    except GithubException:
                        pass
            
            pr.create_issue_comment(comment)
            self._reviewed_this_session.add(pr_number)
            
            return {"success": True, "pr_number": pr_number}
        except GithubException as e:
            return {"error": str(e)}
    
    def run(self, max_steps: int = 100) -> str:
        tool_map = {
            "list_open_prs": self.list_open_prs,
            "get_pr_diff": self.get_pr_diff,
            "post_review_comment": self.post_review_comment,
        }
        
        messages = [
            {"role": "system", "content": REVIEW_AGENT_SYSTEM},
            {"role": "user", "content": f"Review all open PRs in {self.repo.full_name}."}
        ]
        
        for step in range(max_steps):
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=REVIEW_TOOLS,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            messages.append(message)
            
            if not message.tool_calls:
                return message.content  # Agent is done
            
            for call in message.tool_calls:
                args = json.loads(call.function.arguments)
                result = tool_map[call.function.name](**args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result)
                })
        
        return "Agent reached step limit"
```

### Rate Limiting and Quota Management

Production agents need rate limit handling:

```python
import time
from functools import wraps

def with_rate_limit(calls_per_minute: int = 20):
    """Decorator to rate-limit tool calls."""
    min_interval = 60.0 / calls_per_minute
    last_called = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            elapsed = now - last_called.get(func.__name__, 0)
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_called[func.__name__] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Apply to GitHub API calls
@with_rate_limit(calls_per_minute=30)
def get_pr_diff(self, pr_number: int) -> dict:
    ...
```

For OpenAI API quota, catch `RateLimitError` and back off:

```python
import openai
import time

def call_llm_with_backoff(client, **kwargs):
    for attempt in range(5):
        try:
            return client.chat.completions.create(**kwargs)
        except openai.RateLimitError:
            wait = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError("Failed after 5 attempts")
```

### Logging Agent Actions for Debugging

```python
import logging
import json

# Set up structured logging
logger = logging.getLogger("agent")
handler = logging.FileHandler("agent.log")
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def log_tool_call(tool_name: str, args: dict, result: dict, duration_ms: float):
    logger.info(json.dumps({
        "event": "tool_call",
        "tool": tool_name,
        "args": args,
        "success": "error" not in result,
        "duration_ms": round(duration_ms, 1)
    }))
```

Query your logs later:

```bash
# Find all failed tool calls
grep '"success": false' agent.log | python -m json.tool

# Find slowest tool calls
cat agent.log | python -c "
import sys, json
calls = [json.loads(l.split(' ', 3)[-1]) for l in sys.stdin if 'tool_call' in l]
slow = sorted(calls, key=lambda x: x.get('duration_ms', 0), reverse=True)[:5]
print(json.dumps(slow, indent=2))
"
```

---

## Section 6: Module Exercises

### Exercise 1: Extend the File Organizer with One New Tool

The current agent handles files but doesn't generate reports. Add a `write_summary` tool:

```python
def write_summary(path: str, content: str) -> dict:
    """Write a text summary to a file."""
    ...
```

Update the system prompt to instruct the agent to write a summary file after organizing. The summary should list: total files moved, breakdown by category, any files that couldn't be processed.

**Goal:** The agent should create an `organization_report.txt` file in the target directory after every run.

### Exercise 2: Add Memory to Store the Last 5 Actions

Using the `AgentMemory` class from Section 3:

1. Initialize memory at agent startup
2. After every `move_file` tool call, log the action
3. At the start of each session, load the last 5 actions and include them in the system prompt context
4. Modify `list_files` to skip files that have already been processed (check `memory.is_processed()`)

**Goal:** Run the agent twice on the same directory. The second run should report "0 files to organize — all already processed."

### Exercise 3: Build an Agent That Reviews Your Git Commits

Build a local version of the code review agent (no GitHub needed):

```python
def get_recent_commits(count: int = 5) -> dict:
    """Get the last N git commits as diffs."""
    result = subprocess.run(
        ["git", "log", f"-{count}", "--format=%H %s", "--no-pager"],
        capture_output=True, text=True
    )
    # Parse and return commit hashes + messages
    ...

def get_commit_diff(commit_hash: str) -> dict:
    """Get the diff for a specific commit."""
    result = subprocess.run(
        ["git", "show", commit_hash, "--no-pager"],
        capture_output=True, text=True
    )
    ...
```

**Goal:** Run `python review_agent.py` in any git repository and get an AI review of your last 5 commits, written to `commit-review.md`.

---

### 🚀 Module Project: Build a "Daily Standup" Agent

Build an agent that generates your daily standup from your git activity.

**What it should do:**
1. List all commits from the last 24 hours across all branches: `git log --all --since="24 hours ago"`
2. Read each commit's diff to understand what changed
3. Generate a standup in this format:
   - **Yesterday:** What I worked on (inferred from commits)
   - **Today:** What I'm working on (inferred from in-progress branches)
   - **Blockers:** Any TODO/FIXME comments added in recent commits

**Tools needed:**
- `get_recent_commits(hours: int)`
- `get_commit_diff(hash: str)`
- `search_for_pattern(pattern: str, since_commit: str)` — grep for TODOs
- `write_standup(content: str)` — saves to `standup.md`

This is a complete, useful agent you'll actually use every day. When you have it working, try running it as a cron job.

---

### ✅ Module 4 Checklist

- [ ] File organizer agent runs successfully on a test directory
- [ ] Agent correctly categorizes files by type
- [ ] Memory is persisted between runs (SQLite)
- [ ] Already-processed files are skipped on re-run
- [ ] At least one new tool added to the file organizer
- [ ] Commit review agent generates a review of last 5 commits
- [ ] Standup agent project is started (or completed!)

---

## Key Takeaways

1. **An agent is LLM + tools + loop** — nothing more. The complexity comes from tool design and memory management, not from the loop itself.
2. **ReAct is the foundation** — Reason, Act, Observe. Every production agent you encounter is a variation of this pattern.
3. **Tool design determines reliability** — one tool, one purpose; explicit schemas; error handling that lets the agent recover.
4. **Memory enables real utility** — stateless agents are demos; stateful agents are products.
5. **Start simple, add complexity when you need it** — a 150-line file organizer is a real agent. You don't need a framework.
6. **Rate limiting and logging are not optional** — every production agent needs them from day one.

---

*Module 5: Deploying AI Features to Production →*
