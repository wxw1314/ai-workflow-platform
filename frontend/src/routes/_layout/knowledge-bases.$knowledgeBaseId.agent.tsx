
import { useCallback, useEffect, useRef, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  Bot,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Square,
  Trash2,
  User,
  Wrench,
} from "lucide-react"

import { ConversationsService } from "@/client"
import type { ConversationPublic } from "@/client"

export const Route = createFileRoute(
  "/_layout/knowledge-bases/$knowledgeBaseId/agent",
)({
  component: KnowledgeBaseAgentPage,
})

interface ConversationMessage {
  type: "human" | "ai"
  content: string
}

interface ConversationMessagesResponse {
  data: ConversationMessage[]
  count: number
}

interface AgentSource {
  [key: string]: unknown
}

interface ToolStatus {
  tool: string
  tool_call_id?: string | null
  status: "running" | "success" | "degraded" | "error"
  error?: string | null
}

interface RetryStatus {
  tool: string
  service: string
  attempt: number
  delay: number
  message: string
}

interface ChatMessage {
  id: string
  type: "human" | "ai"
  content: string
  sources?: AgentSource[]
  tools?: ToolStatus[]
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? ""

function getAccessToken() {
  return localStorage.getItem("access_token") || ""
}

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function formatTime(seconds: number) {
  return `${seconds.toFixed(1)} 秒`
}

/**
 * 解析标准 SSE 数据。
 *
 * 服务端格式：
 * event: token
 * data: {"content":"你好"}
 *
 * 空行代表一个事件结束。
 */
async function readSSEStream(
  response: Response,
  onEvent: (event: string, data: unknown) => void,
  signal: AbortSignal,
) {
  if (!response.body) {
    throw new Error("当前浏览器不支持读取流式响应。")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  let buffer = ""

  function dispatchEvent(frame: string) {
    let eventName = "message"
    const dataLines: string[] = []

    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart())
      }
    }

    if (dataLines.length === 0) return

    const rawData = dataLines.join("\n")

    try {
      onEvent(eventName, JSON.parse(rawData))
    } catch {
      console.error("无法解析 SSE 数据：", rawData)
    }
  }

  try {
    while (true) {
      if (signal.aborted) break

      const { value, done } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // 同时兼容 LF 和 CRLF 格式。
      const normalized = buffer.replace(/\r\n/g, "\n")
      const frames = normalized.split("\n\n")

      buffer = frames.pop() ?? ""

      for (const frame of frames) {
        if (frame.trim()) {
          dispatchEvent(frame)
        }
      }
    }

    buffer += decoder.decode()

    if (buffer.trim()) {
      dispatchEvent(buffer)
    }
  } finally {
    if (signal.aborted) {
      await reader.cancel().catch(() => undefined)
    }

    reader.releaseLock()
  }
}

function KnowledgeBaseAgentPage() {
  const { knowledgeBaseId } = Route.useParams()

  const [conversations, setConversations] = useState<ConversationPublic[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    null,
  )

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")

  const [loadingConversations, setLoadingConversations] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [sending, setSending] = useState(false)

  const [error, setError] = useState("")
  const [retryStatus, setRetryStatus] = useState<RetryStatus | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const activeConversationIdRef = useRef<string | null>(null)

  useEffect(() => {
    activeConversationIdRef.current = activeConversationId
  }, [activeConversationId])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // 加载当前知识库的会话列表。
  const loadConversations = useCallback(async () => {
    setLoadingConversations(true)
    setError("")

    try {
      const result = await ConversationsService.readConversations({
        query: {
          knowledge_base_id: knowledgeBaseId,
          skip: 0,
          limit: 100,
        },
      })

      setConversations(result.data.data)
    } catch (err) {
      console.error(err)
      setError("加载会话列表失败。")
    } finally {
      setLoadingConversations(false)
    }
  }, [knowledgeBaseId])

  useEffect(() => {
    void loadConversations()
  }, [loadConversations])

  // 加载指定会话的历史消息。
  const loadMessages = useCallback(async (conversationId: string) => {
    setLoadingMessages(true)
    setError("")
    setMessages([])

    try {
      const result =
        await ConversationsService.readConversationMessages({
          path: {
            conversation_id: conversationId,
          },
        })

      const response = result.data as ConversationMessagesResponse

      setMessages(
        response.data.map((message, index) => ({
          id: `${conversationId}-${index}`,
          type: message.type,
          content: message.content,
        })),
      )
    } catch (err) {
      console.error(err)
      setError("加载历史消息失败。")
    } finally {
      setLoadingMessages(false)
    }
  }, [])

  // 切换会话。
  async function handleSelectConversation(conversationId: string) {
    if (sending) {
      abortControllerRef.current?.abort()
    }

    setActiveConversationId(conversationId)
    activeConversationIdRef.current = conversationId
    setRetryStatus(null)

    await loadMessages(conversationId)
  }

  // 创建会话。
  async function handleCreateConversation() {
    setCreatingConversation(true)
    setError("")

    try {
      const result = await ConversationsService.createConversation({
        body: {
          knowledge_base_id: knowledgeBaseId,
          title: "新对话",
        },
      })

      const conversation = result.data

      setConversations((previous) => [conversation, ...previous])
      setActiveConversationId(conversation.id)
      activeConversationIdRef.current = conversation.id
      setMessages([])
      setRetryStatus(null)
    } catch (err) {
      console.error(err)
      setError("创建会话失败。")
    } finally {
      setCreatingConversation(false)
    }
  }

  // 删除会话。
  async function handleDeleteConversation(
    event: React.MouseEvent,
    conversation: ConversationPublic,
  ) {
    event.stopPropagation()

    const confirmed = window.confirm(
      `确定删除会话「${conversation.title}」吗？`,
    )

    if (!confirmed) return

    if (activeConversationId === conversation.id && sending) {
      abortControllerRef.current?.abort()
    }

    try {
      await ConversationsService.deleteConversation({
        path: {
          conversation_id: conversation.id,
        },
      })

      const remaining = conversations.filter(
        (item) => item.id !== conversation.id,
      )

      setConversations(remaining)

      if (activeConversationId === conversation.id) {
        setActiveConversationId(null)
        activeConversationIdRef.current = null
        setMessages([])
        setRetryStatus(null)

        if (remaining.length > 0) {
          await handleSelectConversation(remaining[0].id)
        }
      }
    } catch (err) {
      console.error(err)
      setError("删除会话失败。")
    }
  }

  // 处理 SSE 事件。
  function handleAgentEvent(
    event: string,
    data: unknown,
    assistantMessageId: string,
  ) {
    const payload = data as Record<string, unknown>

    switch (event) {
      case "start":
        setRetryStatus(null)
        break

      case "token": {
        const content = payload.content

        if (typeof content !== "string" || !content) break

        setMessages((previous) =>
          previous.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: message.content + content }
              : message,
          ),
        )
        break
      }

      case "tool_start": {
        const tool = String(payload.tool ?? "unknown")
        const toolCallId = payload.tool_call_id as string | null

        setRetryStatus(null)

        setMessages((previous) =>
          previous.map((message) => {
            if (message.id !== assistantMessageId) return message

            const tools = message.tools ?? []

            return {
              ...message,
              tools: [
                ...tools,
                {
                  tool,
                  tool_call_id: toolCallId,
                  status: "running",
                },
              ],
            }
          }),
        )
        break
      }

      case "tool_end": {
        const tool = String(payload.tool ?? "unknown")
        const toolCallId = payload.tool_call_id as string | null
        const status = String(payload.status ?? "success") as ToolStatus["status"]

        setMessages((previous) =>
          previous.map((message) => {
            if (message.id !== assistantMessageId) return message

            return {
              ...message,
              tools: (message.tools ?? []).map((item) => {
                const matches = toolCallId
                  ? item.tool_call_id === toolCallId
                  : item.tool === tool && item.status === "running"

                return matches
                  ? {
                      ...item,
                      status,
                      error:
                        typeof payload.error === "string"
                          ? payload.error
                          : null,
                    }
                  : item
              }),
            }
          }),
        )
        break
      }

      case "tool_retry":
        setRetryStatus({
          tool: String(payload.tool ?? "unknown"),
          service: String(payload.service ?? "unknown"),
          attempt: Number(payload.attempt ?? 0),
          delay: Number(payload.delay ?? 0),
          message: String(payload.message ?? "服务暂时异常，正在重试。"),
        })
        break

      case "done": {
        const answer = payload.answer
        const sources = Array.isArray(payload.sources)
          ? (payload.sources as AgentSource[])
          : []

        setRetryStatus(null)

        setMessages((previous) =>
          previous.map((message) =>
            message.id === assistantMessageId
              ? {
                  ...message,
                  // token 已经逐步输出；done.answer 用于最终校准。
                  content:
                    typeof answer === "string" ? answer : message.content,
                  sources,
                }
              : message,
          ),
        )
        break
      }

      case "error":
        setError(
          typeof payload.message === "string"
            ? payload.message
            : "Agent 执行失败。",
        )
        break
    }
  }

  // 发送消息并消费 SSE。
  async function handleSendMessage() {
    const query = input.trim()

    if (!query || sending) return

    let conversationId = activeConversationId

    // 第一次提问时自动创建会话。
    if (!conversationId) {
      try {
        const result = await ConversationsService.createConversation({
          body: {
            knowledge_base_id: knowledgeBaseId,
            title: query.slice(0, 40),
          },
        })

        const conversation = result.data

        conversationId = conversation.id

        setConversations((previous) => [conversation, ...previous])
        setActiveConversationId(conversationId)
        activeConversationIdRef.current = conversationId
      } catch (err) {
        console.error(err)
        setError("创建会话失败，无法发送消息。")
        return
      }
    }

    const userMessage: ChatMessage = {
      id: createMessageId(),
      type: "human",
      content: query,
    }

    const assistantMessageId = createMessageId()

    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      type: "ai",
      content: "",
      tools: [],
    }

    setMessages((previous) => [
      ...previous,
      userMessage,
      assistantMessage,
    ])

    setInput("")
    setSending(true)
    setError("")
    setRetryStatus(null)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const token = getAccessToken()

      const response = await fetch(
        `${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}/agent/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
            ...(token
              ? { Authorization: `Bearer ${token}` }
              : {}),
          },
          body: JSON.stringify({
            session_id: conversationId,
            query,
          }),
          signal: controller.signal,
        },
      )

      if (!response.ok) {
        const responseText = await response.text()
        throw new Error(
          responseText || `请求失败：HTTP ${response.status}`,
        )
      }

      await readSSEStream(
        response,
        (event, data) => {
          handleAgentEvent(event, data, assistantMessageId)
        },
        controller.signal,
      )
    } catch (err) {
      if (controller.signal.aborted) {
        // 用户主动停止，不显示为错误。
        setMessages((previous) =>
          previous.filter(
            (message) =>
              message.id !== assistantMessageId ||
              message.content.length > 0 ||
              (message.tools?.length ?? 0) > 0,
          ),
        )
      } else {
        console.error(err)
        setError(
          err instanceof Error ? err.message : "Agent 请求失败。",
        )
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null
      }

      setSending(false)
      setRetryStatus(null)

      // 刷新会话列表，以便后端更新标题或更新时间后同步显示。
      void loadConversations()
    }
  }

  // 停止生成。
  function handleStopGeneration() {
    abortControllerRef.current?.abort()
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] min-h-[600px] overflow-hidden">
      {/* 左侧会话列表 */}
      <aside className="flex w-72 shrink-0 flex-col border-r">
        <div className="border-b p-4">
          <Link
            to="/knowledge-bases/$knowledgeBaseId"
            params={{ knowledgeBaseId }}
            className="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={16} />
            返回知识库
          </Link>

          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Agent 会话</h2>

            <button
              type="button"
              onClick={handleCreateConversation}
              disabled={creatingConversation}
              className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground disabled:opacity-50"
            >
              {creatingConversation ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Plus size={14} />
              )}
              新建
            </button>
          </div>
        </div>

        <div className="flex-1 space-y-1 overflow-y-auto p-2">
          {loadingConversations ? (
            <p className="p-3 text-sm text-muted-foreground">
              正在加载会话...
            </p>
          ) : conversations.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">
              暂无会话，点击新建开始对话。
            </p>
          ) : (
            conversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={() =>
                  void handleSelectConversation(conversation.id)
                }
                className={`group flex cursor-pointer items-center gap-2 rounded-md px-3 py-3 text-sm transition-colors ${
                  activeConversationId === conversation.id
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-muted"
                }`}
              >
                <MessageSquare
                  size={16}
                  className="shrink-0 text-muted-foreground"
                />

                <span className="min-w-0 flex-1 truncate">
                  {conversation.title}
                </span>

                <button
                  type="button"
                  title="删除会话"
                  onClick={(event) =>
                    void handleDeleteConversation(event, conversation)
                  }
                  className="shrink-0 rounded p-1 text-muted-foreground opacity-0 hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* 右侧聊天区域 */}
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b px-6 py-4">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Bot size={20} />
          </div>

          <div>
            <h1 className="font-semibold">知识库 Agent</h1>
            <p className="text-xs text-muted-foreground">
              基于当前知识库进行智能问答
            </p>
          </div>
        </header>

        {error && (
          <div className="mx-6 mt-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            {error}
            <button
              type="button"
              onClick={() => setError("")}
              className="ml-3 underline"
            >
              关闭
            </button>
          </div>
        )}

        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-4xl space-y-6">
            {loadingMessages ? (
              <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted-foreground">
                <Loader2 size={16} className="animate-spin" />
                正在加载历史消息...
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <div className="mb-4 flex size-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Bot size={32} />
                </div>

                <h2 className="text-lg font-semibold">
                  你好，我是知识库 Agent
                </h2>

                <p className="mt-2 max-w-md text-sm text-muted-foreground">
                  你可以向我提问，我会检索当前知识库中的相关内容，并根据检索结果回答。
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.type === "human"
                      ? "flex-row-reverse"
                      : "flex-row"
                  }`}
                >
                  <div
                    className={`flex size-8 shrink-0 items-center justify-center rounded-full ${
                      message.type === "human"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {message.type === "human" ? (
                      <User size={16} />
                    ) : (
                      <Bot size={17} />
                    )}
                  </div>

                  <div
                    className={`min-w-0 max-w-[85%] space-y-3 ${
                      message.type === "human" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`rounded-xl px-4 py-3 text-sm leading-7 ${
                        message.type === "human"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      {message.content ? (
                        <div className="whitespace-pre-wrap break-words">
                          {message.content}
                        </div>
                      ) : sending && message.type === "ai" ? (
                        <span className="inline-flex items-center gap-2 text-muted-foreground">
                          <Loader2 size={14} className="animate-spin" />
                          正在思考...
                        </span>
                      ) : null}
                    </div>

                    {/* 工具执行状态 */}
                    {message.tools && message.tools.length > 0 && (
                      <div className="space-y-2">
                        {message.tools.map((tool, index) => (
                          <div
                            key={tool.tool_call_id ?? `${tool.tool}-${index}`}
                            className="flex items-start gap-2 rounded-md border px-3 py-2 text-xs"
                          >
                            <Wrench
                              size={14}
                              className="mt-0.5 shrink-0 text-muted-foreground"
                            />

                            <div className="min-w-0">
                              <div className="font-medium">
                                {tool.tool}
                                {tool.status === "running" && (
                                  <span className="ml-2 text-muted-foreground">
                                    执行中...
                                  </span>
                                )}
                                {tool.status === "success" && (
                                  <span className="ml-2 text-green-600">
                                    已完成
                                  </span>
                                )}
                                {tool.status === "degraded" && (
                                  <span className="ml-2 text-amber-600">
                                    降级执行
                                  </span>
                                )}
                                {tool.status === "error" && (
                                  <span className="ml-2 text-destructive">
                                    执行失败
                                  </span>
                                )}
                              </div>

                              {tool.error && (
                                <p className="mt-1 break-words text-muted-foreground">
                                  {tool.error}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 重试状态 */}
                    {retryStatus && sending && message.type === "ai" && (
                      <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
                        <p>{retryStatus.message}</p>
                        <p className="mt-1">
                          {retryStatus.service} · 第 {retryStatus.attempt} 次重试
                          · 等待 {formatTime(retryStatus.delay)}
                        </p>
                      </div>
                    )}

                    {/* 检索来源 */}
                    {message.sources && message.sources.length > 0 && (
                      <details className="rounded-md border px-3 py-2 text-xs">
                        <summary className="cursor-pointer font-medium">
                          参考来源（{message.sources.length}）
                        </summary>

                        <div className="mt-2 space-y-2">
                          {message.sources.map((source, index) => (
                            <pre
                              key={index}
                              className="overflow-x-auto whitespace-pre-wrap break-words rounded bg-muted p-2"
                            >
                              {JSON.stringify(source, null, 2)}
                            </pre>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              ))
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 输入区域 */}
        <div className="border-t p-4">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-end gap-3 rounded-xl border bg-background p-3 shadow-sm">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault()
                    void handleSendMessage()
                  }
                }}
                placeholder="输入问题，按 Enter 发送，Shift + Enter 换行..."
                rows={2}
                disabled={sending}
                className="max-h-40 min-h-12 flex-1 resize-y bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
              />

              {sending ? (
                <button
                  type="button"
                  onClick={handleStopGeneration}
                  className="inline-flex shrink-0 items-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground"
                >
                  <Square size={14} />
                  停止
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => void handleSendMessage()}
                  disabled={!input.trim() || loadingMessages}
                  className="inline-flex shrink-0 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Send size={14} />
                  发送
                </button>
              )}
            </div>

            <p className="mt-2 text-center text-xs text-muted-foreground">
              Agent 的回答由知识库检索结果辅助生成，请注意核对重要信息。
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
