# Third-party notices

PixCell's dataset records, generated images, ground-truth programs, release
tools, and documentation are distributed under the [MIT License](LICENSE).
The release tools and generated programs use the separately distributed
packages below. Their source code is not vendored in this directory, and each
package remains governed by its own license.

| Package | Version used for the release | License |
|---|---:|---|
| GDSFactory | 9.20.7 | MIT |
| gdstk | 0.9.0 | Boost Software License 1.0 |
| kfactory | 2.0.1 | MIT |
| Pillow | 12.3.0 | HPND / MIT-CMU family |
| NumPy | 2.4.6 | BSD-3-Clause, with separately licensed bundled components |
| SciPy | 1.18.0 | BSD-3-Clause, with separately licensed bundled components |
| scikit-image | 0.26.0 | BSD family, with MIT-licensed components |
| Shapely | 2.1.2 | BSD-3-Clause; binary distributions may bundle GEOS |
| KLayout | 0.30.6 | GPL-3.0-or-later |
| Hugging Face Datasets | 5.0.0 | Apache-2.0 |
| Apache Arrow / PyArrow | 24.0.0 | Apache-2.0 |
| huggingface_hub | 1.22.0 | Apache-2.0 |
| pytest | 9.1.1 | MIT |

This summary is provided for convenience and is not a replacement for the
license text shipped by each dependency. A local installation made from
`requirements-lock.txt` installs those packages from their normal
distribution channels, including their complete notices.

The visual examples are synthetic: they were rendered from project-authored
parametric programs using the declared primitive API. The dataset does not
contain scraped paper figures, foundry layouts, or third-party training
images.
