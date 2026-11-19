import { useRef } from "react"
import type { Node } from "@xyflow/react"

type Props = {
  node: Node
  onUpdateNode: (
    nodeId: string,
    data: Record<string, unknown>,
  ) => void
}

export default function RAGNodeConfig({
  node,
  onUpdateNode,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const sourceType = String(
    node.data.sourceType ?? "upload",
  )

  const update = (data: Record<string, unknown>) => {
    onUpdateNode(node.id, {
      ...node.data,
      ...data,
    })
  }

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const files = Array.from(event.target.files ?? [])

    if (files.length === 0) {
      return
    }

    update({
      documents: files.map((file) => ({
        name: file.name,
        size: file.size,
        type: file.type,
      })),
    })
  }

  const documents = Array.isArray(node.data.documents)
    ? node.data.documents
    : []

  return (
    <div className="space-y-6">
      {/* 数据来源 */}
      <div>
        <label className="mb-2 block text-sm font-medium">
          数据来源
        </label>

        <div className="space-y-2">
          <label className="flex cursor-pointer items-center gap-2 rounded-md border p-3">
            <input
              type="radio"
              name={`rag-source-${node.id}`}
              checked={sourceType === "upload"}
              onChange={() =>
                update({
                  sourceType: "upload",
                })
              }
            />

            <div>
              <div className="text-sm font-medium">
                上传文档
              </div>

              <div className="text-xs text-muted-foreground">
                为当前 RAG 节点提供文档
              </div>
            </div>
          </label>

          <label className="flex cursor-pointer items-center gap-2 rounded-md border p-3">
            <input
              type="radio"
              name={`rag-source-${node.id}`}
              checked={sourceType === "knowledge_base"}
              onChange={() =>
                update({
                  sourceType: "knowledge_base",
                })
              }
            />

            <div>
              <div className="text-sm font-medium">
                已有知识库
              </div>

              <div className="text-xs text-muted-foreground">
                使用系统中已有的知识库
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* 上传文档 */}
      {sourceType === "upload" && (
        <div>
          <label className="mb-2 block text-sm font-medium">
            文档
          </label>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.md,.doc,.docx"
            className="hidden"
            onChange={handleFileChange}
          />

          <button
            type="button"
            onClick={() =>
              fileInputRef.current?.click()
            }
            className="w-full rounded-md border border-dashed p-6 text-center transition-colors hover:border-primary hover:bg-accent"
          >
            <div className="text-sm font-medium">
              上传文档
            </div>

            <div className="mt-1 text-xs text-muted-foreground">
              PDF、TXT、Markdown、Word
            </div>
          </button>

          {documents.length > 0 && (
            <div className="mt-3 space-y-2">
              {documents.map(
                (
                  document: {
                    name: string
                    size: number
                  },
                  index,
                ) => (
                  <div
                    key={`${document.name}-${index}`}
                    className="rounded-md border px-3 py-2"
                  >
                    <div className="truncate text-sm">
                      {document.name}
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {Math.round(
                        document.size / 1024,
                      )}{" "}
                      KB
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      )}

      {/* 知识库 */}
      {sourceType === "knowledge_base" && (
        <div>
          <label className="mb-2 block text-sm font-medium">
            知识库
          </label>

          <select
            value={String(
              node.data.knowledgeBaseId ?? "",
            )}
            onChange={(event) =>
              update({
                knowledgeBaseId: event.target.value,
              })
            }
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="">
              请选择知识库
            </option>

            <option value="default">
              默认知识库
            </option>

            <option value="product">
              产品知识库
            </option>

            <option value="company">
              公司知识库
            </option>
          </select>
        </div>
      )}

      {/* 检索参数 */}
      <div className="space-y-4">
        <div>
          <label className="mb-2 block text-sm font-medium">
            Top K
          </label>

          <input
            type="number"
            min="1"
            max="20"
            value={Number(node.data.topK ?? 5)}
            onChange={(event) =>
              update({
                topK: Number(event.target.value),
              })
            }
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium">
            相似度阈值
          </label>

          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={Number(
              node.data.similarityThreshold ?? 0.7,
            )}
            onChange={(event) =>
              update({
                similarityThreshold: Number(
                  event.target.value,
                ),
              })
            }
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          />
        </div>
      </div>
    </div>
  )
}