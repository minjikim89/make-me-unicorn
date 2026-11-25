export function InvoiceNote({ html }: { html: string }) {
  // notes come from the customer-facing form
  return <div className="note" dangerouslySetInnerHTML={{ __html: html }} />;
}
