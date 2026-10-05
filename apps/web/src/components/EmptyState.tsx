import "./states.css"
import { Btn, Icon, RoutePattern } from "./kit"

/** Centered block: two routes at 12% behind a 48 px icon, heading, one sentence, one primary button, optional quiet link (05 4.16). */
export function EmptyState({
  icon,
  title,
  body,
  action,
  link,
}: {
  icon: string
  title: string
  body: string
  /** Left out when the person cannot act, such as a viewer on a trip. */
  action?: { label: string; onClick: () => void }
  link?: { label: string; href: string }
}) {
  return (
    <section className="state">
      <div className="state__art">
        <RoutePattern
          className="state__routes"
          viewBox="0 0 160 96"
          a="M4 80 C 40 80, 40 20, 80 40 S 130 20, 156 10"
          b="M4 60 C 50 90, 90 70, 110 50 S 140 60, 156 36"
        />
        <Icon name={icon} size={48} className="state__icon" />
      </div>
      <h2 className="h-heading">{title}</h2>
      <p className="state__body">{body}</p>
      <div className="state__actions">
        {action && <Btn variant="primary" onClick={action.onClick}>{action.label}</Btn>}
        {link && <a className="state__link" href={link.href}>{link.label}</a>}
      </div>
    </section>
  )
}
