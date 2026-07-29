import gdsfactory as gf

# Device parameters
length = 2.35
width = 0.85
layer = (1, 0)

@gf.cell
def device():
    c = gf.Component()
    
    # The shape appears to be a cross with rounded/elliptical arms and rectangular stubs
    # Looking at the silhouette, it has 4 folded lobes meeting at center with straight extensions
    
    # Create the cross shape using the cross primitive with appropriate dimensions
    # The footprint is 4.7 x 4.7, so half is 2.35
    # The cross should have length matching the full extent
    
    # Using cross primitive with length=4.7, width=0.85 to get the right footprint
    cross = gf.components.cross(length=4.7, width=width, layer=layer)
    c << cross
    
    return c

if __name__ == "__main__":
    dev = device()
    dev.write_gds("device.gds")