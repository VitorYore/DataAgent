import { EmptyState } from './EmptyState'
import { SectionHeader } from './SectionHeader'

export function PagePlaceholder({ title, description }: { title: string; description: string }) {
  return <><SectionHeader title={title} description={description} /><EmptyState title="Área em preparação" description="As análises estarão disponíveis aqui em uma próxima etapa." /></>
}
