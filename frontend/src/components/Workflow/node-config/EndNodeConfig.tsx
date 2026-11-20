import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function EndNodeConfig({
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
          输出格式
        </label>

        <select
          value={String(
            node.data.outputType ?? "text",
          )}
          onChange={(event) =>
            update({
              outputType: event.target.value,
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="text">文本</option>
          <option value="json">JSON</option>
        </select>
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">
          输出变量
        </label>

        <input
          value={String(
            node.data.outputVariable ?? "",
          )}
          onChange={(event) =>
            update({
              outputVariable: event.target.value,
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="例如：result"
        />
      </div>
    </div>
  )
}