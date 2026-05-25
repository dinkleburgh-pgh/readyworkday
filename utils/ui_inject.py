"""utils/ui_inject.py

UI injection helpers extracted from app_unloadv1.7.py.
Contains:
  - inject_global_styles()       — base CSS for toasts, buttons, captions
  - inject_pwa_bootstrap()       — PWA manifest + service-worker registration
  - inject_blank_page_watchdog() — client-side blank/stall recovery watchdog
  - inject_inprogress_visibility_guard() — force-show main container on re-render
"""
import streamlit as st

# Fallback used when caller does not supply a max_reloads value.
_DEFAULT_WATCHDOG_MAX_RELOADS = 3


def inject_global_styles() -> None:
    """Inject base global CSS: toast positioning, button polish, auto-refresh
    skeleton suppression, and caption container hiding."""
    # --- toast / button / auto-refresh CSS ---
    st.markdown(
        """
        <style>
        [data-testid="stToastContainer"] {
            top: 0.85rem !important;
            right: 0.85rem !important;
            left: auto !important;
            bottom: auto !important;
            width: min(92vw, 430px) !important;
            max-width: min(92vw, 430px) !important;
            z-index: 1800 !important;
        }
        @supports (padding: max(0px)) {
            [data-testid="stToastContainer"] {
                top: calc(0.85rem + env(safe-area-inset-top)) !important;
                right: calc(0.85rem + env(safe-area-inset-right)) !important;
            }
        }
        [data-testid="stToast"] {
            border-radius: 12px !important;
            border: 1px solid rgba(125, 211, 252, 0.45) !important;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.93)) !important;
            color: #e2e8f0 !important;
            box-shadow: 0 14px 32px rgba(2, 6, 23, 0.42) !important;
            backdrop-filter: blur(6px) !important;
            -webkit-backdrop-filter: blur(6px) !important;
        }
        [data-testid="stToast"] p {
            color: #e2e8f0 !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
        }
        @media (max-width: 980px) {
            [data-testid="stToastContainer"] {
                top: 0.55rem !important;
                right: 0.55rem !important;
                width: min(96vw, 420px) !important;
                max-width: min(96vw, 420px) !important;
            }
            @supports (padding: max(0px)) {
                [data-testid="stToastContainer"] {
                    top: calc(0.55rem + env(safe-area-inset-top)) !important;
                    right: calc(0.55rem + env(safe-area-inset-right)) !important;
                }
            }
        }
        /* Hide skeleton loaders from auto-refresh timer components */
        [class*="_auto_refresh"] {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
        }
        [class*="_auto_refresh"] > div,
        [class*="_auto_refresh"] iframe {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            border: 0 !important;
        }
        [class*="_auto_refresh"] [data-testid="stSkeleton"],
        [class*="_auto_refresh"] .stSkeleton {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }
        /* Truck button base polish */
        button[kind="primary"] {
            border-radius: 14px !important;
            transition: filter 0.10s ease, transform 0.10s ease !important;
        }
        button[kind="primary"]:hover {
            filter: brightness(1.13) !important;
            transform: translateY(-1px) !important;
        }
        button[kind="primary"]:active {
            filter: brightness(0.88) !important;
            transform: translateY(1px) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # --- caption container hiding ---
    st.markdown(
        """
        <style>
        div[data-testid="stCaptionContainer"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_pwa_bootstrap() -> None:
    """Inject mobile/PWA metadata and service worker registration into the parent document."""
    st.html(
        """
        <script>
        (async () => {
            const parentWin = window.parent;
            if (!parentWin || !parentWin.document) {
                return;
            }
            const doc = parentWin.document;
            if (doc.documentElement.dataset.truckappPwaInit === "1") {
                return;
            }
            doc.documentElement.dataset.truckappPwaInit = "1";

            const ensureMeta = (name, content, attr = "name") => {
                const selector = `meta[${attr}="${name}"]`;
                let el = doc.head.querySelector(selector);
                if (!el) {
                    el = doc.createElement("meta");
                    el.setAttribute(attr, name);
                    doc.head.appendChild(el);
                }
                el.setAttribute("content", content);
            };

            const ensureLink = (rel, href) => {
                let el = doc.head.querySelector(`link[rel="${rel}"]`);
                if (!el) {
                    el = doc.createElement("link");
                    el.setAttribute("rel", rel);
                    doc.head.appendChild(el);
                }
                el.setAttribute("href", href);
                return el;
            };

            ensureMeta("viewport", "width=device-width, initial-scale=1, viewport-fit=cover");
            ensureMeta("theme-color", "#0f172a");
            ensureMeta("color-scheme", "dark");
            ensureMeta("format-detection", "telephone=no");
            ensureMeta("apple-mobile-web-app-capable", "yes");
            ensureMeta("apple-mobile-web-app-status-bar-style", "black-translucent");
            ensureMeta("apple-mobile-web-app-title", "TruckApp");
            ensureMeta("mobile-web-app-capable", "yes");

            const staticCandidates = ["/app/static", "/static", "./static"];
            const assetMatchesType = async (url, expectedTypes) => {
                try {
                    const resp = await fetch(url, { method: "GET", cache: "no-store" });
                    if (!resp.ok) {
                        return false;
                    }
                    const contentType = String(resp.headers.get("content-type") || "").toLowerCase();
                    return expectedTypes.some((hint) => contentType.includes(String(hint).toLowerCase()));
                } catch (_) {
                    return false;
                }
            };

            let staticRoot = null;
            let staticWorkerAvailable = false;
            for (const candidate of staticCandidates) {
                const manifestOk = await assetMatchesType(`${candidate}/manifest.webmanifest`, ["manifest", "json"]);
                const swOk = await assetMatchesType(`${candidate}/sw.js`, ["javascript", "ecmascript"]);
                if (manifestOk) {
                    staticRoot = candidate;
                    staticWorkerAvailable = swOk;
                    break;
                }
            }

            if (!staticRoot) {
                return;
            }

            ensureLink("manifest", `${staticRoot}/manifest.webmanifest`);
            const favicon = ensureLink("icon", `${staticRoot}/icons/truckapp-icon-192.png`);
            favicon.setAttribute("sizes", "192x192");
            favicon.setAttribute("type", "image/png");
            const appleIcon = ensureLink("apple-touch-icon", `${staticRoot}/icons/truckapp-icon-180.png`);
            appleIcon.setAttribute("sizes", "180x180");
            appleIcon.setAttribute("type", "image/png");

            if (staticWorkerAvailable && "serviceWorker" in parentWin.navigator) {
                try {
                    const swScope = new URL(`${staticRoot.replace(/\\/$/, "")}/`, parentWin.location.origin).pathname;
                    await parentWin.navigator.serviceWorker.register(`${staticRoot}/sw.js`, { scope: swScope });
                } catch (_) {
                    // Non-fatal: app still functions as normal web app without SW.
                }
            }
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def inject_blank_page_watchdog(max_reloads: int, is_mobile: bool) -> None:
    """Client-side watchdog that detects a blank/stalled Streamlit render and
    reloads the page up to *max_reloads* times within a rolling window."""
    max_reload_count = max(1, int(max_reloads or _DEFAULT_WATCHDOG_MAX_RELOADS))
    is_mobile_client = bool(is_mobile)
    st.html(
        f"""
        <script>
        (function() {{
            try {{
                const hostWin = window.parent || window;
                const root = hostWin.document;
                if (!hostWin || !root || hostWin.__truckBlankWatchdogBound) return;
                hostWin.__truckBlankWatchdogBound = true;

                const MAX_RELOADS = {int(max_reload_count)};
                const CHECK_MS = 1200;
                const STALL_MS = 8500;
                const TRANSIENT_MAX_MS = 12000;
                const USER_ACTION_GRACE_MS = 9000;
                const FAST_RESUME_HIDDEN_MS = 2 * 60 * 1000;
                const IS_MOBILE_CLIENT = {str(bool(is_mobile_client)).lower()};
                const WINDOW_MS = 15 * 60 * 1000;
                const KEY_TS = "truckappBlankWatchdogTs";
                const KEY_COUNT = "truckappBlankWatchdogCount";

                const nowMs = () => Date.now();
                const toFiniteNumber = (value) => {{
                    const parsed = Number(value);
                    return Number.isFinite(parsed) ? parsed : 0;
                }};

                const readReloadState = () => {{
                    try {{
                        const stamp = toFiniteNumber(hostWin.sessionStorage.getItem(KEY_TS));
                        const count = toFiniteNumber(hostWin.sessionStorage.getItem(KEY_COUNT));
                        if (!stamp || (nowMs() - stamp) > WINDOW_MS) {{
                            return {{ stamp: 0, count: 0 }};
                        }}
                        return {{ stamp, count }};
                    }} catch (e) {{
                        return {{ stamp: 0, count: 0 }};
                    }}
                }};

                const writeReloadState = (count) => {{
                    try {{
                        hostWin.sessionStorage.setItem(KEY_TS, String(nowMs()));
                        hostWin.sessionStorage.setItem(KEY_COUNT, String(Math.max(0, count)));
                    }} catch (e) {{}}
                }};

                const buildRecoveryUrl = (reason, count, stallMs, visibilityState, hiddenMs = null) => {{
                    try {{
                        const nextUrl = new hostWin.URL(hostWin.location.href);
                        nextUrl.searchParams.set("diag_event", "blank_watchdog_reload");
                        nextUrl.searchParams.set("diag_reason", String(reason || "unknown").slice(0, 48));
                        nextUrl.searchParams.set("diag_count", String(Math.max(0, Number(count || 0))));
                        if (Number.isFinite(stallMs)) {{
                            nextUrl.searchParams.set("diag_stall_ms", String(Math.max(0, Math.round(stallMs))));
                        }}
                        if (Number.isFinite(hiddenMs)) {{
                            nextUrl.searchParams.set("diag_hidden_ms", String(Math.max(0, Math.round(hiddenMs))));
                        }}
                        if (visibilityState) {{
                            nextUrl.searchParams.set("diag_vis", String(visibilityState).slice(0, 16));
                        }}
                        return nextUrl.toString();
                    }} catch (e) {{
                        return null;
                    }}
                }};

                const removeOverlayHost = () => {{
                    try {{
                        const overlayHost = root.getElementById('shop-notice-overlay-host');
                        if (overlayHost) overlayHost.remove();
                    }} catch (e) {{}}
                }};

                const isVisibleNode = (node, minWidth = 16, minHeight = 10) => {{
                    try {{
                        if (!node || typeof node.getBoundingClientRect !== "function") return false;
                        const style = hostWin.getComputedStyle ? hostWin.getComputedStyle(node) : null;
                        if (style) {{
                            const opacity = Number(style.opacity);
                            if (style.display === "none" || style.visibility === "hidden" || (!Number.isNaN(opacity) && opacity <= 0.02)) {{
                                return false;
                            }}
                        }}
                        const rect = node.getBoundingClientRect();
                        return rect.width >= minWidth && rect.height >= minHeight;
                    }} catch (e) {{
                        return false;
                    }}
                }};

                const hasVisibleMainContent = (container) => {{
                    if (!container) return false;
                    const selectors = [
                        '[data-testid="stButton"]',
                        '[data-testid="stSelectbox"]',
                        '[data-testid="stMultiSelect"]',
                        '[data-testid="stTextInput"]',
                        '[data-testid="stNumberInput"]',
                        '[data-testid="stTextArea"]',
                        '[data-testid="stTable"]',
                        '[data-testid="stDataFrame"]',
                        '[data-testid="stAlert"]',
                        '[data-testid="stHeading"]',
                        '[data-testid="stMarkdownContainer"]',
                        'button',
                        'input',
                        'textarea',
                        'table'
                    ].join(', ');
                    const nodes = Array.from(container.querySelectorAll(selectors));
                    for (const node of nodes) {{
                        if (isVisibleNode(node)) return true;
                    }}
                    return false;
                }};

                let blankSinceMs = 0;
                let transientSinceMs = 0;
                let lastUserActionMs = nowMs();
                let hiddenSinceMs = 0;
                let pendingResumeHiddenMs = 0;
                let resumeReloadQueued = false;

                const resetRecoveryTimers = () => {{
                    blankSinceMs = 0;
                    transientSinceMs = 0;
                }};

                const markUserAction = () => {{
                    lastUserActionMs = nowMs();
                    resetRecoveryTimers();
                }};

                const hasTransientUi = () => Boolean(
                    root.querySelector('[role="dialog"], [data-testid="stSpinner"], [data-testid="stStatusWidget"], [data-testid="stSkeleton"]')
                );

                const isRenderHealthy = () => {{
                    const appRoot =
                        root.querySelector('[data-testid="stAppViewContainer"]') ||
                        root.querySelector('.stApp');
                    if (!appRoot) return true;

                    const style = hostWin.getComputedStyle ? hostWin.getComputedStyle(appRoot) : null;
                    if (style && (style.display === "none" || style.visibility === "hidden")) {{
                        return false;
                    }}

                    // Ignore transient Streamlit states briefly while the next render mounts.
                    if (hasTransientUi()) {{
                        if (!transientSinceMs) transientSinceMs = nowMs();
                        if ((nowMs() - transientSinceMs) <= TRANSIENT_MAX_MS) {{
                            return true;
                        }}
                    }} else {{
                        transientSinceMs = 0;
                    }}

                    const mainContainer =
                        root.querySelector('[data-testid="stMainBlockContainer"]') ||
                        root.querySelector('[data-testid="stMain"]') ||
                        root.querySelector('section.main');
                    if (!mainContainer) return true;

                    const rect =
                        typeof mainContainer.getBoundingClientRect === "function"
                            ? mainContainer.getBoundingClientRect()
                            : {{ width: 0, height: 0 }};
                    const hasArea = rect.width > 80 && rect.height > 60;
                    const hasMeaningfulContent = hasVisibleMainContent(mainContainer);

                    if (!hasArea) return false;
                    if (!hasMeaningfulContent) return false;
                    return true;
                }};

                const showManualRecoveryHint = (reason) => {{
                    try {{
                        if (root.getElementById("truckapp-blank-watchdog-hint")) return;
                        const hint = root.createElement("div");
                        hint.id = "truckapp-blank-watchdog-hint";
                        const suffix = reason ? " (" + String(reason).slice(0, 28) + ")" : "";
                        hint.textContent = "Render stalled after auto-retries" + suffix + ". Press Ctrl+F5 to hard refresh.";
                        hint.style.position = "fixed";
                        hint.style.right = "10px";
                        hint.style.bottom = "10px";
                        hint.style.zIndex = "2147483647";
                        hint.style.background = "rgba(17,24,39,0.94)";
                        hint.style.color = "#e5e7eb";
                        hint.style.border = "1px solid rgba(148,163,184,0.55)";
                        hint.style.borderRadius = "8px";
                        hint.style.padding = "8px 10px";
                        hint.style.fontSize = "12px";
                        hint.style.fontWeight = "700";
                        hint.style.boxShadow = "0 10px 25px rgba(0,0,0,0.35)";
                        hint.style.pointerEvents = "none";
                        root.body.appendChild(hint);
                    }} catch (e) {{}}
                }};

                const recoverWithReload = (reason, stallMs, hiddenMs = null) => {{
                    const state = readReloadState();
                    if (state.count >= MAX_RELOADS) {{
                        showManualRecoveryHint(reason);
                        return;
                    }}

                    const nextCount = state.count + 1;
                    writeReloadState(nextCount);
                    removeOverlayHost();

                    const target = buildRecoveryUrl(
                        reason,
                        nextCount,
                        stallMs,
                        root.visibilityState || "visible",
                        hiddenMs,
                    );
                    try {{
                        if (target) hostWin.location.replace(target);
                        else hostWin.location.reload();
                    }} catch (e) {{
                        try {{ hostWin.location.reload(); }} catch (e2) {{}}
                    }}
                }};

                const maybeRecover = (reason = "interval") => {{
                    if (root.visibilityState === "hidden") return;

                    if ((nowMs() - lastUserActionMs) < USER_ACTION_GRACE_MS) return;

                    if (isRenderHealthy()) {{
                        blankSinceMs = 0;
                        return;
                    }}

                    // Wait for connectivity to return before forcing reload loops.
                    if (hostWin.navigator && hostWin.navigator.onLine === false) {{
                        if (!blankSinceMs) blankSinceMs = nowMs();
                        return;
                    }}

                    removeOverlayHost();

                    if (!blankSinceMs) {{
                        blankSinceMs = nowMs();
                        return;
                    }}

                    const stalledMs = nowMs() - blankSinceMs;
                    if (stalledMs < STALL_MS) return;

                    recoverWithReload(reason, stalledMs);
                }};

                const queueFastResumeReload = (reason, hiddenDurationMs, delayMs = 220) => {{
                    if (!IS_MOBILE_CLIENT || hiddenDurationMs < FAST_RESUME_HIDDEN_MS) return false;
                    pendingResumeHiddenMs = hiddenDurationMs;
                    if (resumeReloadQueued) return true;
                    if (hostWin.navigator && hostWin.navigator.onLine === false) return true;

                    resumeReloadQueued = true;
                    try {{
                        hostWin.setTimeout(() => {{
                            resumeReloadQueued = false;
                            if ((root.visibilityState || "visible") === "hidden") return;
                            if (hostWin.navigator && hostWin.navigator.onLine === false) return;

                            const hiddenMsToReport = pendingResumeHiddenMs || hiddenDurationMs;
                            pendingResumeHiddenMs = 0;
                            recoverWithReload(
                                `resume_${{String(reason || "visible").slice(0, 18)}}`,
                                null,
                                hiddenMsToReport,
                            );
                        }}, Math.max(60, Number(delayMs) || 0));
                    }} catch (e) {{
                        resumeReloadQueued = false;
                    }}
                    return true;
                }};

                const scheduleRecoveryCheck = (reason, delayMs = 160) => {{
                    try {{
                        hostWin.setTimeout(() => maybeRecover(reason), delayMs);
                    }} catch (e) {{}}
                }};

                const handleResumeSignal = (reason, delayMs = 160) => {{
                    const hiddenDurationMs = hiddenSinceMs ? Math.max(0, nowMs() - hiddenSinceMs) : 0;
                    hiddenSinceMs = 0;
                    resetRecoveryTimers();

                    if (!queueFastResumeReload(reason, hiddenDurationMs, delayMs + 60)) {{
                        pendingResumeHiddenMs = 0;
                        scheduleRecoveryCheck(reason, delayMs);
                    }}
                }};

                if (hostWin.__truckBlankWatchdogTimer) {{
                    try {{ hostWin.clearInterval(hostWin.__truckBlankWatchdogTimer); }} catch (e) {{}}
                }}
                hostWin.__truckBlankWatchdogTimer = hostWin.setInterval(() => maybeRecover("interval"), CHECK_MS);

                hostWin.addEventListener("pageshow", () => {{
                    handleResumeSignal("pageshow", 180);
                }}, {{ passive: true }});

                hostWin.addEventListener("focus", () => {{
                    handleResumeSignal("focus", 140);
                }}, {{ passive: true }});

                hostWin.addEventListener("online", () => {{
                    if (pendingResumeHiddenMs >= FAST_RESUME_HIDDEN_MS) {{
                        queueFastResumeReload("online", pendingResumeHiddenMs, 180);
                        return;
                    }}
                    handleResumeSignal("online", 220);
                }}, {{ passive: true }});

                hostWin.addEventListener("pagehide", () => {{
                    hiddenSinceMs = nowMs();
                }}, {{ passive: true }});

                root.addEventListener("visibilitychange", () => {{
                    if ((root.visibilityState || "visible") === "hidden") {{
                        hiddenSinceMs = nowMs();
                        return;
                    }}

                    handleResumeSignal("visible", 200);
                }}, {{ passive: true }});

                root.addEventListener("pointerdown", markUserAction, true);
                root.addEventListener("keydown", markUserAction, true);
                root.addEventListener("touchstart", markUserAction, {{ passive: true, capture: true }});

                root.addEventListener("readystatechange", () => {{
                    if (root.readyState === "complete") {{
                        scheduleRecoveryCheck("ready", 120);
                    }}
                }}, {{ passive: true }});

                scheduleRecoveryCheck("boot", 260);
            }} catch (e) {{}}
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def inject_inprogress_visibility_guard() -> None:
    """Force the main Streamlit app container to be visible after an in-progress render."""
    st.html(
        """
        <script>
        (function() {
            try {
                const root = window.parent.document;
                if (!root) return;

                const appRoot =
                    root.querySelector('[data-testid="stAppViewContainer"]') ||
                    root.querySelector('.stApp');
                const mainContainer =
                    root.querySelector('[data-testid="stMainBlockContainer"]') ||
                    root.querySelector('[data-testid="stMain"]') ||
                    root.querySelector('section.main');

                [appRoot, mainContainer].forEach((node) => {
                    if (!node || !node.style) return;
                    node.style.removeProperty('display');
                    node.style.setProperty('visibility', 'visible', 'important');
                    node.style.setProperty('opacity', '1', 'important');
                });
            } catch (e) {}
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
