import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "data" / "healthcare.duckdb"))
out_path = ROOT / "data" / "gold_clinical_summary.csv"
con.execute(f"COPY main.clinical_summary TO '{out_path.as_posix()}' (HEADER, DELIMITER ',')")
print(f"Exported to {out_path}")
