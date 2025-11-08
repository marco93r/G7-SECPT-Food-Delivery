from __future__ import annotations

import os

from payment_service.app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8083")),
        reload=True,
    )
