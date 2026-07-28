Recreate the device shown in the attached image as a primitives-only,
parametric GDSFactory Python program.

Hard requirements:

- Use GDSFactory 9.20.7 and place all device material on layer `(1, 0)`.
- Use only the primitive constructors in the exact catalogue above to create
  geometry. Ordinary GDSFactory assembly, transforms, ports, cross-sections,
  and Python control flow are allowed. Do not use prebuilt device-level
  stencils, raw polygon coordinates, raster tracing, or runtime image reads.
- Declare every function-defining tunable, such as gaps, lengths, widths,
  radii, offsets, pitches, and repeated-element counts, as a live top-level
  `name = value` assignment.
- Define the device with an `@gf.cell` function and return the completed
  component.
- Produce a complete executable program. Under
  `if __name__ == "__main__":`, instantiate the device and write it to the
  exact filename `device.gds` with `.write_gds("device.gds")`. The different
  filename in the catalogue's assembly example is illustrative and does not
  apply to this task.
- Match the stated physical footprint in micrometers.

Before coding, reason internally about the topology, connectivity, repeated
elements, and function-defining knobs. Before answering, check that every
identifier is defined, every catalogue function and keyword is spelled exactly
as documented, port names are indexed directly, and the program ends by writing
a non-empty `device.gds`. Do not output the reasoning.

Output only the complete Python program. Do not include explanation or any
other text.
