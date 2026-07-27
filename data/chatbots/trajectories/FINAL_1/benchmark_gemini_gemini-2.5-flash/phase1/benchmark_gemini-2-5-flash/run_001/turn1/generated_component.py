import gdsfactory as gf
# Corrected import: 'Path' is not in gdsfactory.typings. 
# For type hinting GDSFactory Path objects, use 'gf.Path' directly.
from gdsfactory.typings import CrossSectionSpec 

@gf.cell
def trident_splitter() -> gf.Component:
    """
    Recreates the trident splitter geometry from the provided image.

    The geometry consists of three waveguide-like structures:
    - A central waveguide that tapers from wide to narrow.
    - Two outer waveguides that start straight, then their inner edges taper
      inward while the outer edges remain relatively stable, and finally flare
      outward.

    The device is constructed using GDSFactory's path extrusion and boolean operations.
    The total footprint is 40.0 x 1.7 um.
    """
    c = gf.Component("trident_splitter")
    
    # Define a default cross-section for layer information.
    # The `width` here is a placeholder as it will be overridden by functions.
    # The `layer` (1,0) is used consistently for all generated geometry.
    xs_default_layer = gf.cross_section.cross_section(width=0.5, layer=(1, 0)) 
    
    # Device footprint constraints
    total_length = 40.0
    total_height = 1.7
    
    # --- Parameters for initial (left-side at x=0) dimensions ---
    wg_outer_width_left = 0.4 # Width of top/bottom outer waveguides at the input
    wg_center_width_left = 0.2 # Width of the central waveguide at the input
    
    # Calculate the initial gap between central and outer waveguides
    # total_height = 2 * wg_outer_width_left + 2 * gap_left + wg_center_width_left
    gap_left = (total_height - 2 * wg_outer_width_left - wg_center_width_left) / 2 # = 0.35 um

    # --- Parameters for feature control points and dimensions along x-axis ---
    x_split_start = 10.0 # X-coordinate where outer WGs start to transition/taper
    x_curve_start = 25.0 # X-coordinate where the outer WGs begin their dominant outward curve
    
    width_end_center = 0.01 # Final width of the central waveguide (tapers almost to a point)
    width_outer_end = 0.25 # Estimated final width of outer waveguides at the output
    
    # --- 1. Central Waveguide Construction ---
    # Path is a simple straight line along the x-axis.
    path_center: gf.Path = gf.path.straight(length=total_length) # Corrected type hint
    
    # The cross-section for the central waveguide has a width that tapers with `t` (normalized path parameter).
    # The `offset` is 0 because the path is already the centerline of the waveguide.
    xs_center_taper: CrossSectionSpec = xs_default_layer.copy(
        width=lambda t: wg_center_width_left * (1 - t) + width_end_center * t,
        offset=0 # Fixed offset for the centerline of this CrossSection from its own path
    )
    wg_center = c << gf.path.extrude(path_center, xs_center_taper)
    
    # --- 2. Top Outer Waveguide Construction ---
    # For the outer waveguides, the path is defined as their *bottom edge*.
    # The cross-section's offset will then place its centerline (and thus define its top edge) above this path.
    
    # Calculate Y-coordinates for the control points of the top outer waveguide's bottom edge.
    y_bot_edge_outer_start = wg_center_width_left / 2 + gap_left # Initial y-position for the bottom edge of the top outer WG
    
    # Determine the Y-coordinate for the inner curve point (at x_curve_start).
    # This point ensures the gap between the central and outer waveguides is maintained/controlled.
    t_at_x_curve_start = x_curve_start / total_length 
    central_wg_width_at_curve_start = wg_center_width_left * (1 - t_at_x_curve_start) + width_end_center * t_at_x_curve_start
    central_wg_top_edge_y_at_curve_start = central_wg_width_at_curve_start / 2 # Top edge of central WG at this x-coord
    
    min_gap_at_curve = 0.1 # Assumed minimum gap between central and outer waveguides at this point
    y_bot_edge_outer_mid = central_wg_top_edge_y_at_curve_start + min_gap_at_curve
    
    # Final Y-coordinate for the bottom edge of the top outer waveguide (at x=total_length).
    # This ensures the overall device fits the total_height.
    y_bot_edge_outer_end = total_height / 2 - width_outer_end 
    
    # Define the control points for the bottom edge path of the top outer waveguide.
    path_top_outer_bottom_edge_points = [
        (0, y_bot_edge_outer_start),
        (x_split_start, y_bot_edge_outer_start),
        (x_curve_start, y_bot_edge_outer_mid),
        (total_length, y_bot_edge_outer_end)
    ]
    # Use gf.path.smooth to create a continuous, curved path through these points.
    path_top_outer_bottom_edge: gf.Path = gf.path.smooth(path_top_outer_bottom_edge_points, radius=5) # Corrected type hint
    
    # Define a function to generate a CrossSection object for each `t` along the path.
    # This allows both `width` and `offset` of the cross-section to vary along the path.
    def get_xs_top_outer_at_t(t: float) -> gf.CrossSection:
        x = t * total_length
        current_width: float
        if x <= x_split_start:
            current_width = wg_outer_width_left # Initial constant width
        elif x <= x_curve_start:
            # Linear taper of width in the transition region
            t_rel = (x - x_split_start) / (x_curve_start - x_split_start)
            current_width = wg_outer_width_left * (1 - t_rel) + width_outer_end * t_rel
        else:
            current_width = width_outer_end # Constant width in the curved output section
            
        # The offset for the cross-section is relative to the `path_top_outer_bottom_edge`.
        # Since this path represents the bottom edge of the waveguide, the centerline (offset)
        # needs to be `current_width / 2` above the path.
        current_offset = current_width / 2 
        
        # Return a new CrossSection object with the calculated width and offset for this `t`.
        return gf.cross_section.cross_section(
            width=current_width, 
            offset=current_offset,
            layer=xs_default_layer.layer,
            # Ensure other cross-section properties (if any) are carried over
            port_names=xs_default_layer.port_names,
            port_types=xs_default_layer.port_types,
            sections=xs_default_layer.sections 
        )
    
    # Extrude the path using the dynamically generated cross-section.
    wg_top_outer = c << gf.path.extrude(path_top_outer_bottom_edge, get_xs_top_outer_at_t)
    
    # --- 3. Bottom Outer Waveguide Construction ---
    # Create the bottom outer waveguide by extruding the same path and cross-section,
    # then mirroring the resulting component across the x-axis.
    wg_bot_outer_comp = gf.path.extrude(path_top_outer_bottom_edge, get_xs_top_outer_at_t)
    wg_bot_outer_ref = c << wg_bot_outer_comp
    wg_bot_outer_ref.mirror((0,0), (1,0)) # Mirror across the x-axis (y=0)
    
    # --- Combine all three components into a single GDS layer using Boolean OR operations ---
    # `gf.path.extrude` returns a Component, which can be directly used in boolean operations.
    final_shape = gf.boolean(wg_center, wg_top_outer, operation="or", layer=xs_default_layer.layer)
    final_shape = gf.boolean(final_shape, wg_bot_outer_ref, operation="or", layer=xs_default_layer.layer)
    
    c.add_ref(final_shape) # Add the final combined shape to the main component.
    
    # --- Add Ports (conceptual inputs/outputs for the overall device) ---
    # These ports are defined for the entire `trident_splitter` component, not for internal connections.
    
    # Input port for the central waveguide (at x=0, y=0)
    c.add_port("o1_center", center=(0, 0), width=wg_center_width_left, orientation=180, cross_section=xs_default_layer)
    
    # Input ports for the outer waveguides (at x=0)
    c.add_port("o1_top", center=(0, y_bot_edge_outer_start + wg_outer_width_left/2), width=wg_outer_width_left, orientation=180, cross_section=xs_default_layer)
    c.add_port("o1_bot", center=(0, -(y_bot_edge_outer_start + wg_outer_width_left/2)), width=wg_outer_width_left, orientation=180, cross_section=xs_default_layer)

    # Output ports (at x=total_length)
    y_top_outer_output_center = y_bot_edge_outer_end + width_outer_end/2 
    c.add_port("o2_top", center=(total_length, y_top_outer_output_center), width=width_outer_end, orientation=0, cross_section=xs_default_layer)
    y_bot_outer_output_center = -(y_bot_edge_outer_end + width_outer_end/2)
    c.add_port("o2_bot", center=(total_length, y_bot_outer_output_center), width=width_outer_end, orientation=0, cross_section=xs_default_layer)

    return c

if __name__ == "__main__":
    c = trident_splitter()
    c.show() # Display the generated GDS in KLayout or similar viewer
    # c.write_gds("trident_splitter.gds") # Uncomment to save the GDS file