# EDA GUI Async Bridge — Reference Implementations

## ADS (Keysight Advanced Design System)

### Startup hook: `<workspace>/scripting/boot.ael`

ADS automatically executes `boot.ael` (AEL language) after the workspace fully loads in the GUI.

**Complete `boot.ael` with error capture:**

```ael
// ADS workspace AEL automation hook
// Install once per workspace via setup tool

decl _scripting_dir  = strcat(get_workspace_path(), "/scripting");
decl _task_file      = strcat(_scripting_dir, "/task.ael");
decl _result_path    = strcat(_scripting_dir, "/result.txt");
decl _error_occurred = FALSE;

// Error handler — fires on any AEL runtime error
// on_error() docs: code=error code, class_name=error type,
//   op_code=operation, filename=source file, line=line no., col=column no.
// geterror() docs: returns human-readable last error string
defun _task_error_cb(code, class_name, op_code, filename, line, col) {
    _error_occurred = TRUE;
    decl _ef = fopen(_result_path, "w");
    fputs(_ef, "status=error\n");
    fputs(_ef, strcat("error_code=",    code,          "\n"));
    fputs(_ef, strcat("error_class=",   class_name,    "\n"));
    fputs(_ef, strcat("error_file=",    filename,      "\n"));
    fputs(_ef, strcat("error_line=",    line,          "\n"));
    fputs(_ef, strcat("error_col=",     col,           "\n"));
    fputs(_ef, strcat("error_message=", geterror(),    "\n"));
    fclose(_ef);
    return NULL;   // NULL = suppress ADS error dialog
}

if (file_exists(_task_file)) {
    decl _f0 = fopen(_result_path, "w");
    fputs(_f0, "status=running\n");   // written before load; survives process crash
    fclose(_f0);

    on_error(&_task_error_cb);
    load(_task_file);                 // task.ael contains only task logic
    on_error(NULL);

    if (!_error_occurred) {
        decl _f1 = fopen(_result_path, "w");
        fputs(_f1, "status=ok\n");
        fclose(_f1);
    }
    delete_file(_task_file);          // prevent re-execution on next workspace open
}
```

**AEL error capture functions (official docs):**

| Function | Signature | Source |
|---|---|---|
| `on_error()` | `on_error(func_address)` — registers callback; callback args: `(code, class, op, file, line, col)`; return NULL to suppress dialog | `processed/madcap_txt/priority1/ael/on_error().md` |
| `geterror()` | `geterror()` — returns string of last error message | `processed/madcap_txt/priority1/ael/geterror().md` |
| `check_syntax()` | `check_syntax(string)` — returns True/False for syntax validity (syntax only, not identifier resolution) | `processed/madcap_txt/priority1/ael/check_syntax().md` |

**AEL pre-compiler (syntax check before GUI launch):**
```powershell
aelcomp task.ael task.atf   # aelcomp is in $HPEESOF_DIR/bin/
```

**ADS project reference:** `notes/ads-gui-ael-mcp-architecture.md` in the ADS2025_help repo.

---

## Cadence Virtuoso

### Startup hook: `.cdsinit` or `init.il`

Virtuoso (IC design suite) executes `.cdsinit` from the project directory on startup.  
Library-level init uses `cdsenv` and `<lib>/boot.il`.

**Equivalent `.cdsinit` pattern (Cadence SKILL language):**

```il
; Cadence SKILL automation hook  (SKILL = Cadence's scripting language, NOT a Cursor skill file)
; Place in project directory: <project>/.cdsinit

let((taskFile resultPath errorOccurred)
    taskFile   = strcat(getShellEnvVar("PWD") "/automation/task.il")
    resultPath = strcat(getShellEnvVar("PWD") "/automation/result.txt")
    errorOccurred = nil

    when(isFile(taskFile)
        ; Write running state
        let((port)
            port = outfile(resultPath "w")
            fprintf(port "status=running\n")
            close(port)
        )

        ; errset() = Cadence SKILL's error capture mechanism (analogous to AEL on_error())
        ; errget() = retrieves last error message string (analogous to AEL geterror())
        errset(
            load(taskFile)
        )
        when(errget()
            errorOccurred = t
            let((port msg)
                msg  = errget()
                port = outfile(resultPath "w")
                fprintf(port "status=error\n")
                fprintf(port "error_message=%s\n" msg)
                close(port)
            )
        )
        unless(errorOccurred
            let((port)
                port = outfile(resultPath "w")
                fprintf(port "status=ok\n")
                close(port)
            )
        )
        deleteFile(taskFile)
    )
)
```

**SKILL error capture functions:**

| ADS AEL | Cadence SKILL | Notes |
|---|---|---|
| `on_error(func)` | `errset(expr)` | SKILL wraps the expression rather than registering a persistent callback |
| `geterror()` | `errget()` | Returns last error string |
| `load(file)` | `load(file)` | Same concept |
| `fopen`/`fputs`/`fclose` | `outfile`/`fprintf`/`close` | File I/O equivalents |

**Virtuoso GUI launch:**
```bash
virtuoso -restore <project_dir>/layout.sdb &
# or
virtuoso -noxshm -log virtuoso.log <project_dir> &
```

---

## EDA Tool Startup Hook Survey

| EDA Tool | Startup Hook File | Location | Script Language |
|---|---|---|---|
| Keysight ADS | `boot.ael` | `<workspace>/scripting/` | AEL (proprietary) |
| Cadence Virtuoso | `.cdsinit` | Project dir or `~/` | Cadence SKILL (proprietary) |
| Cadence Innovus | `innovus.tcl` startup scripts | Project dir | Tcl |
| Synopsys DC | `synopsys_dc.setup` | `~/` or project dir | Tcl |
| Synopsys StarRC | RC startup files | Project dir | Tcl |
| Mentor Calibre | `calibre.rcx` | `~/` | Tcl/SVRF |
| ANSYS HFSS | IronPython scripting | Project | IronPython |
| ANSYS Mechanical | `startup.py` | User scripts dir | Python |

> **Finding the hook**: If the tool is not listed, search its documentation for "init script", "startup file", "auto-load", or "workspace boot". Many tools based on Tcl follow the `<toolname>.setup` convention in `~/`.

---

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Hook fires before workspace is ready | GUI-only API calls fail silently | Use workspace-open hook (not app-startup hook); verify with a simple test call first |
| Overwriting existing hook | Other automation breaks | Always append or backup; never replace silently |
| Task file not deleted | Task re-executes on next workspace open | Delete task file inside the hook after execution |
| No `running` state written | Cannot distinguish "timeout" from "ADS crash" | Always write `running` before `load()` |
| Error handler returns non-NULL | ADS shows error dialog, blocking automation | Return `NULL` to suppress dialog |
| Polling too short | Result file appears truncated | Use atomic write (write to `.tmp`, then rename) or add a brief delay before reading |
