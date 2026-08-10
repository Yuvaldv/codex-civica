from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

def deploy(site_dir: Path, env_overrides: dict | None = None) -> bool:
    """Build and deploy the Docusaurus site."""
    logging.info("Deploying site...")
    env = {**os.environ, **(env_overrides or {})}
    try:
        result = subprocess.run(
            ["npm", "run", "deploy"],
            cwd=str(site_dir),
            env=env,
            timeout=300,
            capture_output=False,
        )
        if result.returncode != 0:
            logging.error("Deploy failed with exit code %d", result.returncode)
            return False
        logging.info("Deploy successful.")
        return True
    except (subprocess.TimeoutExpired, OSError) as e:
        logging.error("Deploy error: %s", e)
        return False
