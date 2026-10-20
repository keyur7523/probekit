/** Indeterminate working label: "Saving" with a sweeping shine and counting dots. */
export default function Working({ children }: { children: string }) {
  return (
    <span className="working" role="status">
      <span className="working-text">{children}</span>
      <span className="working-dots" aria-hidden="true" />
    </span>
  )
}
