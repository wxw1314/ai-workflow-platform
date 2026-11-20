import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function TextNodeConfig({
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
          文本内容
        </label>

        <textarea
          value={String(node.data.content ?? "")}
          onChange={(event) =>
            update({
              content: event.target.value,
            })
          }
          className="min-h-40 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="输入文本内容..."
        />
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">
          输出变量名
        </label>

        <input
          value={String(node.data.outputVariable ?? "")}
          onChange={(event) =>
            update({
              outputVariable: event.target.value,
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="例如：context"
        />
      </div>
    </div>
  )
}