"""`python -m cad_trust` → audit CLI (the only CLI we ship in v0.1.1)."""
from cad_trust.audit import main

if __name__ == "__main__":
    raise SystemExit(main())
