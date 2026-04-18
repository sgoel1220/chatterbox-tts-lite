export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Workflow {id}</h1>
      <p className="text-muted-foreground">Workflow detail coming soon.</p>
    </div>
  );
}
