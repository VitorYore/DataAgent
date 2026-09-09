export function SectionHeader({ title, description }: { title: string; description: string }) {
  return <div className="mb-8"><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-muted">{description}</p></div>
}
