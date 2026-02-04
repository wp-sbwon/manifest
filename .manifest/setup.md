# Setup & how Manifest works

## Required tools (no manual install)

- **OpenCode** — chat and slash commands. The launcher installs it when missing (e.g. `brew install opencode` or `npm install -g opencode-ai`).
- **Podman** — Worker Squad runs in containers. The setup script and launcher install and start Podman when missing; you do not install or run it yourself.

## First-time setup

Run from the project root:

```bash
./scripts/setup.sh
```

This creates the venv, installs Python deps, and ensures Homebrew (macOS), Podman, and OpenCode are available.

## Run

```bash
source venv/bin/activate
manifest
```

This starts OpenCode (chat/commands) and the Manifest View. If OpenCode or Podman are missing, the launcher will try to install and start them.

## Project dir

The app uses the **current working directory** as the project. Run `manifest` from your target repo. When developing Manifest itself, run from the manifest repo; it uses a temp project dir so the View doesn’t load the manifest codebase. Override with `MANIFEST_PROJECT_DIR` if needed.
