import kfactory as kf
import kfactory.geo as geo
import kfactory.routing as routing


@kf.cell
def flower_cross(petal_length: float = 3.0, petal_width: float = 2.0, stem_length: float = 0.7, stem_width: float = 0.7):
    """
    Creates a flower-like cross geometry using GDSFactory primitives.
    """
    c = kf.KCell("flower_cross")

    # Create the petal shape (modified ellipse)
    petal = c << kf.geo.ellipse(radii=(petal_length / 2, petal_width / 2), layer=(1, 0))
    petal.rotate(90)

    # Create the stem
    stem = c << kf.geo.rectangle(size=(stem_length, stem_width), layer=(1, 0), centered=True)
    stem.move((0, petal_length / 2 + stem_length / 2))

    petal_with_stem = kf.geo.boolean(petal.kcell, stem.kcell, operation="or", layer=(1, 0))
    petal_with_stem_ref = c << petal_with_stem


    petal_1 = c << petal_with_stem
    petal_2 = c << petal_with_stem
    petal_3 = c << petal_with_stem
    petal_4 = c << petal_with_stem

    petal_2.rotate(90)
    petal_3.rotate(180)
    petal_4.rotate(270)

    # Create the cross shape by combining the petals
    cross = kf.geo.boolean(petal_1.kcell, petal_2.kcell, operation="or", layer=(1, 0))
    cross = kf.geo.boolean(cross, petal_3.kcell, operation="or", layer=(1, 0))
    cross = kf.geo.boolean(cross, petal_4.kcell, operation="or", layer=(1, 0))

    c.add(cross)

    return c


if __name__ == "__main__":
    flower = flower_cross()
    flower.show(show_ports=False)  # Opens KLayout