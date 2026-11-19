import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function StartNodeConfig({
  node,
  onUpdateNode,
}: Props) {
  const triggerType = String(
    node.data.triggerType ?? "manual",
  )

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
          触发方式
        </label>

        <select
          value={triggerType}
          onChange={(event) =>
            update({
              triggerType: event.target.value,
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="manual">
            手动运行
          </option>

          <option value="api">
            API
          </option>

          <option value="schedule">
            定时任务
          </option>
        </select>
      </div>

      {triggerType === "api" && (
        <div className="rounded-md border bg-muted/30 p-3">
          <div className="text-sm font-medium">
            API 输入
          </div>

          <p className="mt-1 text-xs text-muted-foreground">
            工作流可以通过 API 请求触发。
          </p>
        </div>
      )}

      {triggerType === "schedule" && (
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium">
              Cron 表达式
            </label>

            <input
              value={String(
                node.data.cron ?? "0 9 * * *",
              )}
              onChange={(event) =>
                update({
                  cron: event.target.value,
                })
              }
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="0 9 * * *"
            />
          </div>

          <p className="text-xs text-muted-foreground">
            例如：每天上午 9 点执行。
          </p>
        </div>
      )}

      <div>
        <div className="mb-2 text-sm font-medium">
          输入变量
        </div>

        <div className="rounded-md border">
          <div className="border-b px-3 py-2 text-xs text-muted-foreground">
            第一版先支持基础输入变量
          </div>

          <div className="space-y-2 p-3">
            <input
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="变量名，例如 question"
            />

            <select className="w-full rounded-md border bg-background px-3 py-2 text-sm">
              <option value="string">string</option>
              <option value="number">number</option>
              <option value="boolean">boolean</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}