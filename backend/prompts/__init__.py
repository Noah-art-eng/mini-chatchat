from prompts.default import DEFAULT_PROMPT
from prompts.empty import EMPTY_PROMPT
from prompts.strict import STRICT_PROMPT


PROMPT_TEMPLATES = {
    "default": DEFAULT_PROMPT,
    "empty": EMPTY_PROMPT,
    "strict": STRICT_PROMPT,
}


def get_prompt_template(prompt_name):
    return PROMPT_TEMPLATES.get(prompt_name, DEFAULT_PROMPT)
