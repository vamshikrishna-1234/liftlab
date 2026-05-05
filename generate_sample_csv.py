"""Generate a sample customer population CSV for demos.

Used both by the Streamlit app's 'Download sample' button (in-memory) and to
produce the static `samples/liftlab_sample_population.csv` file shipped in
the repo so demo viewers can grab one with a single click.
"""
from __future__ import annotations

from pathlib import Path

from liftlab.data import generate_population


def main() -> None:
    out_dir = Path("samples")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "liftlab_sample_population.csv"

    df = generate_population(n_households=50_000, seed=42)
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df):,} rows to {out_path}")
    print(f"File size: {out_path.stat().st_size / 1024:.1f} KB")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
