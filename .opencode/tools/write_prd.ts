import { tool } from "@opencode-ai/plugin"
import path from "path"
import { fileURLToPath } from "url"

const _toolsDir = path.dirname(fileURLToPath(import.meta.url))
const _repoRoot = path.dirname(path.dirname(_toolsDir))
const _cliPath = path.join(_toolsDir, "architect_cli.py")
const _srcPath = path.join(_repoRoot, "src")

export default tool({
  description:
    "Save PRD to .manifest/prd.json (fixed format: title, mission, sections).",
  args: {
    title: tool.schema.string().describe("PRD title").optional(),
    mission: tool.schema.string().describe("Mission or product goal").optional(),
    sections: tool.schema
      .array(
        tool.schema.object({
          heading: tool.schema.string(),
          content: tool.schema.string(),
        })
      )
      .describe("Sections: array of { heading, content }")
      .optional(),
  },
  async execute(args, context) {
    const worktree = context.worktree || context.directory || process.cwd()
    const manifestDir = path.join(worktree, ".manifest")
    const payload = JSON.stringify({
      title: args.title ?? "",
      mission: args.mission ?? "",
      sections: args.sections ?? [],
    })
    const env = { ...process.env, PYTHONPATH: _srcPath }
    const result = await Bun.$`python3 ${_cliPath} ${manifestDir} write_prd ${payload}`.env(env).text()
    return result.trim()
  },
})
