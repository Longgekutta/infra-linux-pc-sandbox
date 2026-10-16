# tls-daemon — Native TLS Impersonation Daemon (bogdanfinn/tls-client)

Chrome_133-profile TLS daemon. NDJSON over stdio:
- request:  `{"id":"1","method":"GET","url":"https://...","headers":{...}}`
- response: `{"id":"1","status":200,"headers":{...},"body_b64":"...","proto":"HTTP/2.0"}`

## Build (Go >= 1.24)

```bash
go mod tidy && go build -o tls-daemon-bin .
```

If `proxy.golang.org` is unreachable (common in CN networks), use GOPROXY=direct
with git rewrites for golang.org/x/* mirrors, or vendor the deps.

## Wire with the Python bridge

`core/tls_rewrite.py` auto-detects `tls-daemon-bin` via PATH; or pass the
explicit path: `TLSRewriteDriver(cdp_driver, daemon_path="tls_daemon/tls-daemon-bin")`.
