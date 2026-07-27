"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

width_mmi = 2.5
length_mmi = 5.5
length_taper = 10.0
width_taper = 1.0
gap_mmi = 0.25

c = gf.components.mmi1x2(width_mmi=width_mmi, length_mmi=length_mmi,
                         length_taper=length_taper, width_taper=width_taper,
                         gap_mmi=gap_mmi)
c.write_gds("device.gds")
