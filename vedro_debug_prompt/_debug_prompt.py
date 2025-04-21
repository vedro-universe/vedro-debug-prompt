from typing import Type, Union

from vedro import create_tmp_file
from vedro.core import ConfigType, Dispatcher, Plugin, PluginConfig
from vedro.events import ConfigLoadedEvent, ScenarioFailedEvent

from ._prompt_builder import PromptBuilder

__all__ = ("DebugPrompt", "DebugPromptPlugin",)


class DebugPromptPlugin(Plugin):
    def __init__(self, config: "Type[DebugPrompt]") -> None:
        super().__init__(config)
        self._prompt_builder: PromptBuilder = config.prompt_builder
        self._global_config: Union[ConfigType, None] = None

    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
                  .listen(ScenarioFailedEvent, self.on_scenario_failed)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        self._global_config = event.config

    async def on_scenario_failed(self, event: ScenarioFailedEvent) -> None:
        assert self._global_config is not None  # for type checker

        scenario_result = event.scenario_result
        prompt = self._prompt_builder.build(scenario_result, self._global_config.project_dir)

        prompt_file = create_tmp_file(prefix="prompt_", suffix=".md")
        prompt_file.write_text(prompt)

        prompt_file_path = prompt_file.relative_to(self._global_config.project_dir)
        scenario_result.add_extra_details(f"AI Debug Prompt: {prompt_file_path}")


class DebugPrompt(PluginConfig):
    plugin = DebugPromptPlugin

    prompt_builder: PromptBuilder = PromptBuilder()
