type MarkdownContentProps = {
  content: string;
};

/** 用途：负责 isTableBlock 的界面或数据处理职责。 */
function isTableBlock(lines: string[]) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    lines.length >= 2 &&
    lines[0].includes("|") &&
    /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[1])
  );
}

/** 用途：负责 renderInline 的界面或数据处理职责。 */
function renderInline(text: string) {
  const parts = text.split(/(`[^`]+`)/g);

  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
    }

    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

/** 用途：负责 renderTable 的界面或数据处理职责。 */
function renderTable(lines: string[], key: string) {
  const [headerLine, , ...bodyLines] = lines;
  const headers = headerLine
    .split("|")
    .map(cell => cell.trim())
    .filter(Boolean);
  const rows = bodyLines.map(line =>
    line
      .split("|")
      .map(cell => cell.trim())
      .filter(Boolean)
  );

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="message-table-wrap" key={key}>
      <table className="message-table">
        <thead>
          <tr>
            {headers.map(header => (
              <th key={header}>{renderInline(header)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${key}-row-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${key}-cell-${rowIndex}-${cellIndex}`}>
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 用途：负责 MarkdownContent 的界面或数据处理职责。 */
export function MarkdownContent({ content }: MarkdownContentProps) {
  const blocks: string[][] = [];
  let currentBlock: string[] = [];
  let isInCodeFence = false;

  content.split("\n").forEach(line => {
    if (line.trim().startsWith("```")) {
      isInCodeFence = !isInCodeFence;
      currentBlock.push(line);
      return;
    }

    if (!isInCodeFence && line.trim() === "") {
      if (currentBlock.length > 0) {
        blocks.push(currentBlock);
        currentBlock = [];
      }
      return;
    }

    currentBlock.push(line);
  });

  if (currentBlock.length > 0) {
    blocks.push(currentBlock);
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="message-markdown">
      {blocks.map((block, index) => {
        const key = `markdown-block-${index}`;
        const firstLine = block[0] || "";
        const trimmed = firstLine.trim();
        const isCodeBlock =
          block[0]?.trim().startsWith("```") &&
          block[block.length - 1]?.trim().startsWith("```");

        if (isCodeBlock) {
          const language = block[0].trim().replace("```", "").trim();
          const code = block.slice(1, -1).join("\n");

          /** 用途：负责 return 的界面或数据处理职责。 */
          return (
            <pre className="message-code-block" key={key}>
              {language && <span>{language}</span>}
              <code>{code}</code>
            </pre>
          );
        }

        if (isTableBlock(block)) {
          return renderTable(block, key);
        }

        if (block.every(line => /^[-*]\s+/.test(line.trim()))) {
          /** 用途：负责 return 的界面或数据处理职责。 */
          return (
            <ul key={key}>
              {block.map((line, itemIndex) => (
                <li key={`${key}-item-${itemIndex}`}>
                  {renderInline(line.trim().replace(/^[-*]\s+/, ""))}
                </li>
              ))}
            </ul>
          );
        }

        if (block.every(line => /^\d+\.\s+/.test(line.trim()))) {
          /** 用途：负责 return 的界面或数据处理职责。 */
          return (
            <ol key={key}>
              {block.map((line, itemIndex) => (
                <li key={`${key}-item-${itemIndex}`}>
                  {renderInline(line.trim().replace(/^\d+\.\s+/, ""))}
                </li>
              ))}
            </ol>
          );
        }

        if (trimmed.startsWith(">")) {
          /** 用途：负责 return 的界面或数据处理职责。 */
          return (
            <blockquote key={key}>
              {block.map(line => line.trim().replace(/^>\s?/, "")).join("\n")}
            </blockquote>
          );
        }

        if (/^#{1,3}\s+/.test(trimmed)) {
          const heading = trimmed.replace(/^#{1,3}\s+/, "");

          /** 用途：负责 return 的界面或数据处理职责。 */
          return (
            <h3 className="message-subheading" key={key}>
              {renderInline(heading)}
            </h3>
          );
        }

        return <p key={key}>{renderInline(block.join("\n"))}</p>;
      })}
    </div>
  );
}
