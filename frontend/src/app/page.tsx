import { RecentStatements } from "@/components/RecentStatements";
import { TopBar } from "@/components/TopBar";
import { UploadForm } from "@/components/UploadForm";

export default function UploadPage() {
  return (
    <>
      <TopBar step={1} />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="text-2xl font-semibold">Sort your rental statements for Schedule E</h1>
        <p className="mb-8 mt-2 max-w-[72ch] text-muted">
          Upload a bank or credit card statement. We will sort every transaction and ask you about the
          ones we are unsure of.
        </p>
        <UploadForm />
        <h2 className="mb-2 mt-12 text-lg font-semibold">Recent statements</h2>
        <RecentStatements />
      </main>
    </>
  );
}
