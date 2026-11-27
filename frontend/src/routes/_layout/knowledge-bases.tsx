
import { useEffect, useState } from "react"
import {  createFileRoute,
  Link,
  Outlet,
  useRouterState
 } from "@tanstack/react-router"
import { Database, Pencil, Plus, Trash2 } from "lucide-react"

import {
  KnowledgeBasesService,
} from "@/client"
import type { KnowledgeBasePublic } from "@/client"

export const Route = createFileRoute("/_layout/knowledge-bases")({
  component: KnowledgeBasesPage,
})

function KnowledgeBasesPage() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  const isDetailPage = /^\/knowledge-bases\/[^/]+(?:\/agent)?\/?$/.test(pathname)  
  const [items, setItems] = useState<KnowledgeBasePublic[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [editing, setEditing] = useState<KnowledgeBasePublic | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  async function loadKnowledgeBases() {
    setLoading(true)
    setError("")

    try {
      const result = await KnowledgeBasesService.basesReadKnowledgeBases({
        query: { skip: 0, limit: 100 },
      })
      setItems(result.data.data)
    } catch (err) {
      console.error(err)
      setError("加载知识库失败，请检查网络或登录状态。")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadKnowledgeBases()
  }, [])

  function openCreateForm() {
    setEditing(null)
    setName("")
    setDescription("")
    setShowForm(true)
  }

  function openEditForm(item: KnowledgeBasePublic) {
    setEditing(item)
    setName(item.name)
    setDescription(item.description ?? "")
    setShowForm(true)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!name.trim()) {
      setError("请输入知识库名称。")
      return
    }

    setSaving(true)
    setError("")

    try {
      if (editing) {
        await KnowledgeBasesService.basesUpdateKnowledgeBase({
          path: { id: editing.id },
          body: {
            name: name.trim(),
            description: description.trim() || null,
          },
        })
      } else {
        await KnowledgeBasesService.basesCreateKnowledgeBase({
          body: {
            name: name.trim(),
            description: description.trim() || null,
          },
        })
      }

      setShowForm(false)
      setEditing(null)
      await loadKnowledgeBases()
    } catch (err) {
      console.error(err)
      setError("保存知识库失败，请稍后重试。")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(item: KnowledgeBasePublic) {
    const confirmed = window.confirm(
      `确定删除知识库「${item.name}」吗？此操作可能同时删除其中的文档和向量数据。`,
    )

    if (!confirmed) return

    try {
      await KnowledgeBasesService.basesDeleteKnowledgeBase({
        path: { id: item.id },
      })
      await loadKnowledgeBases()
    } catch (err) {
      console.error(err)
      setError("删除知识库失败。")
    }
  }

  if (isDetailPage) {
    return <Outlet />
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">知识库</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理知识库、上传文档，并为 Agent 提供 RAG 检索能力。
          </p>
        </div>

        <button
          type="button"
          onClick={openCreateForm}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          <Plus size={16} />
          新建知识库
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-lg border p-5"
        >
          <h2 className="font-semibold">
            {editing ? "编辑知识库" : "新建知识库"}
          </h2>

          <div className="space-y-2">
            <label htmlFor="kb-name" className="text-sm font-medium">
              名称
            </label>
            <input
              id="kb-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：产品技术文档"
              required
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="kb-description" className="text-sm font-medium">
              描述
            </label>
            <textarea
              id="kb-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="描述这个知识库的用途..."
              rows={3}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              {saving ? "保存中..." : "保存"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-md border px-4 py-2 text-sm"
            >
              取消
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          正在加载知识库...
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <Database className="mx-auto mb-3 text-muted-foreground" size={36} />
          <p className="font-medium">还没有知识库</p>
          <p className="mt-1 text-sm text-muted-foreground">
            创建一个知识库，开始整理你的内部文档。
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <div key={item.id} className="rounded-lg border p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="truncate font-semibold">{item.name}</h2>
                  <p className="mt-2 line-clamp-3 min-h-12 text-sm text-muted-foreground">
                    {item.description || "暂无描述"}
                  </p>
                </div>
                <Database className="shrink-0 text-muted-foreground" size={22} />
              </div>

              <div className="mt-5 flex items-center justify-between border-t pt-4">
                <Link
                  to="/knowledge-bases/$knowledgeBaseId"
                  params={{ knowledgeBaseId: item.id }}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  管理文档 →
                </Link>

                <div className="flex gap-2">
                  <button
                    type="button"
                    title="编辑"
                    onClick={() => openEditForm(item)}
                    className="rounded-md border p-2 hover:bg-muted"
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    type="button"
                    title="删除"
                    onClick={() => void handleDelete(item)}
                    className="rounded-md border p-2 text-destructive hover:bg-destructive/5"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <p className="mt-3 truncate text-xs text-muted-foreground">
                ID: {item.id}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
