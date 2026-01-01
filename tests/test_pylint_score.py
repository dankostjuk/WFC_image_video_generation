import re
import shutil
import subprocess


def test_pylint_score_threshold() -> None:
    pylint = shutil.which("pylint")
    if pylint is None:
        raise AssertionError("pylint is not installed")

    result = subprocess.run(
        [pylint, "src/*", "--disable=C0301,C0103"],
        capture_output=True,
        text=True,
        check=False,
    )

    match = re.search(r"rated at ([0-9.]+)/10", result.stdout)
    assert match, f"pylint score not found in output:\n{result.stdout}"
    score = float(match.group(1))
    assert score > 9.9, f"pylint score too low: {score}"
