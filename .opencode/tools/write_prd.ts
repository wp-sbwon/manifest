import { tool } from "@opencode-ai/plugin"
import path from "path"
import { fileURLToPath } from "url"

const _toolsDir = path.dirname(fileURLToPath(import.meta.url))
const _repoRoot = path.dirname(path.dirname(_toolsDir))
const _cliPath = path.join(_toolsDir, "architect_cli.py")
const _srcPath = path.join(_repoRoot, "src")

export default tool({
  description:
    "Write PRD and initial blueprint to .manifest. Creates prd.json and blueprint_design.json from mission text. Use this to persist top-down design from user discussion.",
  args: {
    mission: tool.schema
      .string()
      .describe("Mission or product goal text to save as PRD and minimal blueprint"),
  },
  async execute(args, context) {
    const worktree = context.worktree || context.directory || process.cwd()
    const manifestDir = path.join(worktree, ".manifest")
    const payload = JSON.stringify({ mission: args.mission || "" })
    const env = { ...process.env, PYTHONPATH: _srcPath }
    const result = await Bun.$`python3 ${_cliPath} ${manifestDir} write_prd ${payload}`.env(env).text()
    return result.trim()
  },
})
