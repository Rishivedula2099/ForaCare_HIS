"""P7-B03: HTML -> PDF through headless Chromium (Playwright).

Playwright's *sync* API runs on one dedicated worker thread that owns the
browser, rather than the async API on the server's event loop: the async
API needs subprocess support that some event-loop policies (notably
uvicorn's on Windows) don't provide, and a single owner thread keeps the
browser lifecycle simple. The browser starts lazily on first use and is
reused; renders are serialized through that thread.
"""
import asyncio
import html
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.documents.layout import PageSpec

logger = logging.getLogger(__name__)

_MM_PER_PX = 25.4 / 96
_RENDER_TIMEOUT_MS = 15_000
# Renders are serialized on one thread; beyond this many waiting, fail fast
# with a clear 503 rather than let requests pile up behind a slow render.
_MAX_PENDING = 20


class PdfEngineUnavailableError(AppError):
    code = "PDF_ENGINE_UNAVAILABLE"
    status_code = 503


def _footer_template(footer_text: str | None, margin_mm: float) -> str:
    extra = f"<div>{html.escape(footer_text)}</div>" if footer_text else ""
    return (
        f'<div style="width:100%;font-size:7px;color:#64748b;padding:0 {margin_mm}mm;font-family:Helvetica,Arial,sans-serif;">'
        f"{extra}"
        '<div style="display:flex;justify-content:space-between;">'
        "<span>Generated via ForaCare HIS</span>"
        '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
        "</div></div>"
    )


class _PdfWorker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pdf-render")
        self._playwright = None
        self._browser = None
        self._pending = 0

    # --- runs on the worker thread -------------------------------------
    def _ensure_browser(self):
        if self._browser is not None and self._browser.is_connected():
            return self._browser
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()
        args = ["--no-sandbox"] if get_settings().pdf_chromium_no_sandbox else []
        self._browser = self._playwright.chromium.launch(headless=True, args=args)
        return self._browser

    def _render(self, html_source: str, spec: PageSpec, footer_text: str | None) -> bytes:
        browser = self._ensure_browser()
        # A continuous roll must be laid out at its printable width, otherwise
        # the height measured below is for the wrong line wrapping.
        continuous = spec.height_mm is None
        viewport = (
            {"width": round((spec.width_mm - 2 * spec.margin_mm) / _MM_PER_PX), "height": 400} if continuous else None
        )
        page = browser.new_page(viewport=viewport) if viewport else browser.new_page()
        try:
            # Documents are self-contained; never let rendered content reach out.
            page.route(
                "**/*",
                lambda route: route.continue_()
                if route.request.url.startswith(("data:", "about:"))
                else route.abort(),
            )
            page.set_default_timeout(_RENDER_TIMEOUT_MS)
            page.set_content(html_source, wait_until="load")
            if continuous:
                # One page exactly as tall as the content.
                content_px = page.evaluate("document.body.getBoundingClientRect().height")
                height_mm = max(content_px * _MM_PER_PX + 2 * spec.margin_mm + 2, 30)
                margin = f"{spec.margin_mm}mm"
                return page.pdf(
                    width=f"{spec.width_mm}mm",
                    height=f"{height_mm:.1f}mm",
                    print_background=True,
                    margin={"top": margin, "bottom": margin, "left": margin, "right": margin},
                )
            if spec.paged:
                return page.pdf(
                    prefer_css_page_size=True,
                    print_background=True,
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template=_footer_template(footer_text, spec.margin_mm),
                )
            return page.pdf(prefer_css_page_size=True, print_background=True)
        finally:
            page.close()

    def _close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    # --- async API -----------------------------------------------------
    async def render(self, html_source: str, spec: PageSpec, footer_text: str | None) -> bytes:
        if self._pending >= _MAX_PENDING:
            raise PdfEngineUnavailableError("The PDF service is busy. Please try again shortly.")
        loop = asyncio.get_running_loop()
        self._pending += 1
        try:
            return await loop.run_in_executor(self._executor, self._render, html_source, spec, footer_text)
        except Exception as exc:  # launch failure (browser not installed), crash, timeout
            logger.exception("PDF render failed")
            raise PdfEngineUnavailableError(
                "The PDF engine is unavailable. Ensure Playwright's Chromium is installed."
            ) from exc
        finally:
            self._pending -= 1

    async def shutdown(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._close)
        self._executor.shutdown(wait=False)


_worker: _PdfWorker | None = None


async def render_pdf(html_source: str, *, page: PageSpec, footer_text: str | None = None) -> bytes:
    global _worker
    if _worker is None:
        _worker = _PdfWorker()
    return await _worker.render(html_source, page, footer_text)


async def shutdown_pdf_engine() -> None:
    global _worker
    if _worker is not None:
        worker, _worker = _worker, None
        await worker.shutdown()
