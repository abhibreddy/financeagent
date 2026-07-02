import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Markdown renderer with Tailwind-styled elements (agent reports use headings + tables). */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mb-2 mt-1 text-lg font-semibold" {...p} />,
          h2: (p) => <h2 className="mb-2 mt-4 text-base font-semibold" {...p} />,
          h3: (p) => <h3 className="mb-1 mt-3 text-sm font-semibold" {...p} />,
          p: (p) => <p className="my-2" {...p} />,
          ul: (p) => <ul className="my-2 list-disc pl-5" {...p} />,
          ol: (p) => <ol className="my-2 list-decimal pl-5" {...p} />,
          li: (p) => <li className="my-0.5" {...p} />,
          strong: (p) => <strong className="font-semibold" {...p} />,
          hr: () => <hr className="my-3 border-border" />,
          code: (p) => <code className="rounded bg-muted px-1 py-0.5 text-xs" {...p} />,
          table: (p) => (
            <div className="my-3 overflow-x-auto">
              <table className="w-full border-collapse text-xs" {...p} />
            </div>
          ),
          th: (p) => <th className="border border-border bg-muted px-2 py-1 text-left font-medium" {...p} />,
          td: (p) => <td className="border border-border px-2 py-1" {...p} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
