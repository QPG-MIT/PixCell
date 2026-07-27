import gdsfactory as gf

# Target footprint (approx): 40.0 x 1.7 um

@gf.cell
def three_prong_fork():
    L_total = 40.0
    W_trunk = 1.7

    # Outer arms
    W_arm = 1.0                   # width of each outer arm in the merged (right) region
    w_tip = 0.14                  # thin width at the left
    y_final = W_trunk/2 - W_arm/2 # centerline offset needed for 1.7-um wide trunk
    y0 = 0.26                     # initial offset so we have 3 separate prongs at the left
    dy_sbend = y_final - y0       # additional offset provided by the S-bend

    L0 = 4.0                      # short straight to present offset at the very left
    Lsb = 8.0                     # S-bend x-span
    Ltaper = 20.0                 # taper after S-bend (arms widen away from center)
    Lright = max(0.0, L_total - (L0 + Lsb + Ltaper))

    xs_thin = gf.cross_section.strip(width=w_tip, layer=(1, 0))
    xs_arm = gf.cross_section.strip(width=W_arm, layer=(1, 0))

    def outer_arm(sign=+1) -> gf.Component:
        c = gf.Component()
        # 1) thin straight at the left, already vertically offset
        s0 = c << gf.components.straight(length=L0, cross_section=xs_thin)
        s0.move((0, sign * y0))

        # 2) small S-bend to reach the final centerline offset
        sb = c << gf.components.bend_s(size=(Lsb, sign * dy_sbend), cross_section=xs_thin)
        sb.connect("o1", s0.ports["o2"])

        # 3) widen to the arm width (happens after arm is offset — keeps the fork gaps)
        tap = c << gf.components.taper(length=Ltaper, width1=w_tip, width2=W_arm, layer=(1, 0))
        tap.connect("o1", sb.ports["o2"])

        # 4) final straight (trunk)
        st = c << gf.components.straight(length=Lright, cross_section=xs_arm)
        st.connect("o1", tap.ports["o2"])
        return c

    top = outer_arm(+1)
    bot = outer_arm(-1)

    # Middle prong: separate at the left, vanishes before the arms broaden
    w_mid = 0.14
    L_mid_head = 4.0
    L_mid_taper = 10.0

    xs_mid = gf.cross_section.strip(width=w_mid, layer=(1, 0))
    mid = gf.Component()
    m0 = mid << gf.components.straight(length=L_mid_head, cross_section=xs_mid)
    tip = mid << gf.components.taper(length=L_mid_taper, width1=w_mid, width2=0.02, layer=(1, 0))
    tip.connect("o1", m0.ports["o2"])

    # Union of the three parametric pieces
    fork = gf.boolean(gf.boolean(top, bot, operation="or", layer=(1, 0)),
                      mid, operation="or", layer=(1, 0))
    return fork


if __name__ == "__main__":
    c = three_prong_fork()
    c.write_gds("three_prong_fork.gds")
    c.show()