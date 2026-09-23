import { useEffect, useState } from "react";
import {
  listOAuthProviders,
  type OAuthProviderStatus
} from "../api/auth";
import { API_BASE } from "../api/client";
import { Button } from "../components/ui";
import { useI18n } from "../i18n";

type OAuthButtonsProps = {
  mode: "login" | "register";
};

/** 用途：负责 providerIcon 的界面或数据处理职责。 */
function providerIcon(provider: string) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <span className="oauth-provider-mark" aria-hidden="true">
      {provider === "github" ? "GH" : "G"}
    </span>
  );
}

/** 用途：负责 OAuthButtons 的界面或数据处理职责。 */
export function OAuthButtons({ mode }: OAuthButtonsProps) {
  const { t } = useI18n();
  const [providers, setProviders] = useState<OAuthProviderStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    let ignore = false;
    /** 用途：负责 listOAuthProviders 的界面或数据处理职责。 */
    listOAuthProviders()
      .then(response => {
        if (!ignore) setProviders(response.providers);
      })
      .catch(() => {
        if (!ignore) setProviders([]);
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });
    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => {
      ignore = true;
    };
  }, []);

  /** 用途：负责 startOAuth 的界面或数据处理职责。 */
  function startOAuth(provider: string) {
    window.location.assign(`${API_BASE}/auth/oauth/${provider}`);
  }

  if (isLoading) {
    return <div className="oauth-loading">{t("auth.loadingProviders")}</div>;
  }

  if (providers.length === 0) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="oauth-auth-section" data-testid="oauth-auth-section">
      <div className="oauth-divider">
        <span>{t("auth.orContinueWith")}</span>
      </div>
      <div className="oauth-button-grid">
        {providers.map(provider => (
          <Button
            disabled={!provider.configured}
            key={provider.provider}
            onClick={() => startOAuth(provider.provider)}
            type="button"
            variant="secondary"
          >
            {providerIcon(provider.provider)}
            {mode === "login"
              ? t(`auth.oauthSignIn.${provider.provider}`)
              : t(`auth.oauthRegister.${provider.provider}`)}
          </Button>
        ))}
      </div>
    </div>
  );
}
