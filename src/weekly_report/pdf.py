from pathlib import Path

FALTA_PLAYWRIGHT = (
    "Para exportar a PDF hace falta Playwright:\n"
    "  uv sync --extra pdf\n"
    "  uv run playwright install chromium"
)


def save_pdf(html_path: Path) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(FALTA_PLAYWRIGHT)

    path = html_path.with_suffix(".pdf")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.pdf(path=path, format="Letter", print_background=True)
        browser.close()
    return path
