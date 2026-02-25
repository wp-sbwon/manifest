import { tool } from "@opencode-ai/plugin"
import path from "path"
import { fileURLToPath } from "url"

const _toolsDir = path.dirname(fileURLToPath(import.meta.url))
const _repoRoot = path.dirname(path.dirname(_toolsDir))
const _cliPath = path.join(_toolsDir, "architect_cli.py")
const _srcPath = path.join(_repoRoot, "src")

export default tool({
  description:
    "Create blueprint_design.json from .manifest/prd.json and start layer-by-layer expansion. Requires prd.json. Builds root from PRD, saves blueprint_design.json, then runs the layer writer recursively until breakdown is complete.",
  args: {},
  async execute(_args, context) {
    const worktree = context.worktree || context.directory || process.cwd()
    const manifestDir = path.join(worktree, ".manifest")
    const env = { ...process.env, PYTHONPATH: _srcPath }
    const result = await Bun.$`python3 ${_cliPath} ${manifestDir} create_blueprint_from_prd`.env(env).text()
    return result.trim()
  },
})
