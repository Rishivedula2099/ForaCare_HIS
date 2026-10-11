import { redirect } from "next/navigation";

// The Documents nav entry lands on template management until other document
// tooling (history, reprint) gets its own screen.
export default function DocumentsPage() {
  redirect("/documents/templates");
}
