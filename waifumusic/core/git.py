import asyncio
import shlex
from typing import Tuple

import config
from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    """
    Run a shell command asynchronously and return stdout, stderr, returncode, pid.
    """
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def git():
    """
    Git operations are disabled on Heroku.
    This function does nothing but logs a message.
    """
    LOGGER(__name__).info("Git operations are disabled on Heroku. Updates should be done via deploy.")
