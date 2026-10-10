import { t } from "../../lib/i18n"
import { Icon } from "../kit"
import "./ai.css"

/**
 * The label on AI output (06 section 12.4): "AI suggestion, check details before booking". Use `found` for facts the
 * AI took from a web page ("Found by AI, check the source"). Text always, never color alone.
 */
export function AiLabel({ found = false }: { found?: boolean }) {
  return (
    <p className="ai-label">
      <Icon name="sparkles" size={16} />
      <span>{t(found ? "ai.labelFound" : "ai.label")}</span>
    </p>
  )
}
