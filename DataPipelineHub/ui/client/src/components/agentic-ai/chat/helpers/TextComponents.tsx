// Custom markdown components for styling
export const MarkdownComponents = {
  // Headings
  h1: ({ children }: any) => (
    <h1 className="text-xl font-bold mb-2 text-gray-100">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-lg font-semibold mb-2 text-gray-100">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-base font-semibold mb-1 text-gray-100">{children}</h3>
  ),
  
  // Text formatting
  strong: ({ children }: any) => (
    <strong className="font-bold text-gray-100">{children}</strong>
  ),
  em: ({ children }: any) => (
    <em className="italic text-gray-100">{children}</em>
  ),
  
  // Lists - Updated to handle malformed bullet points
  ul: ({ children }: any) => (
    <ul className="list-disc list-inside mb-2 space-y-1 text-gray-200">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="list-decimal list-inside mb-2 space-y-1 text-gray-200">{children}</ol>
  ),
  li: ({ children }: any) => {
    // Clean up any remaining bullet artifacts in list items
    const cleanChildren = typeof children === 'string' 
      ? children.replace(/^[•\*]\s*/, '') 
      : children;
    return <li className="text-gray-200">{cleanChildren}</li>;
  },
  
  // Code blocks
  code: ({ inline, children }: any) => 
    inline ? (
      <code className="bg-gray-800 text-cyan-300 px-1 py-0.5 rounded text-sm font-mono">
        {children}
      </code>
    ) : (
      <pre className="bg-gray-900 text-cyan-300 p-3 rounded-lg overflow-x-auto mb-2">
        <code className="font-mono text-sm">{children}</code>
      </pre>
    ),
  
  // Blockquotes
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-4 border-primary pl-4 italic text-gray-300 mb-2">
      {children}
    </blockquote>
  ),
  
  // Tables
  table: ({ children }: any) => (
    <div className="overflow-x-auto mb-2">
      <table className="min-w-full border-collapse border border-gray-700">
        {children}
      </table>
    </div>
  ),
  th: ({ children }: any) => (
    <th className="border border-gray-700 px-3 py-2 bg-gray-800 text-gray-100 font-semibold text-left">
      {children}
    </th>
  ),
  td: ({ children }: any) => (
    <td className="border border-gray-700 px-3 py-2 text-gray-200">
      {children}
    </td>
  ),
  
  // Paragraphs
  p: ({ children }: any) => (
    <p className="mb-2 text-gray-200 leading-relaxed">{children}</p>
  ),
  
  // Links
  a: ({ href, children }: any) => (
    <a 
      href={href} 
      target="_blank" 
      rel="noopener noreferrer"
      className="text-primary hover:text-primary/80 underline"
    >
      {children}
    </a>
  ),
};

// Simplified and more precise preprocessing function
export const preprocessText = (text: string): string => {
return text
  // Convert literal \n to actual newlines first
  .replace(/\\n/g, '\n')
  
  // Fix malformed bold markdown patterns (most common LLM issues)
  .replace(/\*{4,}([^*]+)\*{4,}/g, '**$1**') // 4+ asterisks to proper bold
  .replace(/\*{3}([^*]+)\*{3}/g, '**$1**') // ***text*** to **text**
  .replace(/\*{2}([^*]+)\*{3}/g, '**$1**') // **text*** to **text**
  .replace(/\*{3}([^*]+)\*{2}/g, '**$1**') // ***text** to **text**
  
  // Handle bullet point patterns more precisely
  .replace(/^[\s]*\*[\s]+(?=\S)/gm, '• ') // Line-starting * followed by content
  .replace(/^[\s]*\*[\s]*$/gm, '') // Remove lines with only * and whitespace
  
  // Clean up orphaned asterisks at end of lines (but preserve valid markdown)
  .replace(/(?<!\*)\*(?!\*)\s*$/gm, '') // Single trailing * (not part of **)
  .replace(/\*{3,}\s*$/gm, '') // 3+ trailing asterisks
  
  // Remove extra asterisks around already proper bold text
  .replace(/\*+(\*\*[^*]+\*\*)\*+/g, '$1')
  
  // Ensure proper spacing around code blocks
  .replace(/```(\w+)?\n/g, '\n```$1\n')
  .replace(/\n```\s*$/gm, '\n```\n')
  
  .trim();
};