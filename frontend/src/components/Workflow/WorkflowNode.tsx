
import {
  Handle,
  Position,
  type Node,
  type NodeProps,
} from "@xyflow/react"

type WorkflowNodeData = {
  label: string
  kind: string
}

type WorkflowNodeType = Node<WorkflowNodeData, "workflow">

export default function WorkflowNode({
  data,
  selected,
}: NodeProps<WorkflowNodeType>) {
  return (
    <div
      className={`min-w-40 rounded-lg border bg-card shadow-sm ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-border"
      }`}
    >
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !bg-primary"
      />

      <div className="rounded-t-lg border-b bg-muted px-3 py-2">
        <div className="text-xs text-muted-foreground">
          {data.kind.toUpperCase()}
        </div>
        <div className="font-medium">{data.label}</div>
      </div>

      <div className="px-3 py-3 text-xs text-muted-foreground">
        点击节点配置参数
      </div>

      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !bg-primary"
      />
    </div>
  )
}
