"""Run the local W4 demo service."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("payresolve_ai.service.app:app", host="127.0.0.1", port=8765)
