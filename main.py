import os

import uvicorn

from src.api.app import app
from src.core.logging import configurar_logging

configurar_logging()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                8000,
            )
        ),
    )