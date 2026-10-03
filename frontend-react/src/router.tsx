import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";

type NavigateOptions = {
  replace?: boolean;
};

type RouterContextValue = {
  location: {
    pathname: string;
  };
  navigate: (to: string, options?: NavigateOptions) => void;
};

const RouterContext = createContext<RouterContextValue | null>(null);

function normalizePath(path: string) {
  // 所有内部路由统一成以 / 开头的 pathname，避免 history 和界面状态出现两种写法。
  if (!path) return "/";
  return path.startsWith("/") ? path : `/${path}`;
}

export function AppRouter({
  children,
  initialPath
}: {
  children: ReactNode;
  initialPath?: string;
}) {
  // 这个轻量路由只管理 pathname，不引入额外路由库；浏览器前进/后退仍由 popstate 同步。
  const [pathname, setPathname] = useState(() =>
    normalizePath(initialPath ?? window.location.pathname)
  );

  useEffect(() => {
    function handlePopState() {
      setPathname(normalizePath(window.location.pathname));
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((to: string, options: NavigateOptions = {}) => {
    // 先写浏览器 history，再更新 React 状态，让地址栏和当前页面始终指向同一路由。
    const nextPath = normalizePath(to);
    if (nextPath === window.location.pathname) {
      setPathname(nextPath);
      return;
    }

    if (options.replace) {
      window.history.replaceState({}, "", nextPath);
    } else {
      window.history.pushState({}, "", nextPath);
    }
    setPathname(nextPath);
  }, []);

  const value = useMemo(
    () => ({
      location: { pathname },
      navigate
    }),
    [navigate, pathname]
  );

  return (
    <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
  );
}

export function useLocation() {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useLocation must be used within AppRouter");
  }
  return context.location;
}

export function useNavigate() {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useNavigate must be used within AppRouter");
  }
  return context.navigate;
}

export function Link({
  children,
  className,
  to
}: {
  children: ReactNode;
  className?: string;
  to: string;
}) {
  const navigate = useNavigate();

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    // 只接管普通左键点击；新标签页和组合键继续使用浏览器原生链接行为。
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.altKey ||
      event.ctrlKey ||
      event.shiftKey
    ) {
      return;
    }

    event.preventDefault();
    navigate(to);
  }

  return (
    <a className={className} href={to} onClick={handleClick}>
      {children}
    </a>
  );
}
