import { tool } from "@opencode-ai/plugin"
import path from "path"
import { fileURLToPath } from "url"

const _toolsDir = path.dirname(fileURLToPath(import.meta.url))
const _repoRoot = path.dirname(path.dirname(_toolsDir))
const _cliPath = path.join(_toolsDir, "architect_cli.py")
const _srcPath = path.join(_repoRoot, "src")

export default tool({
  description:
    "Validate and write blueprint to .manifest/blueprint_design.json. Payload must be a valid blueprint object (root_id, entities). Use after write_prd to persist full architecture.",
  args: {
    payload: tool.schema
      .string()
      .describe("JSON string of blueprint object with root_id and entities array"),
  },
  async execute(args, context) {
    const worktree = context.worktree || context.directory || process.cwd()
    const manifestDir = path.join(worktree, ".manifest")
    const env = { ...process.env, PYTHONPATH: _srcPath }
    const result = await Bun.$`python3 ${_cliPath} ${manifestDir} write_architecture ${args.payload}`.env(env).text()
    return result.trim()
  },
})
