"""Thin entry into the shared search v2 substrate; legacy MVP remains available."""
import os,runpy,sys
from pathlib import Path
def main():
    candidates=[Path(os.getenv("SEARCH_V2_HOME","")) if os.getenv("SEARCH_V2_HOME") else None,Path(__file__).resolve().parents[2]/"quick-web-search",Path.home()/".openclaw"/"skills"/"quick-web-search"]
    for root in candidates:
        if root and (root/"scripts"/"search.py").is_file():
            script=root/"scripts"/"search.py";sys.path.insert(0,str(script.parent))
            args=sys.argv[1:]
            if args and args[0] not in {"search","read","research","auto","batch","health"} and not args[0].startswith("--"):args=["research",*args]
            sys.argv=[str(script),*args];runpy.run_path(str(script),run_name="__main__");return
    raise SystemExit("Shared quick-web-search v2 missing; set SEARCH_V2_HOME or deploy sibling skill.")
if __name__=="__main__":main()
