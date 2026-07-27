"""
HOMI Theme System

Design direction: "Academic" — clean white background, Marcellus serif headings,
Inter body text, charcoal accents, minimal decoration. Inspired by research
project pages.
"""

from typing import Dict, Tuple, Any

# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Surface
    "bg": "#ffffff",
    "bg_secondary": "#fafafa",
    "bg_sidebar": "#f5f5f5",
    "surface": "#ffffff",

    # Text
    "text": "#1a1a1a",
    "text_secondary": "#555555",
    "text_tertiary": "#999999",

    # Accent — charcoal (academic, understated)
    "accent": "#36454F",
    "accent_hover": "#2a363e",
    "accent_light": "#e8ecee",

    # Border
    "border": "#e5e5e5",
    "border_subtle": "#ededed",

    # Status
    "success": "#2e7d32",
    "warning": "#e65100",
    "error": "#c62828",
    "info": "#1565c0",

    # Legacy aliases
    "primary": "#36454F",
    "primary_hover": "#2a363e",
    "primary_light": "#e8ecee",
    "secondary": "#2e7d32",
    "secondary_hover": "#1b5e20",
    "bg_dark": "#ffffff",
    "bg_card": "#ffffff",
    "bg_hover": "#f5f5f5",
    "text_muted": "#555555",
}

# Layer colors for GDS visualization
LAYER_COLORS = {
    (1, 0): {"face": "#4a90d9", "edge": "#2c6fbd", "name": "Core"},
    (2, 0): {"face": "#e07b39", "edge": "#b85d20", "name": "Metal"},
    (3, 0): {"face": "#4caf50", "edge": "#388e3c", "name": "Oxide"},
    (4, 0): {"face": "#9575cd", "edge": "#7e57c2", "name": "Via"},
    (5, 0): {"face": "#ef5350", "edge": "#c62828", "name": "Passivation"},
    (6, 0): {"face": "#26c6da", "edge": "#00acc1", "name": "Nitride"},
    (7, 0): {"face": "#ec407a", "edge": "#c2185b", "name": "Poly"},
    (8, 0): {"face": "#9ccc65", "edge": "#7cb342", "name": "Active"},
}


def get_layer_color(layer: Tuple[int, int]) -> Dict[str, str]:
    """Get colors for a specific layer."""
    if layer in LAYER_COLORS:
        return LAYER_COLORS[layer].copy()
    layer_num = layer[0] % 8
    fallback_key = (layer_num if layer_num > 0 else 1, 0)
    colors = LAYER_COLORS.get(fallback_key, LAYER_COLORS[(1, 0)]).copy()
    colors["name"] = f"Layer {layer[0]}/{layer[1]}"
    return colors


# =============================================================================
# CSS THEME
# =============================================================================

def get_theme_css() -> str:
    """Generate complete CSS theme string."""
    return """
<style>
    /* ================================================================
       FONTS — Marcellus (headings) + Inter (body)
       Same pairing as the reference academic project pages
       ================================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Marcellus&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        color: #1a1a1a !important;
    }

    h1, h2, h3,
    [data-testid="stHeadingWithActionElements"] {
        font-family: 'Marcellus', Georgia, serif !important;
        color: #1a1a1a !important;
    }

    /* ================================================================
       CORE — light background, override Streamlit dark mode
       ================================================================ */
    .stApp {
        background-color: #ffffff !important;
    }

    .stApp > header {
        background-color: transparent !important;
    }

    header[data-testid="stHeader"] {
        background: rgba(255,255,255,0.95) !important;
        backdrop-filter: blur(8px) !important;
    }

    /* Force light text everywhere */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    [data-testid="stText"],
    label, .stRadio label span,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {
        color: #1a1a1a !important;
    }

    /* ================================================================
       BRAND
       ================================================================ */
    .homi-brand {
        text-align: center;
        padding: 2rem 0 0.5rem;
    }

    .homi-brand h1 {
        font-family: 'Marcellus', Georgia, serif !important;
        font-size: 2.4rem;
        font-weight: 400;
        letter-spacing: 0.12em;
        color: #1a1a1a !important;
        margin: 0;
    }

    .homi-brand .tagline {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        font-weight: 400;
        color: #888;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-top: 6px;
    }

    /* ================================================================
       STEP PROGRESS — clean circles on white
       ================================================================ */
    .step-progress {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem 0 0.5rem;
        max-width: 580px;
        margin: 0 auto;
    }

    .step-node {
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .step-circle {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        font-weight: 600;
        transition: all 0.2s ease;
        border: 1.5px solid #d4d4d4;
        background: #fff;
        color: #999;
    }

    .step-circle.completed {
        background: #36454F;
        border-color: #36454F;
        color: #fff;
    }

    .step-circle.active {
        background: #1a1a1a;
        border-color: #1a1a1a;
        color: #fff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    .step-circle.viewing {
        background: #e65100;
        border-color: #e65100;
        color: #fff;
    }

    .step-circle.clickable {
        cursor: pointer;
    }

    .step-circle.clickable:hover {
        background: #4a5d68;
        border-color: #4a5d68;
        color: #fff;
    }

    .step-name {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 500;
        color: #999;
        margin-top: 5px;
        text-align: center;
        white-space: nowrap;
        transition: color 0.2s;
    }

    .step-name.completed { color: #36454F; }
    .step-name.active { color: #1a1a1a; font-weight: 600; }
    .step-name.viewing { color: #e65100; }

    .step-connector {
        flex: 1;
        height: 1.5px;
        min-width: 18px;
        max-width: 40px;
        margin: 0 3px;
        margin-bottom: 20px;
        background: #e5e5e5;
        transition: background 0.2s;
    }

    .step-connector.done {
        background: #36454F;
    }

    /* ================================================================
       SECTION HEADER
       ================================================================ */
    .section-header {
        margin: 1.8rem 0 1rem;
        padding-bottom: 0.6rem;
        border-bottom: 2px solid #ededed;
    }

    .section-header h2 {
        font-family: 'Marcellus', Georgia, serif !important;
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1.5rem !important;
        font-weight: 400 !important;
        color: #1a1a1a !important;
    }

    .section-header .section-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.82rem;
        color: #888;
        margin-top: 4px;
    }

    /* ================================================================
       CARDS — white with subtle border
       ================================================================ */
    .homi-card {
        background: #fff;
        border: 1px solid #ededed;
        border-radius: 8px;
        padding: 1.4rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s;
    }

    .homi-card:hover {
        border-color: #d4d4d4;
    }

    /* ================================================================
       BUTTONS — charcoal with subtle shadow (academic style)
       ================================================================ */
    .stButton > button {
        background-color: #36454F !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.84rem !important;
        transition: all 0.15s ease !important;
        box-shadow: 2px 2px 0px #1a1a1a !important;
    }

    .stButton > button:hover {
        background-color: #2a363e !important;
        transform: translate(-1px, -1px) !important;
        box-shadow: 3px 3px 0px #1a1a1a !important;
    }

    .stButton > button:active {
        transform: translate(1px, 1px) !important;
        box-shadow: 1px 1px 0px #1a1a1a !important;
    }

    /* Secondary */
    .stButton > button[kind="secondary"] {
        background-color: #fff !important;
        border: 1px solid #d4d4d4 !important;
        color: #555 !important;
        box-shadow: none !important;
    }

    .stButton > button[kind="secondary"]:hover {
        border-color: #36454F !important;
        color: #1a1a1a !important;
        background-color: #fafafa !important;
        box-shadow: none !important;
        transform: none !important;
    }

    /* ================================================================
       METRICS
       ================================================================ */
    [data-testid="stMetric"] {
        background: #fafafa;
        border: 1px solid #ededed;
        border-radius: 8px;
        padding: 1rem 1.1rem !important;
    }

    [data-testid="stMetricValue"] {
        font-family: 'Marcellus', serif !important;
        color: #1a1a1a !important;
        font-size: 1.5rem !important;
        font-weight: 400 !important;
    }

    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        color: #888 !important;
    }

    [data-testid="stMetricDelta"] {
        color: #555 !important;
    }

    /* ================================================================
       EXPANDERS
       ================================================================ */
    .streamlit-expanderHeader {
        background: #fafafa !important;
        border: 1px solid #ededed !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        color: #1a1a1a !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: #d4d4d4 !important;
    }

    details[data-testid="stExpander"] {
        border: 1px solid #ededed !important;
        border-radius: 6px !important;
        background: transparent !important;
    }

    details[data-testid="stExpander"] summary span {
        color: #1a1a1a !important;
    }

    /* ================================================================
       SIDEBAR — light gray
       ================================================================ */
    [data-testid="stSidebar"] {
        background-color: #f5f5f5 !important;
        border-right: 1px solid #ededed !important;
    }

    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label {
        color: #1a1a1a !important;
    }

    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #fff !important;
        border: 1px solid #e5e5e5 !important;
        color: #555 !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        text-align: left !important;
        padding: 0.55rem 0.85rem !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: #36454F !important;
        color: #1a1a1a !important;
        background-color: #fff !important;
        transform: none !important;
    }

    /* Sidebar primary (New Project) */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background-color: #36454F !important;
        border: none !important;
        color: #fff !important;
        font-weight: 600 !important;
        box-shadow: 2px 2px 0px #1a1a1a !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background-color: #2a363e !important;
        color: #fff !important;
        transform: translate(-1px, -1px) !important;
        box-shadow: 3px 3px 0px #1a1a1a !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #ededed !important;
        margin: 0.6rem 0 !important;
    }

    .sidebar-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #999;
        margin: 1rem 0 0.5rem;
    }

    /* ================================================================
       FILE UPLOADER
       ================================================================ */
    [data-testid="stFileUploader"] {
        background: #fafafa;
        border: 2px dashed #d4d4d4;
        border-radius: 8px;
        padding: 2rem;
        transition: border-color 0.2s;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #36454F;
    }

    [data-testid="stFileUploader"] * {
        color: #555 !important;
    }

    /* ================================================================
       FORM ELEMENTS
       ================================================================ */
    .stRadio > div {
        gap: 0.4rem;
    }

    .stRadio label span {
        font-weight: 500 !important;
        font-size: 0.84rem !important;
        color: #1a1a1a !important;
    }

    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 6px !important;
        border-color: #d4d4d4 !important;
        background: #fff !important;
        color: #1a1a1a !important;
        font-size: 0.84rem !important;
    }

    .stSelectbox > div > div:focus-within,
    .stNumberInput > div > div > input:focus,
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #36454F !important;
        box-shadow: 0 0 0 1px rgba(54, 69, 79, 0.15) !important;
    }

    /* Select dropdown text */
    .stSelectbox [data-baseweb="select"] span {
        color: #1a1a1a !important;
    }

    /* ================================================================
       TABS
       ================================================================ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: #fafafa;
        border-radius: 6px;
        padding: 3px;
        border: 1px solid #ededed;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 4px;
        color: #888;
        font-weight: 500;
        font-size: 0.82rem;
    }

    .stTabs [aria-selected="true"] {
        background: #36454F !important;
        color: #fff !important;
    }

    /* ================================================================
       SLIDER
       ================================================================ */
    .stSlider > div > div > div > div {
        background: #36454F !important;
    }

    .stSlider label {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #1a1a1a !important;
    }

    .stSlider [data-testid="stTickBarMin"],
    .stSlider [data-testid="stTickBarMax"] {
        color: #888 !important;
    }

    /* ================================================================
       PROGRESS BAR
       ================================================================ */
    .stProgress > div > div > div {
        background: #36454F !important;
        border-radius: 2px !important;
    }

    .stProgress > div > div {
        background: #ededed !important;
        border-radius: 2px !important;
    }

    /* ================================================================
       DIVIDERS — full-width light line (like the reference)
       ================================================================ */
    .homi-divider {
        height: 2px;
        background-color: #ededed;
        margin: 1.2rem 0;
        border: none;
    }

    hr {
        border: none !important;
        height: 2px !important;
        background-color: #ededed !important;
        margin: 1rem 0 !important;
    }

    /* ================================================================
       ALERTS
       ================================================================ */
    .info-box {
        background: #f0f4ff;
        border: 1px solid #c5d4f0;
        border-radius: 6px;
        padding: 0.9rem 1.1rem;
        margin: 0.8rem 0;
        color: #1a1a1a;
    }

    .success-box {
        background: #f0f7f0;
        border-color: #b8d8b8;
    }

    .warning-box {
        background: #fff8f0;
        border-color: #f0d8b8;
    }

    .error-box {
        background: #fef0f0;
        border-color: #f0b8b8;
    }

    [data-testid="stAlert"] {
        border-radius: 6px !important;
        font-size: 0.84rem !important;
    }

    /* ================================================================
       REVERT BANNER
       ================================================================ */
    .revert-banner {
        background: #fff8f0;
        border-left: 3px solid #e65100;
        padding: 10px 14px;
        margin-bottom: 12px;
        border-radius: 0 6px 6px 0;
        color: #1a1a1a;
    }

    .revert-banner strong {
        color: #e65100;
    }

    .revert-banner small {
        color: #888;
    }

    /* ================================================================
       IMAGE CARDS
       ================================================================ */
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
    }

    .image-card {
        position: relative;
        border: 1.5px solid #ededed;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.2s ease;
        background: #fff;
    }

    .image-card:hover {
        border-color: #36454F;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .image-card.selected {
        border-color: #36454F;
        box-shadow: 0 0 0 2px rgba(54, 69, 79, 0.15);
    }

    .score-badge {
        position: absolute;
        top: 6px;
        right: 6px;
        background: rgba(255, 255, 255, 0.92);
        color: #555;
        padding: 2px 8px;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        font-weight: 600;
        border: 1px solid #ededed;
    }

    .score-badge.high {
        color: #2e7d32;
        border-color: #b8d8b8;
        background: rgba(240, 247, 240, 0.95);
    }

    /* ================================================================
       LAYER TOGGLE
       ================================================================ */
    .layer-toggle {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        background: #fafafa;
        border: 1px solid #ededed;
        border-radius: 4px;
        margin-bottom: 4px;
        transition: border-color 0.2s;
        color: #1a1a1a;
    }

    .layer-toggle:hover {
        border-color: #d4d4d4;
    }

    .layer-color-swatch {
        width: 12px;
        height: 12px;
        border-radius: 2px;
        border: 1px solid rgba(0, 0, 0, 0.1);
    }

    /* ================================================================
       EXPLORATION TREE
       ================================================================ */
    .exploration-tree-container {
        background: #fafafa;
        border: 1px solid #ededed;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .tree-legend {
        display: flex;
        gap: 14px;
        margin-bottom: 10px;
        flex-wrap: wrap;
        justify-content: center;
    }

    .tree-legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 0.72rem;
        color: #888;
    }

    .tree-legend-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }

    .tree-legend-dot.pending { background: #d4d4d4; }
    .tree-legend-dot.running { background: #e65100; animation: tree-pulse 1.5s infinite; }
    .tree-legend-dot.complete { background: #2e7d32; }
    .tree-legend-dot.failed { background: #c62828; }

    .tree-stats {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        margin-top: 10px;
    }

    .tree-stat {
        background: #fff;
        border: 1px solid #ededed;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
    }

    .tree-stat-value {
        font-family: 'Marcellus', serif;
        font-size: 1.3rem;
        font-weight: 400;
        color: #1a1a1a;
    }

    .tree-stat-label {
        font-size: 0.62rem;
        color: #999;
        margin-top: 3px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ================================================================
       DOWNLOAD BUTTONS
       ================================================================ */
    [data-testid="stDownloadButton"] > button {
        background: #fff !important;
        border: 1px solid #d4d4d4 !important;
        color: #36454F !important;
        box-shadow: none !important;
        font-weight: 600 !important;
    }

    [data-testid="stDownloadButton"] > button:hover {
        border-color: #36454F !important;
        background: #fafafa !important;
        transform: none !important;
    }

    /* ================================================================
       SCROLLBAR
       ================================================================ */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: #d4d4d4;
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #bbb;
    }

    /* ================================================================
       ANIMATIONS
       ================================================================ */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes tree-pulse {
        0%, 100% {
            box-shadow: 0 0 0 0 rgba(230, 81, 0, 0.3);
        }
        50% {
            box-shadow: 0 0 0 5px rgba(230, 81, 0, 0);
        }
    }

    .fade-in {
        animation: fadeIn 0.25s ease-out;
    }

    /* ================================================================
       CAPTIONS
       ================================================================ */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-size: 0.74rem !important;
        color: #888 !important;
    }

    [data-testid="stTooltipIcon"] {
        color: #bbb !important;
    }

    /* ================================================================
       CHECKBOX / TOGGLE
       ================================================================ */
    .stCheckbox label span {
        color: #1a1a1a !important;
    }

    /* ================================================================
       SPINNER
       ================================================================ */
    .stSpinner > div > div {
        border-top-color: #36454F !important;
    }

    /* ================================================================
       RESPONSIVE
       ================================================================ */
    @media (max-width: 768px) {
        .step-name { display: none; }
        .step-circle { width: 24px; height: 24px; font-size: 0.62rem; }
        .step-connector { min-width: 10px; }
        .section-header h2 { font-size: 1.2rem !important; }
        .image-grid { grid-template-columns: repeat(2, 1fr); }
        .tree-stats { grid-template-columns: repeat(3, 1fr); }
    }

    @media (max-width: 480px) {
        .tree-stats { grid-template-columns: repeat(2, 1fr); }
        .step-progress { padding: 0.5rem 0; }
    }

    /* ================================================================
       LEGACY STEP INDICATOR CLASSES
       ================================================================ */
    .step-indicator { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 16px 0; }
    .step-dot { width: 12px; height: 12px; border-radius: 50%; background: #d4d4d4; }
    .step-dot.completed { background: #36454F; }
    .step-dot.active { background: #1a1a1a; box-shadow: 0 0 8px rgba(0,0,0,0.15); transform: scale(1.3); }
    .step-dot.viewing { background: #e65100; }
    .step-label { font-size: 0.7rem; color: #888; text-align: center; min-width: 50px; }
    .step-label.active { color: #1a1a1a; font-weight: 600; }
    .step-label.completed { color: #36454F; }
    .step-label.viewing { color: #e65100; font-weight: 600; }
</style>
"""


def inject_theme(st) -> None:
    """Inject the theme CSS into the Streamlit page."""
    st.markdown(get_theme_css(), unsafe_allow_html=True)


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_hero(st) -> None:
    """Render the HOMI brand mark."""
    st.markdown("""
    <div class="homi-brand">
        <h1>HOMI</h1>
        <div class="tagline">Photonic Multimodal Intelligence</div>
    </div>
    """, unsafe_allow_html=True)


def render_step_progress(st, viewing_step: float, highest_step: float = None, total_steps: int = 8) -> None:
    """Render the step progress strip."""
    if highest_step is None:
        highest_step = viewing_step

    step_names = [
        "Upload", "Select", "B&W", "Footprint",
        "Generate", "Results", "Explorer", "Simulate"
    ]

    display_viewing = int(viewing_step)
    display_highest = int(highest_step)
    is_viewing_past = display_viewing < display_highest

    html = '<div class="step-progress">'

    for i in range(1, total_steps + 1):
        if is_viewing_past and i == display_viewing:
            state = "viewing"
        elif i < display_highest:
            state = "completed"
        elif i == display_highest:
            state = "active"
        else:
            state = ""

        clickable = "clickable" if i < display_highest else ""
        name = step_names[i - 1] if i <= len(step_names) else f"{i}"
        inner = "&#10003;" if state == "completed" else str(i)

        html += f'''
        <div class="step-node">
            <div class="step-circle {state} {clickable}">{inner}</div>
            <div class="step-name {state}">{name}</div>
        </div>
        '''

        if i < total_steps:
            conn_class = "done" if i < highest_step else ""
            html += f'<div class="step-connector {conn_class}"></div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_step_indicator(st, viewing_step: float, highest_step: float = None, total_steps: int = 8) -> None:
    """Legacy wrapper."""
    render_step_progress(st, viewing_step, highest_step, total_steps)


def section_header(st, step_num, title: str, subtitle: str = "") -> None:
    """Render a clean section header."""
    sub_html = f'<div class="section-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="section-header">
        <h2>{title}</h2>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def divider(st) -> None:
    """Render a subtle divider."""
    st.markdown('<div class="homi-divider"></div>', unsafe_allow_html=True)


def card(st, content_func, **kwargs) -> None:
    """Wrap content in a styled card container."""
    st.markdown('<div class="homi-card">', unsafe_allow_html=True)
    content_func(**kwargs)
    st.markdown('</div>', unsafe_allow_html=True)


def score_badge(score: int) -> str:
    """Generate HTML for a score badge."""
    badge_class = "high" if score >= 7 else ""
    return f'<span class="score-badge {badge_class}">{score}/10</span>'


def layer_toggle_html(layer: Tuple[int, int], visible: bool = True) -> str:
    """Generate HTML for a layer toggle control."""
    colors = get_layer_color(layer)
    checked = "checked" if visible else ""
    return f'''
    <div class="layer-toggle">
        <input type="checkbox" {checked}>
        <div class="layer-color-swatch" style="background: {colors['face']};"></div>
        <span>{colors['name']}</span>
    </div>
    '''
