import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function ConditionNodeConfig({
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
          条件表达式
        </label>

        <textarea
          value={String(
            node.data.expression ?? "",
          )}
          onChange={(event) =>
            update({
              expression: event.target.value,
            })
          }
          className="min-h-28 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="例如：score > 0.8"
        />
      </div>

      <div className="rounded-md border bg-muted/30 p-3">
        <div className="text-sm font-medium">
          输出分支
        </div>

        <div className="mt-2 space-y-1 text-xs text-muted-foreground">
          <div>True → 条件成立</div>
          <div>False → 条件不成立</div>
        </div>
      </div>
    </div>
  )
}