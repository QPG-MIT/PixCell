import gdsfactory as gf

@gf.cell
def tapered_device():
    """
    Constructs the tapered device geometry by composing three taper primitives 
    and performing a boolean union to merge them into a single polygon structure.
    """
    c = gf.Component()

    # Define common dimensions
    length = 40.0
    
    # 1. Create the three taper primitives
    # Center section: transitions from 0.2um to 0.4um
    center_taper = gf.components.taper(length=length, width1=0.2, width2=0.4)
    
    # Outer sections: transition from 0.1um to 0.6um
    # We create two instances
    top_taper = gf.components.taper(length=length, width1=0.1, width2=0.6)
    bottom_taper = gf.components.taper(length=length, width1=0.1, width2=0.6)

    # 2. Position the tapers
    # The center_taper stays at y=0.
    # We shift the top and bottom tapers to align them vertically.
    # An offset of 0.5um provides spacing for the 0.6um wide ends (total height ~1.6um).
    top_ref = c << top_taper
    top_ref.movey(0.5)
    
    bottom_ref = c << bottom_taper
    bottom_ref.movey(-0.5)
    
    center_ref = c << center_taper

    # 3. Boolean Union
    # To satisfy the requirement of composing with boolean operations, 
    # we union the three components into a single geometric layer.
    
    # First, merge top and bottom
    mid_component = gf.boolean(top_ref, bottom_ref, operation="or", layer=(1, 0))
    
    # Then, merge the result with the center
    final_device = gf.boolean(mid_component, center_ref, operation="or", layer=(1, 0))
    
    return final_device

# Create the device and save
device = tapered_device()
device.write_gds("tapered_device.gds")

# Preview the component
if __name__ == "__main__":
    device.show()