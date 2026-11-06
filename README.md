# Tool Utility Repo

Kodi repository for **TorUtilityBox** and **TorBox**.

## Install in Kodi
1. Settings > File manager > Add source > `https://anubis101xy.github.io/tool-utility--repo/` (name it `Tool Utility`)
2. Add-ons > Install from zip file > Tool Utility > `repository.toolutility-1.0.0.zip`
3. Add-ons > Install from repository > Tool Utility Repo > Video add-ons

## Publishing an update
1. Put the new add-on zip(s) in `incoming/`
2. Run `python tools/build_repo.py`
3. Upload the changed files (`zips/`, `index.html`) to GitHub - Kodi picks up the update within a few hours.
