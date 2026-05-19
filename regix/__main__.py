"""Allow `python -m regix` to behave like the `regix` console script."""

from .cli import app


if __name__ == "__main__":
    app()
