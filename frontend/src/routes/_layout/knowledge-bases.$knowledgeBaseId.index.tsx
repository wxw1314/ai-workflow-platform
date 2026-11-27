
import { useEffect, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  ChevronRight,
  FileText,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react"

import {
  DocumentsService,
  KnowledgeBasesService,
} from "@/client"
import type {
  DocumentChunkPublic,
  DocumentPublic,
  KnowledgeBasePublic,
} from "@/client"

export const Route = createFileRoute(
  "/_layout/knowledge-bases/$knowledgeBaseId/",
)({
  component: KnowledgeBaseDetailPage,
})

function formatFileSize(size?: number | null) {
  if (size == null) return "-"
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function KnowledgeBaseDetailPage() {
  const { knowledgeBaseId } = Route.useParams()

  const [knowledgeBase, setKnowledgeBase] =
    useState<KnowledgeBasePublic | null>(null)
  const [documents, setDocuments] = useState<DocumentPublic[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [error, setError] = useState("")
  const [expandedDocumentId, setExpandedDocumentId] = useState<string | null>(
    null,
  )
  const [chunks, setChunks] = useState<Record<string, DocumentChunkPublic[]>>(
    {},
  )
  const [loadingChunksId, setLoadingChunksId] = useState<string | null>(null)

  async function loadData() {
    setLoading(true)
    setError("")

    try {
      const [kbResult, documentResult] = await Promise.all([
        KnowledgeBasesService.basesReadKnowledgeBase({
          path: { id: knowledgeBaseId },
        }),
        DocumentsService.readDocuments({
          path: { knowledge_base_id: knowledgeBaseId },
          query: { skip: 0, limit: 100 },
        }),
      ])

      setKnowledgeBase(kbResult.data)
      setDocuments(documentResult.data.data)
    } catch (err) {
      console.error(err)
      setError("加载知识库或文档失败。")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [knowledgeBaseId])

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError("")

    try {
      await DocumentsService.uploadDocument({
        path: { knowledge_base_id: knowledgeBaseId },
        body: { file },
      })

      await loadData()
    } catch (err) {
      console.error(err)
      setError("文档上传失败，请检查文件格式和大小。")
    } finally {
      setUploading(false)
      event.target.value = ""
    }
  }

  async function handleProcess(document: DocumentPublic) {
    setProcessingId(document.id)
    setError("")

    try {
      const result = await DocumentsService.processDocumentEndpoint({
        path: {
          knowledge_base_id: knowledgeBaseId,
          document_id: document.id,
        },
      })

      setChunks((previous) => ({
        ...previous,
        [document.id]: result.data.data,
      }))
      setExpandedDocumentId(document.id)
    } catch (err) {
      console.error(err)
      setError(`处理文档「${document.filename}」失败。`)
    } finally {
      setProcessingId(null)
    }
  }

  async function handleLoadChunks(document: DocumentPublic) {
    if (expandedDocumentId === document.id) {
      setExpandedDocumentId(null)
      return
    }

    setExpandedDocumentId(document.id)

    if (chunks[document.id]) return

    setLoadingChunksId(document.id)

    try {
      const result = await DocumentsService.readDocumentChunks({
        path: {
          knowledge_base_id: knowledgeBaseId,
          document_id: document.id,
        },
        query: { skip: 0, limit: 100 },
      })

      setChunks((previous) => ({
        ...previous,
        [document.id]: result.data.data,
      }))
    } catch (err) {
      console.error(err)
      setError("读取文档分块失败。")
    } finally {
      setLoadingChunksId(null)
    }
  }

  async function handleDelete(document: DocumentPublic) {
    const confirmed = window.confirm(
      `确定删除文档「${document.filename}」吗？`,
    )
    if (!confirmed) return

    try {
      await DocumentsService.removeDocument({
        path: {
          knowledge_base_id: knowledgeBaseId,
          document_id: document.id,
        },
      })

      setChunks((previous) => {
        const next = { ...previous }
        delete next[document.id]
        return next
      })

      if (expandedDocumentId === document.id) {
        setExpandedDocumentId(null)
      }

      await loadData()
    } catch (err) {
      console.error(err)
      setError("删除文档失败。")
    }
  }

  if (loading) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        正在加载知识库...
      </div>
    )
  }

  if (!knowledgeBase) {
    return (
      <div className="space-y-4 p-6">
        <p className="text-destructive">
          {error || "知识库不存在或无权访问。"}
        </p>
        <Link to="/knowledge-bases" className="text-primary hover:underline">
          返回知识库列表
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link
          to="/knowledge-bases"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={16} />
          返回知识库列表
        </Link>

        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{knowledgeBase.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {knowledgeBase.description || "暂无描述"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/knowledge-bases/$knowledgeBaseId/agent"
              params={{ knowledgeBaseId }}
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              <Bot size={16} />
              打开 Agent
            </Link>

            <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
              <Upload size={16} />
              {uploading ? "上传中..." : "上传文档"}
              <input
                type="file"
                accept=".pdf,.txt,.docx"
                className="hidden"
                disabled={uploading}
                onChange={handleUpload}
              />
            </label>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="rounded-lg border">
        <div className="flex items-center justify-between border-b p-4">
          <div>
            <h2 className="font-semibold">文档管理</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              共 {documents.length} 个文档
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadData()}
            className="rounded-md border p-2 hover:bg-muted"
            title="刷新"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText
              size={36}
              className="mx-auto mb-3 text-muted-foreground"
            />
            <p className="font-medium">还没有上传文档</p>
            <p className="mt-1 text-sm text-muted-foreground">
              上传 PDF、TXT 或 DOCX 文件，开始构建知识库。
            </p>
          </div>
        ) : (
          <div className="divide-y">
            {documents.map((document) => {
              const expanded = expandedDocumentId === document.id
              const documentChunks = chunks[document.id] ?? []

              return (
                <div key={document.id}>
                  <div className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <button
                      type="button"
                      onClick={() => void handleLoadChunks(document)}
                      className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    >
                      {expanded ? (
                        <ChevronDown size={18} />
                      ) : (
                        <ChevronRight size={18} />
                      )}

                      <FileText
                        size={20}
                        className="shrink-0 text-muted-foreground"
                      />

                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">
                          {document.filename}
                        </span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {formatFileSize(document.size)}
                          {document.content_type
                            ? ` · ${document.content_type}`
                            : ""}
                        </span>
                      </span>
                    </button>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={processingId === document.id}
                        onClick={() => void handleProcess(document)}
                        className="rounded-md border px-3 py-2 text-xs hover:bg-muted disabled:opacity-50"
                      >
                        {processingId === document.id
                          ? "处理中..."
                          : "解析并向量化"}
                      </button>

                      <button
                        type="button"
                        onClick={() => void handleDelete(document)}
                        className="rounded-md border p-2 text-destructive hover:bg-destructive/5"
                        title="删除文档"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>

                  {expanded && (
                    <div className="space-y-3 bg-muted/30 p-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold">
                          文档分块 ({documentChunks.length})
                        </h3>
                        {loadingChunksId === document.id && (
                          <span className="text-xs text-muted-foreground">
                            加载中...
                          </span>
                        )}
                      </div>

                      {loadingChunksId === document.id ? (
                        <p className="text-sm text-muted-foreground">
                          正在读取分块...
                        </p>
                      ) : documentChunks.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          暂无分块。请先点击“解析并向量化”。
                        </p>
                      ) : (
                        documentChunks.map((chunk) => (
                          <div
                            key={chunk.id}
                            className="rounded-md border bg-background p-4"
                          >
                            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                              <span className="text-xs font-semibold">
                                Chunk #{chunk.chunk_index}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {chunk.character_count} 字符
                              </span>
                            </div>

                            <p className="whitespace-pre-wrap break-words text-sm leading-6">
                              {chunk.content}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
