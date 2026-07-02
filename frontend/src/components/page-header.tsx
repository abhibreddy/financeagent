export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold">{title}</h1>
      {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
    </header>
  );
}
