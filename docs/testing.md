Project Maestro v2 – Testing

Scope

- Unit tests for frame sampling, parsing, and concurrency helpers
- Manual tests for end-to-end flows

Unit Tests

- Frame Extraction: correct indices for N=5; handles short videos
- Director Parsing: extracts 5 shots from SHOT N: lines; tolerates minor formatting
- Concurrency: ensures bounded parallelism and independent result updates

Manual QA

- Upload: valid mp4 under 30s; reject longer inputs gracefully
- Analyze: context concise; director returns 5 shots
- UI: rows rendered; edits persist; multiple Generate calls in parallel
- Generation: preview updates; save downloads PNG; thumbnail opens full image
- Error Cases: API error on one row doesn’t block others; retry works


