import type { Node } from "@xyflow/react"

import StartNodeConfig from "./node-config/StartNodeConfig"
import TextNodeConfig from "./node-config/TextNodeConfig"
import LLMNodeConfig from "./node-config/LLMNodeConfig"
import ConditionNodeConfig from "./node-config/ConditionNodeConfig"
import RAGNodeConfig from "./node-config/RAGNodeConfig"
import ToolNodeConfig from "./node-config/TextNodeConfig"
import EndNodeConfig from "./node-config/EndNodeConfig"

type WorkflowConfigPanelProps = {
  node: Node | null
  onUpdateNode: (nodeId: string, data: Record<string, unknown>) => void
}

export default function WorkflowConfigPanel({
  node,
  onUpdateNode,
}: WorkflowConfigPanelProps) {
  if (!node) {
    return (
      <aside className="flex h-full w-80 shrink-0 items-center justify-center border-l bg-background p-6">
        <div className="text-center">
          <div className="mb-2 text-sm font-medium">
            未选择节点
          </div>

          <p className="text-sm text-muted-foreground">
            点击画布中的节点，在这里配置节点参数
          </p>
        </div>
      </aside>
    )
  }

  const commonProps = {
    node,
    onUpdateNode,
  }

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-l bg-background">
      <div className="border-b p-4">
        <div className="text-xs text-muted-foreground">
          节点配置
        </div>

        <h2 className="mt-1 text-lg font-semibold">
          {String(node.data.label)}
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {node.data.kind === "start" && (
          <StartNodeConfig {...commonProps} />
        )}

        {node.data.kind === "text" && (
          <TextNodeConfig {...commonProps} />
        )}

        {node.data.kind === "llm" && (
          <LLMNodeConfig {...commonProps} />
        )}

        {node.data.kind === "condition" && (
          <ConditionNodeConfig {...commonProps} />
        )}

        {node.data.kind === "rag" && (
          <RAGNodeConfig {...commonProps} />
        )}

        {node.data.kind === "tool" && (
          <ToolNodeConfig {...commonProps} />
        )}

        {node.data.kind === "end" && (
          <EndNodeConfig {...commonProps} />
        )}
      </div>
    </aside>
  )
}