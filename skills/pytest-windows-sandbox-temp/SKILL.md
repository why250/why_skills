---
name: pytest-windows-sandbox-temp
description: Guides pytest execution in controlled Windows sandboxes with temporary-directory ACL failures. Use when pytest reports WinError 5 under TEMP, tmp_path, TemporaryDirectory, pytest cleanup, or project-local temporary roots.
---

# Pytest Windows Sandbox Temporary Directories

Use this workflow for test-environment permission failures. Do not alter product code merely to avoid a temporary-directory ACL problem.

## Workflow

1. Use the project's interpreter, not the Python resolved from `PATH`:

   ```powershell
   .venv\Scripts\python.exe -m pytest <test-target>
   ```

2. Identify the failure before changing code. Treat these as environment symptoms:

   - `PermissionError: [WinError 5] Access is denied`
   - failure below a `Temp\pytest-*`, `tmp*`, `tmp_path`, or `TemporaryDirectory` path
   - pytest session cleanup failing after otherwise successful tests

3. For tests using pytest fixtures, first use a project-local base directory:

   ```powershell
   .venv\Scripts\python.exe -m pytest <test-target> --basetemp .\temp\pytest_<project>
   ```

4. If the controlled sandbox also denies access to that base directory or cleanup, rerun the same command outside the sandbox with the required approval. Keep the test target and options unchanged.

5. If a test directly calls `tempfile.TemporaryDirectory()`, `--basetemp` does not control it. Prefer the project's verify/build script when it provides a workspace-temp adapter. Do not rely on changing `TEMP`/`TMP` alone.

6. After the ACL issue is bypassed, treat assertion failures as product failures and diagnose them normally. Report orphaned inaccessible temp directories; remove them only with explicit authority.

## Test Authoring

- Prefer pytest's `tmp_path` fixture for new tests.
- Keep production code independent of sandbox-specific paths or adapters.
- Record the interpreter, command, pass/fail count, and whether execution required the sandbox workaround.
