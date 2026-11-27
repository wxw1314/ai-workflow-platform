import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useMemo, useState } from "react"
import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Node,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import WorkflowNode from "@/components/Workflow/WorkflowNode"

type WorkflowNodeKind =
  | "start"
  | "text"
  | "llm"
  | "condition"
  | "rag"
  | "tool"
  | "end"

type WorkflowNodeData = {
  label: string
  kind: WorkflowNodeKind

  // 开始节点
  inputMode?: "manual" | "api"

  // 文本节点
  text?: string

  // LLM 节点
  model?: string
  prompt?: string
  temperature?: number

  // RAG 节点
  knowledgeBaseId?: string
  documents?: string[]

  // 条件节点
  condition?: string

  // 工具节点
  tool?: string
}

type WorkflowNodeType = Node<WorkflowNodeData, "workflow">

const nodeTypes = {
  workflow: WorkflowNode,
}

const initialNodes: WorkflowNodeType[] = [
  {
    id: "start",
    type: "workflow",
    position: { x: 100, y: 100 },
    data: {
      label: "开始",
      kind: "start",
      inputMode: "manual",
    },
  },
  {
    id: "llm",
    type: "workflow",
    position: { x: 400, y: 100 },
    data: {
      label: "LLM",
      kind: "llm",
      model: "gpt-4o-mini",
      prompt: "",
      temperature: 0.7,
    },
  },
  {
    id: "end",
    type: "workflow",
    position: { x: 700, y: 100 },
    data: {
      label: "结束",
      kind: "end",
    },
  },
]

const initialEdges = [
  {
    id: "start-llm",
    source: "start",
    target: "llm",
  },
  {
    id: "llm-end",
    source: "llm",
    target: "end",
  },
]

const availableNodes: Array<{
  type: WorkflowNodeKind
  label: string
  description: string
}> = [
  {
    type: "text",
    label: "文本",
    description: "输入或生成文本内容",
  },
  {
    type: "llm",
    label: "LLM",
    description: "调用大语言模型",
  },
  {
    type: "condition",
    label: "条件",
    description: "根据条件进行分支",
  },
  {
    type: "rag",
    label: "RAG",
    description: "检索知识库或上传文档",
  },
  {
    type: "tool",
    label: "工具",
    description: "调用外部工具或 API",
  },
]

export const Route = createFileRoute("/_layout/workflows")({
  component: Workflows,
})

function Workflows() {
  const [nodes, setNodes, onNodesChange] =
    useNodesState<WorkflowNodeType>(initialNodes)

  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) {
      return null
    }

    return nodes.find((node) => node.id === selectedNodeId) ?? null
  }, [nodes, selectedNodeId])

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((currentEdges) => addEdge(connection, currentEdges))
    },
    [setEdges],
  )

  const addNode = (type: WorkflowNodeKind, label: string) => {
    const newNode: WorkflowNodeType = {
      id: `${type}-${crypto.randomUUID()}`,
      type: "workflow",
      position: {
        x: 150 + Math.random() * 300,
        y: 150 + Math.random() * 300,
      },
      data: {
        label,
        kind: type,

        ...(type === "start" && {
          inputMode: "manual",
        }),

        ...(type === "llm" && {
          model: "gpt-4o-mini",
          prompt: "",
          temperature: 0.7,
        }),

        ...(type === "rag" && {
          knowledgeBaseId: "",
          documents: [],
        }),

        ...(type === "condition" && {
          condition: "",
        }),

        ...(type === "tool" && {
          tool: "",
        }),

        ...(type === "text" && {
          text: "",
        }),
      },
    }

    setNodes((currentNodes) => [...currentNodes, newNode])
    setSelectedNodeId(newNode.id)
  }

  const updateSelectedNode = (
    updates: Partial<WorkflowNodeData>,
  ) => {
    if (!selectedNodeId) {
      return
    }

    setNodes((currentNodes) =>
      currentNodes.map((node) =>
        node.id === selectedNodeId
          ? {
              ...node,
              data: {
                ...node.data,
                ...updates,
              },
            }
          : node,
      ),
    )
  }

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: WorkflowNodeType) => {
      setSelectedNodeId(node.id)
    },
    [],
  )

  const handlePaneClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  return (
    <div className="flex flex-col gap-4">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          工作流编辑器
        </h1>

        <p className="text-muted-foreground">
          通过连接不同节点，构建自己的 AI 工作流
        </p>
      </div>

      <div className="flex h-[650px] overflow-hidden rounded-lg border bg-background">
        {/* ==================== 左侧节点面板 ==================== */}
        <aside className="w-56 shrink-0 border-r bg-background p-4">
          <h2 className="mb-2 font-semibold">
            节点面板
          </h2>

          <p className="mb-4 text-sm text-muted-foreground">
            点击添加节点
          </p>

          <div className="flex flex-col gap-2">
            {availableNodes.map((node) => (
              <button
                key={node.type}
                type="button"
                onClick={() =>
                  addNode(node.type, node.label)
                }
                className="rounded-md border p-3 text-left transition-colors hover:border-primary hover:bg-accent"
              >
                <div className="font-medium">
                  {node.label}
                </div>

                <div className="text-xs text-muted-foreground">
                  {node.description}
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* ==================== 中间画布 ==================== */}
        <div className="min-w-0 flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={handleNodeClick}
            onPaneClick={handlePaneClick}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>

        {/* ==================== 右侧属性面板 ==================== */}
        <aside className="w-80 shrink-0 border-l bg-background">
          {!selectedNode ? (
            <div className="flex h-full items-center justify-center p-6 text-center">
              <div>
                <h2 className="font-semibold">
                  节点属性
                </h2>

                <p className="mt-2 text-sm text-muted-foreground">
                  点击画布中的节点查看和编辑属性
                </p>
              </div>
            </div>
          ) : (
            <NodeSettings
              node={selectedNode}
              onChange={updateSelectedNode}
            />
          )}
        </aside>
      </div>
    </div>
  )
}

type NodeSettingsProps = {
  node: WorkflowNodeType
  onChange: (updates: Partial<WorkflowNodeData>) => void
}

function NodeSettings({
  node,
  onChange,
}: NodeSettingsProps) {
  const { data } = node

  return (
    <div className="flex h-full flex-col">
      {/* 面板标题 */}
      <div className="border-b p-4">
        <div className="text-xs font-medium uppercase text-muted-foreground">
          {data.kind}
        </div>

        <h2 className="mt-1 text-lg font-semibold">
          {data.label}
        </h2>
      </div>

      {/* 属性内容 */}
      <div className="flex-1 overflow-y-auto p-4">
        {data.kind === "start" && (
          <StartNodeSettings
            data={data}
            onChange={onChange}
          />
        )}

        {data.kind === "text" && (
          <TextNodeSettings
            data={data}
            onChange={onChange}
          />
        )}

        {data.kind === "llm" && (
          <LLMNodeSettings
            data={data}
            onChange={onChange}
          />
        )}

        {data.kind === "condition" && (
          <ConditionNodeSettings
            data={data}
            onChange={onChange}
          />
        )}

        {data.kind === "rag" && (
          <RAGNodeSettings
            data={data}
            onChange={onChange}
          />
        )}

        {data.kind === "tool" && (
          <ToolNodeSettings
            data={data}
            onChange={onChange}
          />
        )}

        {data.kind === "end" && (
          <div className="text-sm text-muted-foreground">
            工作流执行到这个节点后结束。
          </div>
        )}
      </div>
    </div>
  )
}

/* ==================== 开始节点 ==================== */

function StartNodeSettings({
  data,
  onChange,
}: {
  data: WorkflowNodeData
  onChange: (updates: Partial<WorkflowNodeData>) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="text-sm font-medium">
          输入方式
        </label>

        <p className="mb-3 mt-1 text-xs text-muted-foreground">
          决定工作流的数据从哪里开始
        </p>

        <div className="space-y-2">
          <label className="flex cursor-pointer items-start gap-3 rounded-md border p-3 hover:bg-accent">
            <input
              type="radio"
              name={`start-input-${data.label}`}
              checked={data.inputMode === "manual"}
              onChange={() =>
                onChange({
                  inputMode: "manual",
                })
              }
            />

            <div>
              <div className="text-sm font-medium">
                手动输入
              </div>

              <div className="text-xs text-muted-foreground">
                在运行工作流时由用户输入内容
              </div>
            </div>
          </label>

          <label className="flex cursor-pointer items-start gap-3 rounded-md border p-3 hover:bg-accent">
            <input
              type="radio"
              name={`start-input-${data.label}`}
              checked={data.inputMode === "api"}
              onChange={() =>
                onChange({
                  inputMode: "api",
                })
              }
            />

            <div>
              <div className="text-sm font-medium">
                API 输入
              </div>

              <div className="text-xs text-muted-foreground">
                通过 API 调用工作流并传入参数
              </div>
            </div>
          </label>
        </div>
      </div>
    </div>
  )
}

/* ==================== 文本节点 ==================== */

function TextNodeSettings({
  data,
  onChange,
}: {
  data: WorkflowNodeData
  onChange: (updates: Partial<WorkflowNodeData>) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">
          文本内容
        </label>

        <textarea
          value={data.text ?? ""}
          onChange={(event) =>
            onChange({
              text: event.target.value,
            })
          }
          placeholder="输入文本内容..."
          className="mt-2 min-h-32 w-full resize-none rounded-md border bg-background p-3 text-sm outline-none focus:border-primary"
        />
      </div>
    </div>
  )
}

/* ==================== LLM 节点 ==================== */

function LLMNodeSettings({
  data,
  onChange,
}: {
  data: WorkflowNodeData
  onChange: (updates: Partial<WorkflowNodeData>) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="text-sm font-medium">
          模型
        </label>

        <select
          value={data.model ?? "gpt-4o-mini"}
          onChange={(event) =>
            onChange({
              model: event.target.value,
            })
          }
          className="mt-2 w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="gpt-4o-mini">
            GPT-4o mini
          </option>

          <option value="gpt-4o">
            GPT-4o
          </option>

          <option value="claude">
            Claude
          </option>
        </select>
      </div>

      <div>
        <label className="text-sm font-medium">
          Prompt
        </label>

        <textarea
          value={data.prompt ?? ""}
          onChange={(event) =>
            onChange({
              prompt: event.target.value,
            })
          }
          placeholder="例如：请根据用户输入生成一段..."
          className="mt-2 min-h-40 w-full resize-none rounded-md border bg-background p-3 text-sm outline-none focus:border-primary"
        />
      </div>

      <div>
        <label className="text-sm font-medium">
          Temperature
        </label>

        <input
          type="number"
          min={0}
          max={2}
          step={0.1}
          value={data.temperature ?? 0.7}
          onChange={(event) =>
            onChange({
              temperature: Number(event.target.value),
            })
          }
          className="mt-2 w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </div>
    </div>
  )
}

/* ==================== 条件节点 ==================== */

function ConditionNodeSettings({
  data,
  onChange,
}: {
  data: WorkflowNodeData
  onChange: (updates: Partial<WorkflowNodeData>) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">
          条件表达式
        </label>

        <p className="mb-2 mt-1 text-xs text-muted-foreground">
          根据上游节点的输出决定走哪条分支
        </p>

        <textarea
          value={data.condition ?? ""}
          onChange={(event) =>
            onChange({
              condition: event.target.value,
            })
          }
          placeholder="例如：output.score > 0.8"
          className="min-h-28 w-full resize-none rounded-md border bg-background p-3 text-sm outline-none focus:border-primary"
        />
      </div>
    </div>
  )
}

/* ==================== RAG 节点 ==================== */

function RAGNodeSettings({
  data,
  onChange,
}: {
  data: WorkflowNodeData
  onChange: (updates: Partial<WorkflowNodeData>) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="text-sm font-medium">
          知识来源
        </label>

        <div className="mt-3 space-y-2">
          <button
            type="button"
            className="w-full rounded-md border p-3 text-left hover:border-primary hover:bg-accent"
          >
            <div className="font-medium">
              上传文档
            </div>

            <div className="mt-1 text-xs text-muted-foreground">
              上传 PDF、TXT、DOCX 等文件
            </div>
          </button>

          <select
            value={data.knowledgeBaseId ?? ""}
            onChange={(event) =>
              onChange({
                knowledgeBaseId: event.target.value,
              })
            }
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="">
              选择知识库
            </option>

            <option value="default">
              默认知识库
            </option>

            <option value="demo">
              Demo 知识库
            </option>
          </select>
        </div>
      </div>

      <div>
        <label className="text-sm font-medium">
          当前文档
        </label>

        {data.documents?.length ? (
          <div className="mt-2 space-y-2">
            {data.documents.map((document) => (
              <div
                key={document}
                className="rounded-md border bg-muted/40 p-2 text-sm"
              >
                {document}
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">
            暂无上传文档
          </p>
        )}
      </div>
    </div>
  )
}

/* ==================== 工具节点 ==================== */

function ToolNodeSettings({
  data,
  onChange,
}: {
  data: WorkflowNodeData
  onChange: (updates: Partial<WorkflowNodeData>) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">
          工具
        </label>

        <select
          value={data.tool ?? ""}
          onChange={(event) =>
            onChange({
              tool: event.target.value,
            })
          }
          className="mt-2 w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="">
            选择工具
          </option>

          <option value="http">
            HTTP API
          </option>

          <option value="web-search">
            Web Search
          </option>

          <option value="code">
            Code
          </option>
        </select>
      </div>
    </div>
  )
}