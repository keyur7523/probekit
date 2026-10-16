export function DemoBadge() {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide bg-amber-100 text-amber-800 border border-amber-300"
      title="Seeded run with scripted outputs and evaluator results. Not real model results."
    >
      Demo data
    </span>
  )
}

export function DemoDataNotice({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-amber-50 border border-amber-200 rounded-xl p-4 ${className}`}>
      <p className="text-amber-800 text-sm">
        <span className="font-semibold">Sample data for illustration — not real model results.</span>{' '}
        Runs marked <span className="font-semibold">DEMO DATA</span> use scripted outputs and scripted
        evaluator verdicts, and are excluded from regression and annotation-agreement metrics.
      </p>
    </div>
  )
}
