# Remote Vivado Compiler API

This FastAPI service connects to the target FPGA build server over SSH, lets users browse remote directories, and streams the output of running Vivado in batch mode.

## Configuration
Environment variables override the default SSH connection values:

- `SSH_HOST` (default: `172.18.10.38`)
- `SSH_PORT` (default: `22`)
- `SSH_USER` (default: `ubuntu`)
- `SSH_PASSWORD` (default: `Sixi@123`)

## Endpoints
- `GET /directories?path=.` — Lists entries in the provided remote path via SFTP.
- `POST /compile` — Body `{ "remote_path": "/path/to/design" }`. Streams the output of `vivado -mode batch -source fpga.tcl` executed inside that directory.

## Running locally
1. Install dependencies: `pip install -r requirements.txt`
2. Start the API: `uvicorn main:app --reload`
3. Consume streaming output with any HTTP client that supports streaming (e.g., `curl`, browsers, or frontend via Fetch streaming).
