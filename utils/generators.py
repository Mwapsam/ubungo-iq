import re


def slugify_function(content):
    content = re.sub(r"[^\w\s-]", "", content)
    content = content.replace("_", "-").replace(" ", "-").lower()
    content = re.sub(r"-+", "-", content).strip("-")
    return content
