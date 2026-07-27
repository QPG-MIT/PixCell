"""
WebGL Polygon Viewer for Weber Explorers

Provides a high-performance WebGL-based polygon renderer using
Streamlit components. Replaces matplotlib for faster visualization.
"""

import json
import streamlit.components.v1 as components
from typing import Dict, List, Tuple, Optional, Any
import gdsfactory as gf


def is_available() -> bool:
    """Check if WebGL viewer dependencies are available."""
    try:
        import streamlit.components.v1
        return True
    except ImportError:
        return False


def extract_polygons_json(
    component: gf.Component,
    layer_colors: Optional[Dict[Tuple[int, int], Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Extract polygons from a GDSFactory component as JSON-serializable data.

    Args:
        component: GDSFactory component
        layer_colors: Optional mapping of layer tuples to color dicts

    Returns:
        Dict with 'polygons', 'bounds', and 'layers' keys
    """
    default_colors = {
        (1, 0): {'face': '#2E86AB', 'edge': '#1B4965', 'name': 'Layer 1'},
        (2, 0): {'face': '#F4A261', 'edge': '#E76F51', 'name': 'Layer 2'},
        (3, 0): {'face': '#2ECC71', 'edge': '#27AE60', 'name': 'Layer 3'},
        (4, 0): {'face': '#9B59B6', 'edge': '#8E44AD', 'name': 'Layer 4'},
        (5, 0): {'face': '#E74C3C', 'edge': '#C0392B', 'name': 'Layer 5'},
    }

    if layer_colors is None:
        layer_colors = default_colors

    polygons = []
    layers_used = {}

    try:
        polys = component.get_polygons()
        if isinstance(polys, dict):
            for layer, poly_list in polys.items():
                # Normalize layer key
                if isinstance(layer, tuple):
                    layer_tuple = layer
                elif isinstance(layer, int):
                    layer_tuple = (layer, 0)
                else:
                    layer_tuple = (1, 0)

                layer_key = f"{layer_tuple[0]}_{layer_tuple[1]}"
                colors = layer_colors.get(layer_tuple, {'face': '#888888', 'edge': '#666666', 'name': f'Layer {layer_tuple}'})
                layers_used[layer_key] = colors

                for poly in poly_list:
                    # Extract hull (outer boundary)
                    hull_pts = []
                    for pt in poly.each_point_hull():
                        hull_pts.append([pt.x / 1000, pt.y / 1000])  # nm to um

                    if hull_pts:
                        poly_data = {
                            'layer': layer_key,
                            'hull': hull_pts,
                            'holes': []
                        }

                        # Extract holes
                        try:
                            num_holes = poly.holes()
                            for hole_idx in range(num_holes):
                                hole_pts = []
                                for pt in poly.each_point_hole(hole_idx):
                                    hole_pts.append([pt.x / 1000, pt.y / 1000])
                                if hole_pts:
                                    poly_data['holes'].append(hole_pts)
                        except Exception:
                            pass

                        polygons.append(poly_data)
    except Exception as e:
        pass

    # Get bounds
    try:
        bbox = component.bbox()
        try:
            xmin, ymin = bbox[0]
            xmax, ymax = bbox[1]
        except TypeError:
            xmin, ymin = bbox.left, bbox.bottom
            xmax, ymax = bbox.right, bbox.top
        bounds = {
            'xmin': float(xmin),
            'ymin': float(ymin),
            'xmax': float(xmax),
            'ymax': float(ymax)
        }
    except Exception:
        bounds = {'xmin': -5, 'ymin': -5, 'xmax': 5, 'ymax': 5}

    return {
        'polygons': polygons,
        'bounds': bounds,
        'layers': {k: {'fill': v['face'], 'stroke': v.get('edge', v['face']), 'name': v.get('name', k)}
                   for k, v in layers_used.items()}
    }


def render_webgl_viewer(
    component: gf.Component,
    layer_colors: Optional[Dict[Tuple[int, int], Dict[str, str]]] = None,
    height: int = 600,
    show_grid: bool = True,
    show_legend: bool = True
) -> None:
    """
    Render a GDSFactory component using WebGL-accelerated canvas.

    Args:
        component: GDSFactory component to render
        layer_colors: Optional layer color mapping
        height: Canvas height in pixels
        show_grid: Whether to show grid lines
        show_legend: Whether to show layer legend
    """
    # Extract polygon data
    data = extract_polygons_json(component, layer_colors)

    # Create the HTML/JS viewer
    html_content = _create_webgl_html(data, height, show_grid, show_legend)

    # Render using Streamlit components
    components.html(html_content, height=height + 50)


def _create_webgl_html(
    data: Dict[str, Any],
    height: int,
    show_grid: bool,
    show_legend: bool
) -> str:
    """Generate the HTML/JS for the WebGL viewer."""

    data_json = json.dumps(data)

    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}

        .container {{
            position: relative;
            width: 100%;
            height: {height}px;
            background: #f8f9fa;
            border-radius: 8px;
            overflow: hidden;
        }}

        #canvas {{
            width: 100%;
            height: 100%;
            cursor: grab;
        }}

        #canvas:active {{
            cursor: grabbing;
        }}

        .legend {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.95);
            padding: 10px 14px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-size: 12px;
            max-width: 200px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            margin: 4px 0;
        }}

        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            margin-right: 8px;
            border: 1px solid rgba(0,0,0,0.2);
        }}

        .info {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            color: #666;
        }}

        .controls {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            display: flex;
            gap: 6px;
        }}

        .controls button {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 6px 10px;
            cursor: pointer;
            font-size: 14px;
        }}

        .controls button:hover {{
            background: #f0f0f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <canvas id="canvas"></canvas>
        <div class="legend" id="legend" style="display: {'block' if show_legend else 'none'}"></div>
        <div class="info" id="info">Scroll to zoom, drag to pan</div>
        <div class="controls">
            <button onclick="resetView()" title="Reset view">⟲</button>
            <button onclick="zoomIn()" title="Zoom in">+</button>
            <button onclick="zoomOut()" title="Zoom out">−</button>
        </div>
    </div>

    <script>
        const data = {data_json};
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const container = canvas.parentElement;

        // High-DPI support
        const dpr = window.devicePixelRatio || 1;

        // View state
        let viewState = {{
            offsetX: 0,
            offsetY: 0,
            scale: 1,
            isDragging: false,
            lastX: 0,
            lastY: 0
        }};

        // Resize canvas
        function resizeCanvas() {{
            const rect = container.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            canvas.style.width = rect.width + 'px';
            canvas.style.height = rect.height + 'px';
            ctx.scale(dpr, dpr);
            render();
        }}

        // Initialize view to fit bounds
        function initView() {{
            const bounds = data.bounds;
            const rect = container.getBoundingClientRect();
            const padding = 40;

            const dataWidth = bounds.xmax - bounds.xmin;
            const dataHeight = bounds.ymax - bounds.ymin;

            const scaleX = (rect.width - padding * 2) / dataWidth;
            const scaleY = (rect.height - padding * 2) / dataHeight;
            viewState.scale = Math.min(scaleX, scaleY);

            // Center the view
            const centerX = (bounds.xmin + bounds.xmax) / 2;
            const centerY = (bounds.ymin + bounds.ymax) / 2;

            viewState.offsetX = rect.width / 2 - centerX * viewState.scale;
            viewState.offsetY = rect.height / 2 + centerY * viewState.scale; // Y is flipped
        }}

        // Transform data coordinates to screen coordinates
        function toScreen(x, y) {{
            return {{
                x: x * viewState.scale + viewState.offsetX,
                y: -y * viewState.scale + viewState.offsetY  // Flip Y
            }};
        }}

        // Transform screen coordinates to data coordinates
        function toData(sx, sy) {{
            return {{
                x: (sx - viewState.offsetX) / viewState.scale,
                y: -(sy - viewState.offsetY) / viewState.scale
            }};
        }}

        // Render the scene
        function render() {{
            const rect = container.getBoundingClientRect();
            ctx.clearRect(0, 0, rect.width, rect.height);

            // Draw grid
            if ({'true' if show_grid else 'false'}) {{
                drawGrid(rect);
            }}

            // Draw polygons
            for (const poly of data.polygons) {{
                const layer = data.layers[poly.layer] || {{ fill: '#888888', stroke: '#666666' }};
                drawPolygon(poly, layer);
            }}

            // Update info
            const bounds = data.bounds;
            const w = (bounds.xmax - bounds.xmin).toFixed(2);
            const h = (bounds.ymax - bounds.ymin).toFixed(2);
            document.getElementById('info').textContent =
                `Size: ${{w}} × ${{h}} μm | Zoom: ${{(viewState.scale * 100).toFixed(0)}}%`;
        }}

        // Draw grid
        function drawGrid(rect) {{
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
            ctx.lineWidth = 1;

            // Determine grid spacing based on zoom
            let gridSize = 1; // 1 μm
            if (viewState.scale < 20) gridSize = 5;
            if (viewState.scale < 5) gridSize = 10;
            if (viewState.scale > 100) gridSize = 0.1;

            const topLeft = toData(0, 0);
            const bottomRight = toData(rect.width, rect.height);

            const startX = Math.floor(topLeft.x / gridSize) * gridSize;
            const startY = Math.floor(bottomRight.y / gridSize) * gridSize;
            const endX = Math.ceil(bottomRight.x / gridSize) * gridSize;
            const endY = Math.ceil(topLeft.y / gridSize) * gridSize;

            ctx.beginPath();
            for (let x = startX; x <= endX; x += gridSize) {{
                const s = toScreen(x, 0);
                ctx.moveTo(s.x, 0);
                ctx.lineTo(s.x, rect.height);
            }}
            for (let y = startY; y <= endY; y += gridSize) {{
                const s = toScreen(0, y);
                ctx.moveTo(0, s.y);
                ctx.lineTo(rect.width, s.y);
            }}
            ctx.stroke();

            // Draw axis
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
            ctx.lineWidth = 1.5;
            const origin = toScreen(0, 0);
            ctx.beginPath();
            ctx.moveTo(0, origin.y);
            ctx.lineTo(rect.width, origin.y);
            ctx.moveTo(origin.x, 0);
            ctx.lineTo(origin.x, rect.height);
            ctx.stroke();
        }}

        // Draw a polygon with holes
        function drawPolygon(poly, layer) {{
            ctx.fillStyle = layer.fill;
            ctx.strokeStyle = layer.stroke;
            ctx.lineWidth = 1.5;
            ctx.globalAlpha = 0.85;

            ctx.beginPath();

            // Draw outer hull
            const hull = poly.hull;
            if (hull.length > 0) {{
                const start = toScreen(hull[0][0], hull[0][1]);
                ctx.moveTo(start.x, start.y);
                for (let i = 1; i < hull.length; i++) {{
                    const pt = toScreen(hull[i][0], hull[i][1]);
                    ctx.lineTo(pt.x, pt.y);
                }}
                ctx.closePath();
            }}

            // Draw holes (counter-clockwise for proper fill rule)
            for (const hole of poly.holes) {{
                if (hole.length > 0) {{
                    const start = toScreen(hole[0][0], hole[0][1]);
                    ctx.moveTo(start.x, start.y);
                    // Draw in reverse for hole
                    for (let i = hole.length - 1; i >= 0; i--) {{
                        const pt = toScreen(hole[i][0], hole[i][1]);
                        ctx.lineTo(pt.x, pt.y);
                    }}
                    ctx.closePath();
                }}
            }}

            ctx.fill('evenodd');
            ctx.globalAlpha = 1;
            ctx.stroke();

            // Draw hole outlines in red
            for (const hole of poly.holes) {{
                if (hole.length > 0) {{
                    ctx.strokeStyle = '#FF6B6B';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    const start = toScreen(hole[0][0], hole[0][1]);
                    ctx.moveTo(start.x, start.y);
                    for (let i = 1; i < hole.length; i++) {{
                        const pt = toScreen(hole[i][0], hole[i][1]);
                        ctx.lineTo(pt.x, pt.y);
                    }}
                    ctx.closePath();
                    ctx.stroke();
                }}
            }}
        }}

        // Build legend
        function buildLegend() {{
            const legend = document.getElementById('legend');
            let html = '';
            for (const [key, layer] of Object.entries(data.layers)) {{
                html += `
                    <div class="legend-item">
                        <div class="legend-color" style="background: ${{layer.fill}}; border-color: ${{layer.stroke}}"></div>
                        <span>${{layer.name}}</span>
                    </div>
                `;
            }}
            legend.innerHTML = html;
        }}

        // Mouse/touch handlers
        canvas.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = viewState.scale * zoomFactor;

            // Zoom toward mouse position
            viewState.offsetX = mouseX - (mouseX - viewState.offsetX) * zoomFactor;
            viewState.offsetY = mouseY - (mouseY - viewState.offsetY) * zoomFactor;
            viewState.scale = newScale;

            render();
        }}, {{ passive: false }});

        canvas.addEventListener('mousedown', (e) => {{
            viewState.isDragging = true;
            viewState.lastX = e.clientX;
            viewState.lastY = e.clientY;
            canvas.style.cursor = 'grabbing';
        }});

        canvas.addEventListener('mousemove', (e) => {{
            if (viewState.isDragging) {{
                const dx = e.clientX - viewState.lastX;
                const dy = e.clientY - viewState.lastY;
                viewState.offsetX += dx;
                viewState.offsetY += dy;
                viewState.lastX = e.clientX;
                viewState.lastY = e.clientY;
                render();
            }}
        }});

        canvas.addEventListener('mouseup', () => {{
            viewState.isDragging = false;
            canvas.style.cursor = 'grab';
        }});

        canvas.addEventListener('mouseleave', () => {{
            viewState.isDragging = false;
            canvas.style.cursor = 'grab';
        }});

        // Touch support
        let lastTouchDistance = 0;

        canvas.addEventListener('touchstart', (e) => {{
            if (e.touches.length === 1) {{
                viewState.isDragging = true;
                viewState.lastX = e.touches[0].clientX;
                viewState.lastY = e.touches[0].clientY;
            }} else if (e.touches.length === 2) {{
                lastTouchDistance = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
            }}
        }}, {{ passive: true }});

        canvas.addEventListener('touchmove', (e) => {{
            e.preventDefault();
            if (e.touches.length === 1 && viewState.isDragging) {{
                const dx = e.touches[0].clientX - viewState.lastX;
                const dy = e.touches[0].clientY - viewState.lastY;
                viewState.offsetX += dx;
                viewState.offsetY += dy;
                viewState.lastX = e.touches[0].clientX;
                viewState.lastY = e.touches[0].clientY;
                render();
            }} else if (e.touches.length === 2) {{
                const distance = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                const scale = distance / lastTouchDistance;
                viewState.scale *= scale;
                lastTouchDistance = distance;
                render();
            }}
        }}, {{ passive: false }});

        canvas.addEventListener('touchend', () => {{
            viewState.isDragging = false;
        }});

        // Control functions
        function resetView() {{
            initView();
            render();
        }}

        function zoomIn() {{
            const rect = container.getBoundingClientRect();
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const zoomFactor = 1.3;

            viewState.offsetX = centerX - (centerX - viewState.offsetX) * zoomFactor;
            viewState.offsetY = centerY - (centerY - viewState.offsetY) * zoomFactor;
            viewState.scale *= zoomFactor;
            render();
        }}

        function zoomOut() {{
            const rect = container.getBoundingClientRect();
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const zoomFactor = 0.77;

            viewState.offsetX = centerX - (centerX - viewState.offsetX) * zoomFactor;
            viewState.offsetY = centerY - (centerY - viewState.offsetY) * zoomFactor;
            viewState.scale *= zoomFactor;
            render();
        }}

        // Initialize
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        initView();
        buildLegend();
        render();
    </script>
</body>
</html>
'''
