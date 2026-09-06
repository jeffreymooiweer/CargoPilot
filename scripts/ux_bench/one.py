"""Re-run one task by name, for checking a fix without the whole suite."""
import sys
from bench import browser, history, sign_in, write
from playwright.sync_api import sync_playwright
import tasks

name = sys.argv[1] if len(sys.argv) > 1 else "task_7"
session = sign_in(); history(session, True); tasks.seed(session)
with sync_playwright() as p:
    engine, ctx = browser(p, session)
    page = ctx.new_page()
    run = getattr(tasks, name)
    try:
        m = run(page, session)
    except TypeError:
        m = run(page)
    engine.close()
write([m], name=name)
