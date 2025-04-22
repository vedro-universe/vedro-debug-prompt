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
    """
    Builds a detailed debug prompt for failed test scenarios.

    This class collects system information, scenario details, steps,
    source code, traceback, and variables to generate a markdown-based
    prompt for use with AI debugging assistants.
    """

    def __init__(self, *, include_variables: bool = False, tb_limit: int = 10) -> None:
        """
        Initialize the PromptBuilder instance with customization options.

        :param include_variables: Whether to include scenario variables in the prompt.
                                  Defaults to False.
        :param tb_limit: The maximum number of traceback lines to include. Defaults to 10.
        """
        self._include_variables = include_variables
        self._tb_limit = tb_limit
        self._tb_filter: Union[TracebackFilter, None] = None

    def build(self, scenario_result: ScenarioResult, project_dir: Path) -> str:
        """
        Build a formatted debug prompt from the given scenario result.

        :param scenario_result: The result of the scenario, including failure and traceback.
        :param project_dir: The root path of the project, used for path cleanup.
        :return: A markdown string containing the full debug prompt.
        """
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
        """
        Retrieve the markdown template used for the debug prompt.

        :return: A string representing the prompt template.
        """
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
        """
        Generate the static system prompt for the debug assistant.

        :return: A string representing the instructions for the AI assistant.
        """
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
        """
        Extract the first error encountered in the scenario result.

        :param scenario_result: The result object containing step results.
        :return: The exception info object if found, otherwise None.
        """
        for step in scenario_result.step_results:
            if step.exc_info:
                return step.exc_info
        return None

    def _get_scenario_name(self, scenario: VirtualScenario) -> str:
        """
        Retrieve the scenario's subject or name.

        :param scenario: The scenario object to extract the name from.
        :return: A string representing the scenario's subject.
        """
        return scenario.subject

    def _get_scenario_steps(self, scenario_result: ScenarioResult) -> str:
        """
        Format each step in the scenario with status and duration.

        :param scenario_result: The scenario result object containing step data.
        :return: A formatted list of scenario steps.
        """
        lines = []
        for step_result in scenario_result.step_results:
            status = str(step_result.status.value)
            lines.append(
                f"[{status}] {step_result.step_name} ({step_result.elapsed:.2f}s)"
            )
        return f"{linesep}".join(f"- {line}" for line in lines)

    def _get_scenario_source(self, scenario: VirtualScenario) -> Tuple[str, int, int]:
        """
        Retrieve and format the source code of the scenario.

        :param scenario: The scenario whose source is to be retrieved.
        :return: A tuple containing the formatted source, start line, and end line.
        """
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
        """
        Add line numbers to a list of source code lines.

        :param lines: A list of source code lines.
        :param start: The line number to start numbering from.
        :return: A string with each line prepended by its line number.
        """
        return "".join(f"{start + i:4d}: {line}" for i, line in enumerate(lines))

    def _get_error_message(self, exc_info: ExcInfo, project_dir: Path) -> str:
        """
        Format the error message from the exception info.

        :param exc_info: The exception info object from the scenario.
        :param project_dir: The base project directory for path normalization.
        :return: A cleaned and formatted error message string.
        """
        exc_value = self._format_exception_message(exc_info.value)
        return self._cleanup_line(exc_value, project_dir)

    def _get_error_tb(self, exc_info: ExcInfo, project_dir: Path) -> str:
        """
        Generate a cleaned-up traceback string from the exception info.

        :param exc_info: The exception info containing the traceback.
        :param project_dir: The project root directory for relative path cleanup.
        :return: A string containing the formatted and filtered traceback.
        """
        if self._tb_filter is None:
            self._tb_filter = TracebackFilter([vedro])
        traceback = self._tb_filter.filter_tb(exc_info.traceback)

        tb_lines = format_tb(traceback, limit=self._tb_limit)
        cleaned = [self._cleanup_line(line, project_dir) for line in tb_lines]
        return "".join(cleaned).rstrip()

    def _format_exception_message(self, exc_value: BaseException) -> str:
        """
        Format an exception message for `AssertionError` or other exception types.

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
        """
        Extract and format variables from the scenario result.

        :param scenario_result: The result object containing the scenario scope.
        :return: A formatted string of variable assignments.
        """
        variables = []
        for key, val in scenario_result.scope.items():
            if not key.startswith("_"):
                variables.append(f"{key} = {val!r}")
        return linesep.join(variables) if variables else "No variables found"

    def _get_runtime(self) -> str:
        """
        Get runtime information including Python version, Vedro version, and OS.

        :return: A string summarizing the runtime environment.
        """
        python_version, *_ = sys.version.split()
        vedro_version = vedro.__version__
        os_platform = platform.platform()
        return f"Python {python_version} · Vedro {vedro_version} · {os_platform}"

    def _cleanup_line(self, line: str, project_dir: Path) -> str:
        """
        Replace absolute paths in a line with relative paths for clarity.

        :param line: The string line to clean.
        :param project_dir: The project directory to be replaced.
        :return: A string with cleaned-up file paths.
        """
        return line.replace(str(project_dir), ".")
