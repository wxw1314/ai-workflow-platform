import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute(
  "/_layout/knowledge-bases/$knowledgeBaseId",
)({
  component: KnowledgeBaseLayout,
})

function KnowledgeBaseLayout() {
  return <Outlet />
}