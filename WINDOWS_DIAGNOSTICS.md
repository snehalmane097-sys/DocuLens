# Windows verification diagnostics — 28 October 2026

## Findings

- **Generated files:** Node successfully created a probe directory, wrote/deleted a file, and removed the probe directory under both `frontend/.next/types/app` and `backend`. The probes left no files. The inspected .next directories were normal directories, not read-only files or links. The ACL lists Authenticated Users Modify and Administrators/SYSTEM FullControl; there was no displayed deny entry. The old EPERM did not reproduce during the latest compile. Its original cause remains unconfirmed; no permission changes, source deletion, cache deletion, or dependency changes were justified.
- **Possible dev process/locks:** `.next/dev/lock` exists (last write displayed as 28 October 2026 10:33:47); this alone does not prove a live process or file lock. Get-Process, Get-NetTCPConnection, and netstat produced no matching visible process/listener output. CIM process inspection explicitly failed: "Access to a CIM resource was not available to the client." Active process ownership and file locks could not be conclusively inspected in this execution context. No processes were killed. No Handle/Process Explorer tooling was installed.
- **Localhost:** Node fetch GET failed with EACCES for both localhost and 127.0.0.1 and different paths. Python raw TCP to 127.0.0.1:3000 failed with WinError 10013. This occurs before an HTTP response, so changing HTTP methods or an application route would not fix the observed failure. Evidence points to socket access restrictions in the execution context; the available tools cannot distinguish host firewall policy from sandbox policy definitively. The configured environment restricts network access. Server health from this context remains unverified.
- **PyPI:** Node DNS lookup returned ENOTFOUND; Resolve-DnsName returned access denied. Python HTTPS to https://pypi.org/simple/fastapi/ failed with socket.gaierror 11001 / getaddrinfo failed before TLS/HTTP. Pip index reported "No matching distribution found for fastapi"; in this context that is not proof the package/version is unavailable. DNS/network access prevents reaching the index.
- **Proxy:** No matching proxy/PIP environment variables were reported. urllib.request.getproxies() returned an empty dictionary. Pip config debug found no global, user, or virtual-environment pip.ini files. The WinHTTP proxy query was unavailable ("The following command was not found: winhttp show proxy"), so host WinHTTP proxy state is unconfirmed.
- **Backend:** Existing venv runs Python 3.12.4 and pip 24.0. FastAPI, pytest, and Uvicorn are absent. Existing requirements were inspected unchanged: fastapi 0.115.6, uvicorn 0.34.0, python-dotenv 1.0.1; dev requirements include runtime requirements, pytest 8.3.4, httpx 0.28.1. No dependency installation was attempted because connectivity diagnostics failed. Backend tests cannot collect without pytest; live endpoints cannot start without FastAPI/Uvicorn.
- **Scope:** No application source, CSS, dependencies, lockfiles, firewall, proxy settings, or security controls were modified during this diagnostic pass.

## Commands and results

Commands below ran from C:\Doculens unless noted. PowerShell semicolon-separated inspections were grouped in tool calls; each result is described independently.

### Filesystem and process inspections

```powershell
Get-Content backend/requirements.txt
Get-Content backend/requirements-dev.txt
Get-Content frontend/package.json
Get-ChildItem -Filter AGENTS.md
Get-Process node -ErrorAction SilentlyContinue | Select-Object Id,Path
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object LocalAddress,State,OwningProcess
Get-Item frontend/.next,frontend/.next/types,frontend/.next/types/app | Select-Object FullName,Attributes
Get-Acl frontend/.next/types/app | Format-List Owner,AccessToString
Get-CimInstance Win32_Process -Filter "name='node.exe'" -ErrorAction Continue | Select-Object ProcessId,CommandLine
netstat -ano -p tcp | Select-String ':3000'
Get-Item frontend/.next/dev/lock -ErrorAction SilentlyContinue | Select-Object FullName,LastWriteTime
Get-Content frontend/.next/dev/lock -ErrorAction SilentlyContinue
Get-Content frontend/.next/dev/logs/next-development.log -Tail 8 -ErrorAction SilentlyContinue
Get-ChildItem frontend/.next/types/app -Force | ForEach-Object Name
Get-Content README.md -Tail 20
```

The type directory was temporarily absent when listed during the build's output regeneration. Historical development logs contained a hydration warning showing injected fdprocessedid attributes; it was not a new runtime check and is not evidence that the current app has a rendering fault. No application changes were made based on it.

Node filesystem probe executed with `node -e`:

```javascript
const fs = require('fs');
for (const base of ['C:/Doculens/frontend/.next/types/app', 'C:/Doculens/backend']) {
  const p = base + '/diagnostic-probe-' + process.pid;
  try {
    fs.mkdirSync(p);
    fs.writeFileSync(p + '/probe.txt', 'probe');
    fs.unlinkSync(p + '/probe.txt');
    fs.rmdirSync(p);
    console.log('File probe PASS:', base);
  } catch (e) { console.log('File probe FAIL:', base, e.code, e.syscall); }
}
```

Both probes passed. No lock was observed for newly created probe files; existing generated-file locks were not ruled out.

### Networking, proxy, Python and pip

```powershell
netsh winhttp show proxy
Get-ChildItem Env: | Where-Object Name -match '^(HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|PIP_INDEX_URL|PIP_EXTRA_INDEX_URL)$'
Resolve-DnsName pypi.org -ErrorAction Continue | Select-Object Name,IPAddress
& backend/.venv/Scripts/python.exe --version
& backend/.venv/Scripts/python.exe -m pip --version
& backend/.venv/Scripts/python.exe -m pip config debug
& backend/.venv/Scripts/python.exe -m pip index versions fastapi --retries 0 --timeout 5 --disable-pip-version-check
& backend/.venv/Scripts/python.exe -c "import socket,urllib.request; print('Proxy schemes:',list(urllib.request.getproxies())); print('Modules:'); import importlib.util; print({n:importlib.util.find_spec(n) is not None for n in ['fastapi','pytest','uvicorn']}); socket.create_connection(('127.0.0.1',3000),timeout=3)"
& backend/.venv/Scripts/python.exe -c "import socket; from urllib.request import urlopen; print('Direct HTTPS diagnostic'); urlopen('https://pypi.org/simple/fastapi/',timeout=5)"
Get-ChildItem Env: | Where-Object Name -match 'PROXY|PIP_'
```

Environment listings were filtered and values withheld when appropriate. No proxy credentials were exposed.

Node DNS and HTTP diagnostics executed in the same `node -e` invocation as the filesystem probe:

```javascript
const dns = require('dns');
dns.lookup('pypi.org', (e, a) => console.log('DNS pypi.org:', e?.code || a));
(async () => {
  for (const url of [
    'http://127.0.0.1:3000/api/health',
    'http://127.0.0.1:3000/upload',
    'http://localhost:3000/',
    'https://pypi.org/simple/fastapi/'
  ]) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(5000) });
      console.log('GET', url, r.status);
    } catch (e) { console.log('GET', url, e.cause?.code || e.name, e.cause?.syscall || ''); }
  }
})();
```

The port-3000 /api/health request was a path-independent frontend connection probe, not a backend endpoint test (the backend normally uses port 8000). All localhost probes failed before receiving HTTP status codes.

### Verification

From C:\Doculens\frontend:

```powershell
npm test
npm run typecheck
npm run lint
npm run build
```

- Tests: PASS, 8/8.
- TypeScript: PASS.
- Lint: PASS, no warnings.
- Production build: compiled, passed TypeScript and generated 7/7 static pages; final process status recorded below.

From C:\Doculens:

```powershell
& backend/.venv/Scripts/python.exe -m pytest -q
```

Backend tests: BLOCKED, "No module named pytest". Backend live health/document-list checks: NOT RUN because dependencies are missing. No runtime verification is claimed.

## Remaining actions outside this restricted execution context

1. Run the documented backend installation in a normal VS Code terminal with permitted PyPI access, then pytest and API smoke checks.
2. Test browser interactions and request both frontend and backend locally from that terminal.
3. If EPERM recurs, stop the dev server gracefully in its owning terminal before building. Inspect generated-folder locks/ACLs using approved Windows tools; preserve source and do not reset ACLs blindly.
4. Do not disable firewall/security controls or substitute package versions to hide connectivity failures.

Final production build result: PASS, exit code 0. Next.js lists /, /analytics, /documents, /documents/[id], /reconciliation, /upload, and /_not-found. The previous EPERM was not reproduced. This does not verify browser interactions or localhost connectivity.
