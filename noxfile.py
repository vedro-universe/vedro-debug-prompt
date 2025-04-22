from functools import partial

try:
    import nox
except ImportError:
    print("Please install `nox` to run this script")
    exit(1)

PROJECT_NAME = "vedro_debug_prompt"
PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12", "3.13"]

nox.options.sessions = ["install"]
reusable = partial(nox.session, python=False, reuse_venv=True)


@reusable
def install(session: nox.Session):
    session.run("pip", "install", "--upgrade", "pip")
    session.run("pip", "install", "-e", ".[dev]")


@reusable
def build(session: nox.Session):
    session.run("python", "-m", "build")


@reusable(tags=["lint"])
def check_types(session: nox.Session) -> None:
    session.run("mypy", PROJECT_NAME, "--strict", external=True)


@reusable(tags=["lint"])
def check_imports(session: nox.Session) -> None:
    session.run("isort", PROJECT_NAME, "tests", "--check-only", external=True)


@reusable(tags=["fix"])
def sort_imports(session: nox.Session) -> None:
    session.run("isort", PROJECT_NAME, "tests", external=True)


@reusable(tags=["lint"])
def check_style(session: nox.Session) -> None:
    session.run("pflake8", PROJECT_NAME, "tests", external=True)


@reusable(python=PYTHON_VERSIONS)
def check_types_matrix(session: nox.Session) -> None:
    session.run("mypy", PROJECT_NAME, "--strict", external=True)


@reusable
def bump(session: nox.Session) -> None:
    if not session.posargs:
        session.error("Please specify what to bump: e.g. 'patch', 'minor' or 'major'")

    session.run("bump2version", *session.posargs)
    session.run("git", "--no-pager", "show", "HEAD")
    session.run("git", "verify-commit", "HEAD")
    session.run("bash", "-c", "git verify-tag $(git describe --tags)")


@reusable
def publish(session: nox.Session) -> None:
    session.run("twine", "upload", "dist/*", external=True)
