from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    required_files = [
        root / "data" / "sales.csv",
        root / "data" / "orders.csv",
        root / "data" / "sample_submission.csv",
    ]

    missing = [str(p.relative_to(root)) for p in required_files if not p.exists()]
    if missing:
        raise SystemExit(f"Missing required data files: {missing}")

    # Import checks to catch missing packages early.
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import sklearn  # noqa: F401

    try:
        import lightgbm  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Package check failed: lightgbm is required. Install with 'pip install -r requirements.txt'."
        ) from exc

    print("Sanity check passed: files and core packages are available.")


if __name__ == "__main__":
    main()
