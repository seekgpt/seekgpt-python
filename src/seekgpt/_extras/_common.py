from .._exceptions import SeekGPTError

INSTRUCTIONS = """

SeekGPT error:

    missing `{library}`

This feature requires additional dependencies:

    $ pip install seekgpt[{extra}]

"""


def format_instructions(*, library: str, extra: str) -> str:
    return INSTRUCTIONS.format(library=library, extra=extra)


class MissingDependencyError(SeekGPTError):
    pass
