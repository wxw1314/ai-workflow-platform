import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function LLMNodeConfig({
  node,
  onUpdateNode,
}: Props) {
  const update = (data: Record<string, unknown>) => {
    onUpdateNode(node.id, {
      ...node.data,
      ...data,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="mb-2 block text-sm font-medium">
          模型
        </label>

        <select
          value={String(node.data.model ?? "gpt-4o")}
          onChange={(event) =>
            update({
              model: event.target.value,
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="gpt-4o">GPT-4o</option>
          <option value="gpt-4.1">GPT-4.1</option>
          <option value="claude">Claude</option>
        </select>
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">
          System Prompt
        </label>

        <textarea
          value={String(node.data.systemPrompt ?? "")}
          onChange={(event) =>
            update({
              systemPrompt: event.target.value,
            })
          }
          className="min-h-32 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="定义 AI 的角色和行为..."
        />
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">
          User Prompt
        </label>

        <textarea
          value={String(node.data.userPrompt ?? "")}
          onChange={(event) =>
            update({
              userPrompt: event.target.value,
            })
          }
          className="min-h-32 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="输入用户提示词..."
        />
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">
          Temperature
        </label>

        <input
          type="number"
          min="0"
          max="2"
          step="0.1"
          value={Number(node.data.temperature ?? 0.7)}
          onChange={(event) =>
            update({
              temperature: Number(event.target.value),
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">
          Max Tokens
        </label>

        <input
          type="number"
          min="1"
          value={Number(node.data.maxTokens ?? 2000)}
          onChange={(event) =>
            update({
              maxTokens: Number(event.target.value),
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </div>
    </div>
  )
}