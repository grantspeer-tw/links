# go.thrillworks.site

Short links served by GitHub Pages. `https://go.thrillworks.site/<name>` forwards to the destination recorded in
`links.json`, keeping any query string.

## Add a link

```bash
python golink.py add mokeke --clasp-dir ../tw-mokeke-experiment/gas   # an Apps Script web app
python golink.py add docs --url https://example.com/some/long/path      # any HTTPS URL
python golink.py list
python golink.py remove docs
```

For an Apps Script project, `--clasp-dir` reads the newest versioned web app deployment through clasp. Redeploying
with `clasp update-deployment <id>` keeps the same URL, so the link only needs updating after `clasp create-deployment`.

## How it works

- `links.json` is the source of truth; `golink.py` writes one `<name>/index.html` redirect page per link and a
  `404.html` that forwards case and trailing-slash variants, then commits and pushes.
- GitHub Pages serves the repository at the custom domain in `CNAME`.
- DNS: `go.thrillworks.site` is a CNAME to `grantspeer-tw.github.io` in the `thrillworks.site` Route53 zone.
- Before deleting this repository or disabling Pages, delete that DNS record first, so nobody else can claim the
  subdomain on GitHub.
