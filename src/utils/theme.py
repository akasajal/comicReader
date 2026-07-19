import json

from resource import resource_path


THEMES = resource_path("assets", "themes")


def load_theme(name: str) -> str:
    template = (THEMES / "template.qss").read_text(encoding="utf-8")

    with open(THEMES / f"{name}.json", encoding="utf-8") as f:
        colors = json.load(f)

    for key, value in colors.items():
        template = template.replace(f"{{{{{key}}}}}", value)

    return template
