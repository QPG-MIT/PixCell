"""P0 regression tests: source locations resolve from installed modules, never
from cwd-relative or pre-src/ file paths (the pattern that broke in the src/ move)."""


def test_michaelangelo_dir_resolves_to_package():
    from homi.paths import michaelangelo_dir

    d = michaelangelo_dir()
    assert d.is_dir()
    assert (d / "core" / "compare_absolute.py").is_file()


def test_repo_root_resolves_to_project():
    from homi.paths import repo_root

    assert (repo_root() / "pyproject.toml").is_file()
