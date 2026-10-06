"""Short links on GitHub Pages: https://go.thrillworks.site/<name> redirects to any URL, Apps Script web apps included.

  python golink.py add <name> --clasp-dir <apps script project dir>   # resolves the latest versioned web app deployment
  python golink.py add <name> --url https://...                       # any HTTPS destination
  python golink.py add <name> --clasp-dir <dir> --deployment <id>     # pin a specific deployment
  python golink.py remove <name>
  python golink.py list
  python golink.py build                                              # regenerate the pages from links.json only

links.json is the source of truth. Each link becomes <name>/index.html, a page that forwards immediately (JavaScript,
keeping any ?query, with a meta-refresh fallback), and 404.html forwards case and trailing-slash variants. add/remove
commit and push, and GitHub Pages publishes within a minute. Pass --no-push to stop after the commit.

Apps Script note: `clasp update-deployment <id>` keeps a deployment's URL, so a link only needs re-running `add` when a
new deployment is created. Resolving needs clasp logged in as an account that can see the project.
"""
import argparse, datetime, html, json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
LINKS = ROOT / 'links.json'
DOMAIN = (ROOT / 'CNAME').read_text(encoding='utf-8').strip() if (ROOT / 'CNAME').exists() else 'go.example.com'
NAME = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}$')
RESERVED = {'404', 'index', 'assets', 'cname'}


def load():
    return json.loads(LINKS.read_text(encoding='utf-8')) if LINKS.exists() else {}


def save(links):
    LINKS.write_text(json.dumps(dict(sorted(links.items())), indent=2) + '\n', encoding='utf-8', newline='\n')


def run(cmd, cwd=ROOT, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', shell=(sys.platform == 'win32'))
    if check and r.returncode:
        sys.exit(f'command failed ({r.returncode}): {" ".join(cmd)}\n{r.stdout}{r.stderr}')
    return r


def apps_script_url(clasp_dir, deployment=None):
    """The /exec URL of the newest versioned web app deployment (or the one named) of an Apps Script project."""
    d = pathlib.Path(clasp_dir)
    if not (d / '.clasp.json').exists():
        sys.exit(f'{d} has no .clasp.json; point --clasp-dir at the Apps Script project folder')
    out = run(['clasp', 'list-deployments'], cwd=d).stdout
    found = [(m.group(1), m.group(2)) for m in re.finditer(r'^- (\S+) @(\d+|HEAD)\b', out, re.M)]
    if deployment:
        if deployment not in [i for i, _ in found]:
            sys.exit(f'deployment {deployment} not found; clasp listed: {found}')
        dep = deployment
    else:
        versioned = [(int(v), i) for i, v in found if v != 'HEAD']
        if not versioned:
            sys.exit(f'no versioned deployment (only @HEAD, which is the editor test URL). Run clasp create-deployment first.\n{out}')
        dep = max(versioned)[1]
    return f'https://script.google.com/macros/s/{dep}/exec'


def page(url, title):
    t, u = html.escape(title), html.escape(url, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{t}</title>
<meta name="robots" content="noindex">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>location.replace({json.dumps(url)} + location.search);</script>
<meta http-equiv="refresh" content="1; url={u}">
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;font:16px system-ui,sans-serif;background:#fafaf7;color:#333}}</style>
</head>
<body><p>Redirecting to <a href="{u}">{t}</a></p></body>
</html>
"""


def build(links):
    for old in ROOT.iterdir():  # remove pages whose link was removed
        if old.is_dir() and (old / 'index.html').exists() and old.name not in links and NAME.match(old.name):
            shutil.rmtree(old)
    for name, l in links.items():
        (ROOT / name).mkdir(exist_ok=True)
        (ROOT / name / 'index.html').write_text(page(l['url'], l.get('title') or name), encoding='utf-8', newline='\n')
    table = json.dumps({k: v['url'] for k, v in links.items()})
    (ROOT / '404.html').write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{DOMAIN}</title><meta name="robots" content="noindex">
<script>
  // Forwards /Name, /name/ and /name/anything to the link's destination; unknown names stay on this page.
  var L = {table}, k = location.pathname.replace(/^\\/+/, '').split('/')[0].toLowerCase();
  if (L[k]) location.replace(L[k] + location.search);
</script></head>
<body style="font:16px system-ui,sans-serif;padding:40px">No short link here.</body></html>
""", encoding='utf-8', newline='\n')
    (ROOT / 'index.html').write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{DOMAIN}</title><meta name="robots" content="noindex"></head>
<body style="font:16px system-ui,sans-serif;padding:40px">{DOMAIN}</body></html>
""", encoding='utf-8', newline='\n')
    (ROOT / '.nojekyll').touch()


def publish(message, push):
    run(['git', 'add', '-A'])
    if not run(['git', 'status', '--porcelain']).stdout.strip():
        print('nothing changed'); return
    run(['git', 'commit', '-q', '-m', message])
    if push:
        run(['git', 'push', '-q'])
        print('pushed; GitHub Pages publishes within about a minute')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add'); a.add_argument('name'); g = a.add_mutually_exclusive_group(required=True)
    g.add_argument('--url'); g.add_argument('--clasp-dir'); a.add_argument('--deployment'); a.add_argument('--title'); a.add_argument('--no-push', action='store_true')
    r = sub.add_parser('remove'); r.add_argument('name'); r.add_argument('--no-push', action='store_true')
    sub.add_parser('list'); sub.add_parser('build')
    args = ap.parse_args()
    links = load()
    if args.cmd == 'list':
        for k, v in sorted(links.items()):
            print(f'https://{DOMAIN}/{k}  ->  {v["url"]}')
        return
    if args.cmd == 'build':
        build(links); print(f'built {len(links)} links'); return
    name = args.name.lower()
    if args.cmd == 'remove':
        if name not in links:
            sys.exit(f'no link named {name}')
        del links[name]; save(links); build(links); publish(f'Remove link {name}', not args.no_push)
        print(f'removed https://{DOMAIN}/{name}'); return
    if not NAME.match(name) or name in RESERVED:
        sys.exit(f'invalid name {name!r}: lowercase letters, digits and hyphens, not {sorted(RESERVED)}')
    url = args.url or apps_script_url(args.clasp_dir, args.deployment)
    if not url.startswith('https://'):
        sys.exit('destination must be an https:// URL')
    verb = 'Update' if name in links else 'Add'
    links[name] = {'url': url, 'title': args.title or links.get(name, {}).get('title') or name, 'updated': datetime.date.today().isoformat()}
    save(links); build(links); publish(f'{verb} link {name}', not args.no_push)
    print(f'https://{DOMAIN}/{name}  ->  {url}')


if __name__ == '__main__':
    main()
