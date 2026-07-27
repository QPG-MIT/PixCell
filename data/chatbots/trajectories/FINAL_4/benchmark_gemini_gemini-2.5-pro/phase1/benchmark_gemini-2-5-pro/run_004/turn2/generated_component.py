import gdsfactory as gf
import numpy as np

@gf.cell
def create_tapered_coupler():
    """
    Creates a tapered coupler device resembling a biconvex lens with a
    biconcave gap, using boolean operations on circular primitives.
    
    This version corrects the missing 'layer' argument in the boolean calls.
    """
    # Footprint parameters from the original problem statement
    device_width = 18.0
    device_height = 3.0
    
    # Define the GDS layer for the final geometry
    target_layer = (1, 0)
    
    # Assume a reasonable gap at the ends based on visual inspection.
    # This parameter controls the thickness of the waveguides at the ends.
    gap_at_ends = 1.0

    # --- 1. Define and position primitives for the outer boundary ---
    h_outer = device_height / 2.0
    w_outer = device_width
    R_outer = (h_outer**2 + (w_outer / 2.0)**2) / (2 * h_outer)
    y_center_outer = R_outer - h_outer
    
    # Create the primitive shape once
    outer_circle_primitive = gf.components.circle(radius=R_outer, layer=target_layer)

    # Create a new component for the top outer circle and move its reference
    comp_outer_top = gf.Component()
    ref_ot = comp_outer_top << outer_circle_primitive
    ref_ot.movey(y_center_outer)
    
    # Create a new component for the bottom outer circle and move its reference
    comp_outer_bottom = gf.Component()
    ref_ob = comp_outer_bottom << outer_circle_primitive
    ref_ob.movey(-y_center_outer)
    
    # Intersect the positioned components to create the outer lens shape
    # FIX: Added the required 'layer' argument
    outer_lens = gf.boolean(
        comp_outer_top, comp_outer_bottom, operation="and", layer=target_layer
    )

    # --- 2. Define and position primitives for the inner boundary ---
    x_end = device_width / 2.0
    y_end = gap_at_ends / 2.0
    y_center_inner = (x_end**2 + y_end**2) / (2 * y_end)
    R_inner = y_center_inner
    
    # Create the primitive shape once
    inner_circle_primitive = gf.components.circle(radius=R_inner, layer=target_layer)

    # Create a new component for the top inner circle and move its reference
    comp_inner_top = gf.Component()
    ref_it = comp_inner_top << inner_circle_primitive
    ref_it.movey(y_center_inner)

    # Create a new component for the bottom inner circle and move its reference
    comp_inner_bottom = gf.Component()
    ref_ib = comp_inner_bottom << inner_circle_primitive
    ref_ib.movey(-y_center_inner)

    # --- 3. Perform the final boolean subtractions ---
    # First, subtract the top inner shape from the lens
    # FIX: Added the required 'layer' argument
    temp_component = gf.boolean(
        outer_lens, comp_inner_top, operation="not", layer=target_layer
    )
    
    # Then, subtract the bottom inner shape from the result
    # FIX: Added the required 'layer' argument
    final_device = gf.boolean(
        temp_component, comp_inner_bottom, operation="not", layer=target_layer
    )

    # Create the final component cell and add the resulting geometry to it
    c = gf.Component("tapered_coupler_final")
    c.add_ref(final_device)
    
    return c


if __name__ == "__main__":
    # Create an instance of the component
    device = create_tapered_coupler()
    
    # Write the component to a GDS file
    device.write_gds("tapered_coupler.gds")
    
    print("Successfully generated tapered_coupler.gds")
    # To view the component, uncomment the following line:
    # device.show()