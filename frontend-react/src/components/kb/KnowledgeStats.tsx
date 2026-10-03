import { useI18n } from "../../i18n";

type KnowledgeStatsProps = {
  documentsCount: number;
  failedCount: number;
  indexedCount: number;
  totalChunks: number;
};

export function KnowledgeStats({
  documentsCount,
  failedCount,
  indexedCount,
  totalChunks
}: KnowledgeStatsProps) {
  const { t } = useI18n();

  return (
    <div className="kb-stats grid grid-cols-4 gap-[10px] [grid-area:stats] max-[1100px]:grid-cols-2 max-[720px]:grid-cols-1 [&>article]:rounded-[18px] [&>article]:border [&>article]:border-solid [&>article]:border-mc-border-subtle [&>article]:bg-[color-mix(in_srgb,var(--color-bg-surface)_88%,transparent)] [&>article]:p-mc-4 [&>article]:[box-shadow:none] [&_span]:block [&_span]:text-mc-caption [&_span]:font-[850] [&_span]:text-mc-muted [&_span]:uppercase [&_strong]:mt-mc-2 [&_strong]:block [&_strong]:text-[26px] [&_strong]:font-[740] [&_strong]:text-mc-text">
      <article>
        <span>{t("kb.documents")}</span>
        <strong>{documentsCount}</strong>
      </article>
      <article>
        <span>{t("kb.indexed")}</span>
        <strong>{indexedCount}</strong>
      </article>
      <article>
        <span>{t("kb.chunks")}</span>
        <strong>{totalChunks}</strong>
      </article>
      <article>
        <span>{t("kb.failed")}</span>
        <strong>{failedCount}</strong>
      </article>
    </div>
  );
}
