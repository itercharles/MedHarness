"""Init command — Click declaration only."""

import click


def register(main):
    @main.command("init")
    def init_cmd() -> None:
        """Interactive onboarding: scaffold a product repo and a DHF repo."""
        from medharness.workflows.init import run_init
        run_init()
