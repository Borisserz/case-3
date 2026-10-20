"""Back-compat shim — prefer ``case3.image_api`` (office FastAPI /generate+/edit)."""

from __future__ import annotations

from case3.image_api import (  # noqa: F401
    ImageApiConfig,
    KandinskyConfig,
    edit_png,
    generate_all_figures,
    generate_png,
    image_api_configured,
    max_images_from_env,
)

__all__ = [
    "ImageApiConfig",
    "KandinskyConfig",
    "edit_png",
    "generate_all_figures",
    "generate_png",
    "image_api_configured",
    "max_images_from_env",
]
