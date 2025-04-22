from functools import partial

try:
    import nox
except ImportError:
    print("Please install `nox` to run this script")
    exit(1)

PROJECT_NAME = "vedro_debug_prompt"
PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12", "3.13"]

# Specify which sessions are executed by default when `nox` is run without any -s flags
nox.options.sessions = ["install"]

# Provide a shortcut for defining nox sessions with consistent settings
# - python=False: Use the system Python interpreter rather than creating a new one per session
# - reuse_venv=True: Reuse existing virtual environments across runs for efficiency
reusable = partial(nox.session, python=False, reuse_venv=True)


@reusable
def install(session: nox.Session):
    """
    Install and upgrade pip, then install the project in editable mode with development dependencies.
    """
    session.run("pip", "install", "--upgrade", "pip")
    session.run("pip", "install", "-e", ".[dev]")


@reusable
def build(session: nox.Session):
    """
    Build source and wheel distributions for the project.
    """
    session.run("python", "-m", "build")


@reusable(tags=["lint"])
def check_types(session: nox.Session) -> None:
    """
    Run mypy static type checks against the project code with strict settings.
    """
    session.run("mypy", PROJECT_NAME, "--strict", external=True)


@reusable(tags=["lint"])
def check_imports(session: nox.Session) -> None:
    """
    Verify import sorting without making changes using isort.
    """
    session.run("isort", PROJECT_NAME, "tests", "--check-only", external=True)


@reusable(tags=["fix"])
def sort_imports(session: nox.Session) -> None:
    """
    Automatically sort imports in the project and tests using isort.
    """
    session.run("isort", PROJECT_NAME, "tests", external=True)


@reusable(tags=["lint"])
def check_style(session: nox.Session) -> None:
    """
    Run flake8 to enforce code style and catch linting errors in the project and tests.
    """
    session.run("pflake8", PROJECT_NAME, "tests", external=True)


@reusable(python=PYTHON_VERSIONS)
def check_types_matrix(session: nox.Session) -> None:
    """
    Run mypy checks across all supported Python versions defined in PYTHON_VERSIONS.
    """
    session.run("mypy", PROJECT_NAME, "--strict", external=True)


@reusable
def bump(session: nox.Session) -> None:
    """
    Bump the project version (e.g., patch, minor, major) using bump2version,
    then show and verify the resulting commit and tag.

    Usage: nox -s bump -- <version-part>
    """
    if not session.posargs:
        session.error("Please specify what to bump: e.g. 'patch', 'minor' or 'major'")

    session.run("bump2version", *session.posargs)
    session.run("git", "--no-pager", "show", "HEAD")
    session.run("git", "verify-commit", "HEAD")
    session.run("bash", "-c", "git verify-tag $(git describe --tags)")


@reusable
def publish(session: nox.Session) -> None:
    """
    Upload built distributions from the dist/ directory to PyPI using Twine.

    Requires TWINE_USERNAME and TWINE_PASSWORD (or TWINE_API_TOKEN) in the environment.
    """
    session.run("twine", "upload", "dist/*", external=True)
