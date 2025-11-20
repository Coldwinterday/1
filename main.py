import os
import shlex
from typing import Generator, List

import paramiko
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

HOST = os.getenv("SSH_HOST", "172.18.10.38")
PORT = int(os.getenv("SSH_PORT", "22"))
USERNAME = os.getenv("SSH_USER", "ubuntu")
PASSWORD = os.getenv("SSH_PASSWORD", "Sixi@123")


class DirectoryResponse(BaseModel):
    path: str = Field(..., description="Queried path")
    entries: List[str] = Field(..., description="Directory entries")


class CompileRequest(BaseModel):
    remote_path: str = Field(..., description="Remote working directory containing fpga.tcl")


app = FastAPI(title="Remote Vivado Compiler")


def _get_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"SSH connection failed: {exc}") from exc
    return client


def _list_directory(path: str) -> List[str]:
    client = _get_client()
    try:
        with client.open_sftp() as sftp:
            try:
                entries = sftp.listdir(path)
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=f"Path not found: {path}") from exc
            return sorted(entries)
    finally:
        client.close()


def _stream_command(path: str) -> Generator[bytes, None, None]:
    client = _get_client()
    command = f"cd {shlex.quote(path)} && vivado -mode batch -source fpga.tcl"
    channel = client.get_transport().open_session()
    channel.exec_command(command)

    try:
        while True:
            if channel.recv_ready():
                yield channel.recv(1024)
            if channel.recv_stderr_ready():
                yield channel.recv_stderr(1024)
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
    finally:
        status = channel.recv_exit_status()
        client.close()
        completion = f"\nCompilation finished with exit code {status}."
        yield completion.encode()


@app.get("/directories", response_model=DirectoryResponse)
def list_directories(path: str = ".") -> DirectoryResponse:
    entries = _list_directory(path)
    return DirectoryResponse(path=path, entries=entries)


@app.post("/compile")
def compile_design(request: CompileRequest) -> StreamingResponse:
    try:
        generator = _stream_command(request.remote_path)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to start compilation: {exc}") from exc

    return StreamingResponse(generator, media_type="text/plain")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
