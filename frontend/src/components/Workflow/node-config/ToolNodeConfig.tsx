import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function ToolNodeConfig({
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
          工具类型
        </label>

        <select
          value={String(
            node.data.toolType ?? "http",
          )}
          onChange={(event) =>
            update({
              toolType: event.target.value,
            })
          }
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="http">
            HTTP Request
          </option>

          <option value="code">
            Code
          </option>

          <option value="search">
            Web Search
          </option>
        </select>
      </div>

      {node.data.toolType === "http" && (
        <>
          <div>
            <label className="mb-2 block text-sm font-medium">
              URL
            </label>

            <input
              value={String(node.data.url ?? "")}
              onChange={(event) =>
                update({
                  url: event.target.value,
                })
              }
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="https://api.example.com/..."
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium">
              HTTP Method
            </label>

            <select
              value={String(
                node.data.method ?? "GET",
              )}
              onChange={(event) =>
                update({
                  method: event.target.value,
                })
              }
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
        </>
      )}

      {node.data.toolType === "code" && (
        <div>
          <label className="mb-2 block text-sm font-medium">
            Code
          </label>

          <textarea
            value={String(node.data.code ?? "")}
            onChange={(event) =>
              update({
                code: event.target.value,
              })
            }
            className="min-h-48 w-full resize-none rounded-md border bg-background px-3 py-2 font-mono text-sm"
            placeholder="// 输入代码..."
          />
        </div>
      )}
    </div>
  )
}