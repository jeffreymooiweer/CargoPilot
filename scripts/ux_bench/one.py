"""Re-run one task by name, for checking a fix without the whole suite.

A second argument of `phone` runs it at 390x844, so a finding on the phone
pass can be chased without the twelve tasks in front of it.
"""
import sys
from bench import browser, history, sign_in, write
from playwright.sync_api import sync_playwright
import tasks

name = sys.argv[1] if len(sys.argv) > 1 else "task_7"
phone = len(sys.argv) > 2 and sys.argv[2] == "phone"
session = sign_in(); history(session, True); tasks.seed(session)
with sync_playwright() as p:
    engine, ctx = browser(p, session, 390, 844) if phone else browser(p, session)
    page = ctx.new_page()
    run = getattr(tasks, name)
    try:
        m = run(page, session)
    except TypeError:
        m = run(page)
    engine.close()
write([m], name=name)
