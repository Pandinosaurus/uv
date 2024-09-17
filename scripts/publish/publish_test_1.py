# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx",
#     "packaging",
# ]
# ///

"""
Test `uv publish` by uploading a new version of astral-test-1 to testpypi,
authenticating with a token.
"""

import os
import re
from argparse import ArgumentParser
from pathlib import Path
from shutil import rmtree
from subprocess import check_call

import httpx
from packaging.utils import parse_sdist_filename, parse_wheel_filename

cwd = Path(__file__).parent


def get_new_version(project_name: str) -> str:
    """Return the next free path version on pypi"""
    index_page = f"https://test.pypi.org/simple/{project_name}/?format=application/vnd.pypi.simple.v1+json"
    data = httpx.get(index_page).json()
    versions = set()
    for file in data["files"]:
        if file["filename"].endswith(".whl"):
            [_name, version, _build, _tags] = parse_wheel_filename(file["filename"])
        else:
            [_name, version] = parse_sdist_filename(file["filename"])
        versions.add(version)
    max_version = max(versions)

    # Bump the path version to obtain an empty version
    release = list(max_version.release)
    release[-1] += 1
    return ".".join(str(i) for i in release)


def create_project(project_name: str):
    if cwd.joinpath(project_name).exists():
        rmtree(cwd.joinpath(project_name))
    check_call(["cargo", "run", "init", "--lib", project_name], cwd=cwd)
    pyproject_toml = cwd.joinpath(project_name).joinpath("pyproject.toml")

    # Set to an unclaimed version
    toml = pyproject_toml.read_text()
    new_version = get_new_version(project_name)
    toml = re.sub('version = ".*"', f'version = "{new_version}"', toml)
    pyproject_toml.write_text(toml)


def main():
    parser = ArgumentParser()
    parser.add_argument("project")
    args = parser.parse_args()

    project_name = args.project

    # Create the project
    create_project(project_name)
    # Build the project
    check_call(["cargo", "run", "build"], cwd=cwd.joinpath(project_name))
    # Upload the project
    if project_name == "astral-test-password":
        # Token auth project: Set the token as env var first.
        env = os.environ.copy()
        env["UV_PUBLISH_PASSWORD"] = os.environ["UV_TEST_PUBLISH_TOKEN"]
        check_call(
            [
                "cargo",
                "run",
                "publish",
                "--publish-url",
                "https://test.pypi.org/legacy/",
                "--username",
                "__token__",
            ],
            cwd=cwd.joinpath(project_name),
            env=env,
        )
    elif project_name == "astral-test-keyring":
        # Keyring auth project: Set the token as env var first with:
        # ```
        # uv pip install keyring
        # keyring set https://test.pypi.org/legacy/?astral-test-keyring __token__
        # ```
        # The query parameter a horrible hack stolen from
        # https://github.com/pypa/twine/issues/565#issue-555219267
        check_call(
            [
                "cargo",
                "run",
                "publish",
                "--publish-url",
                "https://test.pypi.org/legacy/?astral-test-keyring",
                "--username",
                "__token__",
                "--keyring-provider",
                "subprocess",
            ],
            cwd=cwd.joinpath(project_name),
        )


if __name__ == "__main__":
    main()
