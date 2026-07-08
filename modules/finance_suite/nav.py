"""
modules/finance_suite/nav.py — exposes the Finance AI Suite's pages to the ERP shell.

One st.Page per agent, driven by SUITE metadata. Paths are relative to the app
entrypoint (app.py at repo root), mirroring modules/finance/nav.py.
"""
import streamlit as st

from modules.finance_suite.specs import SUITE

_PAGES = "modules/finance_suite/pages"

# Order the nav; give the first page a stable url_path.
_ORDER = ["ap", "ar", "cashflow", "reconciliation", "insights", "copilot"]


def get_pages():
    pages = []
    for i, key in enumerate(_ORDER):
        spec = SUITE[key]
        kwargs = {"title": spec.title, "icon": spec.icon}
        if i == 0:
            kwargs["url_path"] = f"suite-{key}"
        pages.append(st.Page(f"{_PAGES}/{key}.py", **kwargs))
    return pages
