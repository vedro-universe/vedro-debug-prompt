from typing import Type, Union

from vedro import create_tmp_file
from vedro.core import ConfigType, Dispatcher, Plugin, PluginConfig
from vedro.events import ConfigLoadedEvent, ScenarioFailedEvent

from ._prompt_builder import PromptBuilder

__all__ = ("DebugPrompt", "DebugPromptPlugin",)


class DebugPromptPlugin(Plugin):
    """
    Listens for scenario failure events and generates debug prompts.

    This plugin integrates with Vedro's event system and responds to
    failed scenarios by creating AI-ready markdown prompts using the PromptBuilder.
    """

    def __init__(self, config: "Type[DebugPrompt]") -> None:
        """
        Initialize the DebugPromptPlugin with the provided configuration.

        :param config: The plugin configuration instance containing a prompt builder.
        """
        super().__init__(config)
        self._prompt_builder: PromptBuilder = config.prompt_builder
        self._global_config: Union[ConfigType, None] = None

    def subscribe(self, dispatcher: Dispatcher) -> None:
        """
        Subscribe to Vedro events.

        :param dispatcher: The dispatcher used to register event listeners.
        """
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
                  .listen(ScenarioFailedEvent, self.on_scenario_failed)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        """
        Handle the ConfigLoadedEvent and store the configuration.

        :param event: The event containing the loaded config.
        """
        self._global_config = event.config

    async def on_scenario_failed(self, event: ScenarioFailedEvent) -> None:
        """
        Handle a failed scenario by building and storing a debug prompt.

        :param event: The event containing the failed scenario result.
        """
        assert self._global_config is not None  # for type checker

        scenario_result = event.scenario_result
        prompt = self._prompt_builder.build(scenario_result, self._global_config.project_dir)

        prompt_file = create_tmp_file(prefix="prompt_", suffix=".md")
        prompt_file.write_text(prompt)

        prompt_file_path = prompt_file.relative_to(self._global_config.project_dir)
        scenario_result.add_extra_details(f"AI Debug Prompt: {prompt_file_path}")


class DebugPrompt(PluginConfig):
    """
    Represents the configuration for the DebugPromptPlugin.

    This config defines plugin metadata and holds a customizable PromptBuilder
    instance used to generate debug prompts.
    """

    plugin = DebugPromptPlugin
    description = "Auto‑generates AI‑ready debug prompts for failed scenarios"

    prompt_builder: PromptBuilder = PromptBuilder()
    """Instance of PromptBuilder used to construct detailed AI-ready debug prompts"""
