import { ModelCapabilities } from "./ModelCapabilities";
import { ModelCard } from "./ModelCard";
import type { ModelsResponse } from "../../api/system";
import type { ChatMode } from "../../types/chat";

type ModelSectionProps = {
  chatMode: ChatMode;
  kbName: string;
  models: ModelsResponse | null;
};

/** 用途：负责 ModelSection 的界面或数据处理职责。 */
export function ModelSection({ chatMode, kbName, models }: ModelSectionProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <>
      <ModelCard chatMode={chatMode} models={models} />
      <ModelCapabilities kbName={kbName} models={models} />
    </>
  );
}
