"""lince-lab: disposable lab-VM substrate for autonomous testing and regression hunting.

This package holds the importable logic that the thin ``lince-lab`` CLI front-end
dispatches into. Absolute imports only — inside the package use
``from lince_lab.x import Y`` (never relative ``.x``). See the module blueprint at
``claudedocs/lince-lab/blueprint.md`` for the authoritative design.
"""

__version__ = "1.0.0"
