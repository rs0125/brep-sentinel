import ReactMarkdown from "react-markdown";

export default function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown-body panel">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}
