---
name: eda-gui-async-bridge
description: Design and implement async command-line ↔ GUI bidirectional communication for industrial EDA software (Keysight ADS, Cadence Virtuoso, Synopsys, ANSYS, etc.) using file-based IPC with native startup hooks. Use when building MCP tools, automation scripts, or CI pipelines that need to drive an EDA GUI from the command line, when the user mentions boot.ael, .cdsinit, SKILL scripting, workspace automation, or GUI-only API access from a non-interactive context.
---

# EDA GUI Async Bridge Pattern

## The Core Idea

Most industrial EDA tools expose GUI-only APIs (schematic printing, simulation control, DRC, layout export) that are inaccessible from command-line scripts. The solution is **file-based async IPC with a native startup hook**:

```
CLI/MCP writes task file → launches EDA GUI → workspace startup hook detects task file
→ executes task in GUI context → writes result file → CLI polls for result
```

The key insight: every major EDA tool has a **native workspace startup script** that runs automatically inside the GUI process after the workspace loads. This is the entry point.

---

## Step 1: Find the Native Startup Hook

Before implementing for any tool, answer these 4 questions:

| Question | ADS example | Virtuoso example |
|---|---|---|
| What is the native startup hook file? | `boot.ael` | `.cdsinit` or `init.il` |
| Where does it live? | `<workspace>/scripting/` | Project dir or `~/` |
| Does the script language have file I/O? | Yes (`fopen`/`fputs`/`fclose`) | Yes (SKILL `outfile`/`fprintf`) |
| Does the language have error capture? | Yes (`on_error()` + `geterror()`) | Yes (`errset()` + `errget()`) |

If the tool has no documented startup hook, search for:
- "workspace init script", "project boot file", "auto-load ael/il/tcl"
- The tool's equivalent of "run on startup" in its scripting docs

---

## Step 2: Design the File Protocol

**Task file** (`task.<ext>`): the script to execute, written by the CLI side before launching the GUI.  
**Result file** (`result.txt`): written by the GUI side after execution; polled by the CLI side.

**Result file status values** (use this 4-state design):

| Status | Written by | Meaning |
|---|---|---|
| file absent (timeout) | — | GUI failed to start, or hook not installed |
| `status=running` | startup hook, before task load | GUI started; task crashed before error handler fired |
| `status=error` + error fields | error handler callback | Script runtime error; include line/col/message |
| `status=ok` | startup hook, after task completes | Success |

---

## Step 3: Implement the Startup Hook

The hook does 4 things: write `running` → register error handler → load task file → write `ok`.  
The error handler writes `error` + details on any runtime exception.

```
// Pseudocode — adapt syntax to the tool's scripting language
declare global: error_occurred = false, result_path

define error_handler(code, file, line, col, message):
    error_occurred = true
    write result_path: "status=error\nerror_file=...\nerror_line=...\nerror_message=..."
    return null   // suppress GUI error dialog

if task_file_exists:
    write result_path: "status=running"
    register_error_handler(error_handler)
    load(task_file)
    unregister_error_handler()
    if not error_occurred:
        write result_path: "status=ok"
    delete task_file   // prevent re-execution on next open
```

---

## Step 4: Generate the Task File from the CLI Side

The CLI/MCP side generates the task script dynamically. The task file contains **only task logic** — no result writing (the hook handles that).

```python
# Python (CLI/MCP side) — generate task script for any EDA tool
def generate_task_script(tool_lang: str, task_body: str) -> str:
    """task_body is the raw script in the tool's native language."""
    return task_body   # no boilerplate needed; hook handles result writing
```

---

## Step 5: Launch and Poll

```powershell
# Windows PowerShell example
$taskPath   = "$workspace\scripting\task.ael"
$resultPath = "$workspace\scripting\result.txt"

$taskBody | Set-Content $taskPath
Start-Process $adsExe -ArgumentList "`"$workspace`""

$deadline = (Get-Date).AddSeconds($timeoutSec)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $resultPath) { break }
    Start-Sleep -Seconds 2
}
$result = if (Test-Path $resultPath) { Get-Content $resultPath -Raw } else { "status=timeout" }
```

---

## Step 6: Syntax Pre-check (Optional but Recommended)

Before launching the GUI, pre-validate the task script using the tool's offline compiler/checker:

| Tool | Pre-check command |
|---|---|
| ADS AEL | `aelcomp task.ael task.atf` |
| Cadence SKILL | `skillint -check task.il` (if available) |
| Tcl-based tools | `tclsh -c "source task.tcl"` |

Run pre-check → fix syntax errors → then launch GUI. This avoids the 30–90 s GUI startup for simple syntax mistakes.

---

## MCP Tool Design Checklist

When wrapping this pattern as an MCP tool:

- [ ] `setup_<tool>_workspace_tool` — installs the startup hook (once per workspace); never silently overwrite existing hook; append or backup instead
- [ ] `run_<tool>_gui_task` — requires explicit `workspace_path`; documents that it is a **heavyweight async operation** (30–90 s); returns structured result with `status` + error fields
- [ ] `precompile_<tool>_script_tool` — syntax-only pre-check using offline compiler; clearly states it does NOT check runtime behavior
- [ ] `check_<tool>_runtime_tool` — verifies tool installation path and environment variables

---

## Naming Warning: Cadence "SKILL" vs Cursor "skill"

When working with Cadence Virtuoso, the tool's scripting language is called **SKILL** (Simulation Kernel Interface Language). This is a completely different meaning from a Cursor agent skill file. In documentation and code, always write:
- **"Cadence SKILL language"** or **"SKILL script"** (capitalized) for Virtuoso's scripting language
- **"Cursor skill"** or **"agent skill"** for this type of file

---

## Reference Implementation and Tool Comparison

See [reference.md](reference.md) for:
- Complete ADS `boot.ael` implementation with `on_error()` error capture
- Cadence Virtuoso `.cdsinit` equivalent mapping
- Known startup hook locations for common EDA tools
