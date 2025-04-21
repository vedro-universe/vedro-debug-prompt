import inspect
import platform
import sys
from os import linesep
from pathlib import Path
from textwrap import dedent
from traceback import format_tb
from typing import List, Tuple, Union

import vedro
from niltype import Nil
from vedro.core import ExcInfo, ScenarioResult, VirtualScenario
from vedro.plugins.director.rich.utils import TracebackFilter

__all__ = ("PromptBuilder",)


class PromptBuilder:
    def __init__(self, *, include_variables: bool = False, tb_limit: int = 10) -> None:
        self._include_variables = include_variables
        self._tb_limit = tb_limit
        self._tb_filter: Union[TracebackFilter, None] = None

    def build(self, scenario_result: ScenarioResult, project_dir: Path) -> str:
        scenario = scenario_result.scenario

        exc_info = self._get_error(scenario_result)
        assert isinstance(exc_info, ExcInfo)

        scenario_source, scenario_lineno, _ = self._get_scenario_source(scenario)
        scenario_path = scenario.path.relative_to(project_dir)
        scenario_loc = f"{scenario_path}:{scenario_lineno}"

        prompt_template = self._get_prompt_template()
        return prompt_template.format(
            system_prompt=self._get_system_prompt(),
            scenario_name=self._get_scenario_name(scenario),
            scenario_loc=scenario_loc,
            runtime=self._get_runtime(),
            scenario_steps=self._get_scenario_steps(scenario_result),
            scenario_source=scenario_source,
            error_message=self._get_error_message(exc_info, project_dir),
            error_tb=self._get_error_tb(exc_info, project_dir),
            variables=self._get_variables(scenario_result) if self._include_variables else "—",
        )

    def _get_prompt_template(self) -> str:
        return dedent("""
            ## SYSTEM
            {system_prompt}

            ## SCENARIO
            - **Name:** {scenario_name}
            - **Location:** {scenario_loc}
            - **Runtime:** {runtime}

            ## STEPS
            {scenario_steps}

            ## SOURCE
            ```python
            {scenario_source}
            ```

            ## FAILURE
            {error_message}

            ## TRACEBACK
            ```python
            {error_tb}
            ```

            ## VARIABLES
            {variables}
        """).strip()

    def _get_system_prompt(self) -> str:
        return dedent("""
            You are a senior Python engineer helping me debug a failed automated test.
            – Analyse the information below.
            – Identify the most likely root cause.
            – Propose the **smallest** code or test change that would make the test pass.
            – Answer in markdown with the sections:
              1. **Root cause**
              2. **Suggested fix (code)** — show only the diff or patched snippet
              3. **Why this works**
        """).strip()

    def _get_error(self, scenario_result: ScenarioResult) -> Union[ExcInfo, None]:
        for step in scenario_result.step_results:
            if step.exc_info:
                return step.exc_info
        return None

    def _get_scenario_name(self, scenario: VirtualScenario) -> str:
        return scenario.subject

    def _get_scenario_steps(self, scenario_result: ScenarioResult) -> str:
        lines = []
        for step_result in scenario_result.step_results:
            status = str(step_result.status.value)
            lines.append(
                f"[{status}] {step_result.step_name} ({step_result.elapsed:.2f}s)"
            )
        return f"{linesep}".join(f"- {line}" for line in lines)

    def _get_scenario_source(self, scenario: VirtualScenario) -> Tuple[str, int, int]:
        try:
            lines, start = inspect.getsourcelines(scenario._orig_scenario)
            dedented = dedent("".join(lines)).splitlines(keepends=True)
            source = self._number_lines(dedented, start)
            end = start + len(dedented) - 1
            return source, start, end
        except:  # noqa: E722
            try:
                raw = scenario.path.read_text()
                lines = raw.splitlines(keepends=True)
                source = self._number_lines(lines, 1)
                return source, 1, len(lines)
            except:  # noqa: E722
                return "", -1, -1

    def _number_lines(self, lines: List[str], start: int) -> str:
        return "".join(f"{start + i:4d}: {line}" for i, line in enumerate(lines))

    def _get_error_message(self, exc_info: ExcInfo, project_dir: Path) -> str:
        exc_value = self._format_exception_message(exc_info.value)
        return self._cleanup_line(exc_value, project_dir)

    def _get_error_tb(self, exc_info: ExcInfo, project_dir: Path) -> str:
        if self._tb_filter is None:
            self._tb_filter = TracebackFilter([vedro])
        traceback = self._tb_filter.filter_tb(exc_info.traceback)

        tb_lines = format_tb(traceback, limit=self._tb_limit)
        cleaned = [self._cleanup_line(line, project_dir) for line in tb_lines]
        return "".join(cleaned).rstrip()

    def _format_exception_message(self, exc_value: BaseException) -> str:
        """
        Format an exception message for `AssertionError` or other exception types.

        This method customizes the formatting of `AssertionError` messages by
        including additional details, such as left and right operands and the
        operator if they are available. For non-`AssertionError` exceptions, it
        returns the string representation of the exception.

        :param exc_value: The exception value to format.
        :return: A string containing the formatted exception message.
        """
        if not isinstance(exc_value, AssertionError):
            return str(exc_value)

        left = getattr(exc_value, "__vedro_assert_left__", Nil)
        if left is Nil:
            return str(exc_value)

        right = getattr(exc_value, "__vedro_assert_right__", Nil)
        operator = getattr(exc_value, "__vedro_assert_operator__", Nil)
        if (right is Nil) or (operator is Nil):
            return f"{exc_value.__class__.__name__}: assert {left!r}"
        else:
            return f"{exc_value.__class__.__name__}: assert {left!r} {operator} {right!r}"

    def _get_variables(self, scenario_result: ScenarioResult) -> str:
        variables = []
        for key, val in scenario_result.scope.items():
            if not key.startswith("_"):
                variables.append(f"{key} = {val!r}")
        return linesep.join(variables) if variables else "No variables found"

    def _get_runtime(self) -> str:
        python_version, *_ = sys.version.split()
        vedro_version = vedro.__version__
        os_platform = platform.platform()
        return f"Python {python_version} · Vedro {vedro_version} · {os_platform}"

    def _cleanup_line(self, line: str, project_dir: Path) -> str:
        return line.replace(str(project_dir), ".")
