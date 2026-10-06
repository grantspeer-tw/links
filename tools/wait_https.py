"""Waits for GitHub Pages to issue the HTTPS certificate for each repo's custom domain, then enforces HTTPS and fetches
https://<domain>/ to confirm. Usage: python tools/wait_https.py grantspeer-tw/links=go.thrillworks.site [...]
GitHub only requests a certificate when the custom domain is saved while its DNS already resolves, so if one stays at
"none" for long, remove and re-save the domain (gh api -X PUT repos/<o>/<r>/pages -F cname=null, then -f cname=<domain>)."""
import json, ssl, subprocess, sys, time, urllib.request

def gh(*a):
    r = subprocess.run(['gh', 'api', *a], capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout.strip(), r.stderr.strip()

todo = dict(a.split('=', 1) for a in sys.argv[1:])
start, last = time.time(), {}
while todo and time.time() - start < 3600:
    for repo, dom in list(todo.items()):
        rc, out, err = gh(f'repos/{repo}/pages')
        if rc:
            state = f'api error {err[:100]}'
        else:
            p = json.loads(out); cert = (p.get('https_certificate') or {}).get('state')
            state = f"cert={cert} enforced={p.get('https_enforced')}"
            if cert == 'approved':
                if not p.get('https_enforced'):
                    rc2, _, err2 = gh('-X', 'PUT', f'repos/{repo}/pages', '-F', 'https_enforced=true', '-f', f'cname={dom}')
                    print(f'{dom}: enforce https', 'ok' if rc2 == 0 else err2[:160], flush=True)
                try:
                    with urllib.request.urlopen(f'https://{dom}/', timeout=20, context=ssl.create_default_context()) as r:
                        print(f'{dom}: https -> {r.status}', flush=True)
                except Exception as e:
                    print(f'{dom}: https FAILED {type(e).__name__} {str(e)[:120]}', flush=True)
                del todo[repo]
                continue
        if last.get(repo) != state:
            print(f'{int(time.time() - start):>5}s {dom}: {state}', flush=True); last[repo] = state
    time.sleep(30)
for repo, dom in todo.items():
    print(f'TIMEOUT after 60 min: {dom} {last.get(repo)}', flush=True)
