# Vedro Debug Prompt

[![PyPI](https://img.shields.io/pypi/v/vedro-debug-prompt.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-debug-prompt/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vedro-debug-prompt?style=flat-square)](https://pypi.python.org/pypi/vedro-debug-prompt/)
[![Python Version](https://img.shields.io/pypi/pyversions/vedro-debug-prompt.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-debug-prompt/)

> **AI Debug Prompt for Vedro** – auto‑generates AI‑friendly Markdown prompts for every failed scenario, ready to paste straight into ChatGPT (or any LLM).

## Installation

<details open>
<summary>Quick</summary>
<p>

For a one‑liner install via Vedro’s plugin manager:

```shell
$ vedro plugin install vedro-debug-prompt
```

</p>
</details>

<details>
<summary>Manual</summary>
<p>

1. Install the package:

```shell
$ pip3 install vedro-debug-prompt
```

2. Enable the plugin in `vedro.cfg.py`:

```python
import vedro
import vedro_debug_prompt

class Config(vedro.Config):
    class Plugins(vedro.Config.Plugins):
        class DebugPrompt(vedro_debug_prompt.DebugPrompt):
            enabled = True
```

</p>
</details>

## Usage

Run your tests as usual:

```shell
vedro run
```

When a scenario fails you’ll see something like:

```text
 ✗ decode base64 encoded string
   |> AI Debug Prompt: .vedro/tmp/prompt_2ltoa90r.md
```

⌘‑click (or Ctrl‑click) the path in most terminals to open the file, then paste its contents into your favourite LLM for an instant diagnosis and minimal fix suggestion.

## Documentation

Full usage examples and advanced configuration live in the docs:

👉 **[vedro.io/docs/ai/debug-prompt](https://vedro.io/docs/ai/debug-prompt)**
