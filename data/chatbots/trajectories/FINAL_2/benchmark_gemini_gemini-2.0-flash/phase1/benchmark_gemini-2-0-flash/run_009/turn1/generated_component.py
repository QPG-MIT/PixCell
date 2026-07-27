import gdsfactory as gf
from gdsfactory.components import rectangle


@gf.cell
def my_component():
    c = gf.Component("my_component")

    # Base rectangle
    rect = c << rectangle(size=(20, 8))  # Adjust size to match image proportions

    # Bottom rectangle
    bottom_rect = c << rectangle(size=(2, 2)) # Adjust size to match image proportions
    bottom_rect.movey(-5) #Adjust offset to match image proportions
    bottom_rect.movex(9)  #Move bottom rectangle to centered position below main rectangle

    # Top rectangles
    top_rects = []
    for i in range(4):
        top_rect = c << rectangle(size=(1.5, 4))  # Adjust size to match image proportions
        top_rect.movey(4) #Adjust offset to match image proportions
        top_rect.movex(i * 4 - 6)  # Distribute rectangles across the top
        top_rects.append(top_rect)

    return c


if __name__ == "__main__":
    c = my_component()
    filename = "my_component.gds"
    c.write_gds(filename=filename)
    print(f"GDS file saved to {filename}")

    # Optionally, display the component
    c.show()