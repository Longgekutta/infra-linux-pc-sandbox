// tls-daemon: NDJSON-over-stdio TLS impersonation daemon built on
// bogdanfinn/tls-client. One JSON request per stdin line -> one JSON response
// per stdout line (base64 body), correlated by id. Interface matches the
// contract in infra-*-sandbox/core/tls_rewrite.py.
package main

import (
	"bufio"
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"

	http "github.com/bogdanfinn/fhttp"
	tls_client "github.com/bogdanfinn/tls-client"
	"github.com/bogdanfinn/tls-client/profiles"
)

type Job struct {
	ID      string            `json:"id"`
	Method  string            `json:"method"`
	URL     string            `json:"url"`
	Headers map[string]string `json:"headers"`
	Body    string            `json:"body,omitempty"`
}

type Result struct {
	ID      string            `json:"id"`
	Status  int               `json:"status"`
	Headers map[string]string `json:"headers"`
	BodyB64 string            `json:"body_b64"`
	Proto   string            `json:"proto,omitempty"`
	Error   string            `json:"error,omitempty"`
}

func main() {
	options := []tls_client.HttpClientOption{
		tls_client.WithTimeoutSeconds(30),
		tls_client.WithClientProfile(profiles.Chrome_133),
		tls_client.WithNotFollowRedirects(),
	}
	client, err := tls_client.NewHttpClient(tls_client.NewNoopLogger(), options...)
	if err != nil {
		fmt.Fprintln(os.Stderr, "client init:", err)
		os.Exit(1)
	}

	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 1024*1024), 32*1024*1024)
	writer := bufio.NewWriter(os.Stdout)
	defer writer.Flush()

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var job Job
		if err := json.Unmarshal(line, &job); err != nil {
			writeResult(writer, Result{ID: "", Error: fmt.Sprintf("bad job json: %v", err)})
			continue
		}

		var bodyReader *bytes.Reader
		if job.Body != "" {
			bodyReader = bytes.NewReader([]byte(job.Body))
		} else {
			bodyReader = bytes.NewReader(nil)
		}
		req, err := http.NewRequest(job.Method, job.URL, bodyReader)
		if err != nil {
			writeResult(writer, Result{ID: job.ID, Error: fmt.Sprintf("bad request: %v", err)})
			continue
		}
		for k, v := range job.Headers {
			req.Header.Set(k, v)
		}

		resp, err := client.Do(req)
		if err != nil {
			writeResult(writer, Result{ID: job.ID, Error: err.Error()})
			continue
		}
		defer resp.Body.Close()

		buf := new(bytes.Buffer)
		if _, err := buf.ReadFrom(resp.Body); err != nil {
			writeResult(writer, Result{ID: job.ID, Error: err.Error()})
			continue
		}

		hdrs := map[string]string{}
		for k, vs := range resp.Header {
			if len(vs) > 0 {
				hdrs[k] = vs[0]
			}
		}
		writeResult(writer, Result{
			ID:      job.ID,
			Status:  resp.StatusCode,
			Headers: hdrs,
			BodyB64: base64.StdEncoding.EncodeToString(buf.Bytes()),
			Proto:   resp.Proto,
		})
	}
}

func writeResult(w *bufio.Writer, r Result) {
	b, _ := json.Marshal(r)
	w.Write(b)
	w.WriteByte('\n')
	w.Flush()
}
