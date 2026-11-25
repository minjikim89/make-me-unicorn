import DOMPurify from "isomorphic-dompurify";

export function InvoiceNote({ html }: { html: string }) {
  return <div className="note" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />;
}
