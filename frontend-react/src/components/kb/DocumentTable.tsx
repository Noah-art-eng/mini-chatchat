import { EmptyKnowledgeState } from "./EmptyKnowledgeState";
import { DocumentRow } from "./DocumentRow";
import type { KnowledgeFile } from "../../types/kb";

type DocumentTableProps = {
  activeDocumentAction: string | null;
  documents: KnowledgeFile[];
  hasKnowledgeBase?: boolean;
  isLoading: boolean;
  onDelete: (filename: string) => void;
  onDownload: (filename: string) => void;
  onReindex: (file: KnowledgeFile) => void;
  onSelectDocument: (file: KnowledgeFile) => void;
  selectedDocument: KnowledgeFile | null;
};

/** 用途：负责 DocumentTable 的界面或数据处理职责。 */
export function DocumentTable({
  activeDocumentAction,
  documents,
  hasKnowledgeBase = true,
  isLoading,
  onDelete,
  onDownload,
  onReindex,
  onSelectDocument,
  selectedDocument
}: DocumentTableProps) {
  if (!isLoading && documents.length === 0) {
    return <EmptyKnowledgeState hasKnowledgeBase={hasKnowledgeBase} />;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="document-list" data-testid="documents" id="documents">
      {documents.map(file => (
        <DocumentRow
          activeDocumentAction={activeDocumentAction}
          file={file}
          isSelected={selectedDocument?.filename === file.filename}
          key={file.filename}
          onDelete={onDelete}
          onDownload={onDownload}
          onReindex={onReindex}
          onSelect={onSelectDocument}
        />
      ))}
    </div>
  );
}
