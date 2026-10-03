import { ModelCapabilities } from "./ModelCapabilities";
import { ModelCard } from "./ModelCard";
import type { ModelsResponse } from "../../api/system";
import type { ChatMode } from "../../types/chat";

type ModelSectionProps = {
  chatMode: ChatMode;
  kbName: string;
  models: ModelsResponse | null;
};

export function ModelSection({ chatMode, kbName, models }: ModelSectionProps) {
  return (
    <>
      <ModelCard chatMode={chatMode} models={models} />
      <ModelCapabilities kbName={kbName} models={models} />
    </>
  );
}
