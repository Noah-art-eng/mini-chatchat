from prompts.default import DEFAULT_PROMPT
from prompts.empty import EMPTY_PROMPT
from prompts.strict import STRICT_PROMPT


PROMPT_TEMPLATES = {
    "default": DEFAULT_PROMPT,
    "empty": EMPTY_PROMPT,
    "strict": STRICT_PROMPT,
}


def get_prompt_template(prompt_name):
    """负责 get_prompt_template 的函数职责。"""
    return PROMPT_TEMPLATES.get(prompt_name, DEFAULT_PROMPT)
