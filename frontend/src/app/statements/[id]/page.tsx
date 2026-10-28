import { ReviewWorkspace } from "@/components/ReviewWorkspace";

export default async function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReviewWorkspace id={id} />;
}
