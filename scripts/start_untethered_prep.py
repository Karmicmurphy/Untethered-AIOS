"""Prep-only launcher check. NOT the final Untethered launcher."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__":
    print("TWIS UNTETHERED — CREDIT-GAP PREP SELF-CHECK")
    result=subprocess.run([sys.executable,str(ROOT/"scripts"/"run_credit_gap_prep_benchmark.py")],cwd=ROOT)
    print("prep modules:","PASS" if result.returncode==0 else "FAIL")
    print("integration with latest local Campaign 3+:","NOT YET VERIFIED")
    print("real conversational model:","NOT INSTALLED / NOT REQUIRED")
    raise SystemExit(result.returncode)
