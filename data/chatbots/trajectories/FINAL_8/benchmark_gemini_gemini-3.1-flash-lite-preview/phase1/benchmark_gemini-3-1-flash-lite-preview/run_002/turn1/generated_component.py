import gdsfactory as gf
import numpy as np

@gf.cell
def tapered_waveguide_array(
    n_lines: int = 5,
    line_width: float = 0.4,
    spacing: float = 0.2,
    total_length: float = 120.0,
    min_length: float = 80.0
):
    """
    Creates the tapered waveguide array geometry matching the device footprint.
    """
    c = gf.Component("tapered_array")
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=line_width, layer=(1, 0))
    
    # Calculate spacing (pitch)
    pitch = line_width + spacing
    
    # We want a symmetrical "bell" shape.
    # We create n_lines waveguides, varying their length.
    # Indices: 0 to n_lines-1. 
    # Center index is (n_lines - 1) / 2
    indices = np.arange(n_lines)
    center_idx = (n_lines - 1) / 2
    
    # Use a parabolic curve to determine length (max at center, min at edges)
    # This creates the tapered transition visual seen in the reference image.
    normalized_curve = (indices - center_idx) ** 2
    max_curve = np.max(normalized_curve)
    
    # Avoid division by zero if n_lines = 1
    if max_curve == 0:
        lengths = [total_length]
    else:
        # Calculate lengths
        lengths = total_length - (normalized_curve / max_curve) * (total_length - min_length)
    
    # Add waveguides
    for i, length in enumerate(lengths):
        # Calculate Y position (centering the array at y=0)
        y_pos = (i - center_idx) * pitch
        
        # Create straight waveguide
        wg = gf.components.straight(length=length, cross_section=xs)
        
        # Add reference to component
        ref = c << wg
        
        # Position the waveguide centered at x=0
        ref.movex(-length / 2)
        ref.movey(y_pos)
        
    return c

# 1. Generate the component
device = tapered_waveguide_array()

# 2. Explicitly write the GDS file to disk
file_path = "tapered_waveguide_array.gds"
device.write_gds(file_path)

print(f"Success! GDS file produced at: {file_path}")
# Optional: device.show() # Uncomment to view in KLayout