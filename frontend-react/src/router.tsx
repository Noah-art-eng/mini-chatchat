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

/** 用途：负责 normalizePath 的界面或数据处理职责。 */
function normalizePath(path: string) {
  if (!path) return "/";
  return path.startsWith("/") ? path : `/${path}`;
}

/** 用途：负责 AppRouter 的界面或数据处理职责。 */
export function AppRouter({
  children,
  initialPath
}: {
  children: ReactNode;
  initialPath?: string;
}) {
  const [pathname, setPathname] = useState(() =>
    /** 用途：负责 normalizePath 的界面或数据处理职责。 */
    normalizePath(initialPath ?? window.location.pathname)
  );

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    /** 用途：负责 handlePopState 的界面或数据处理职责。 */
    function handlePopState() {
      /** 用途：负责 setPathname 的界面或数据处理职责。 */
      setPathname(normalizePath(window.location.pathname));
    }

    window.addEventListener("popstate", handlePopState);
    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((to: string, options: NavigateOptions = {}) => {
    const nextPath = normalizePath(to);
    if (nextPath === window.location.pathname) {
      /** 用途：负责 setPathname 的界面或数据处理职责。 */
      setPathname(nextPath);
      return;
    }

    if (options.replace) {
      window.history.replaceState({}, "", nextPath);
    } else {
      window.history.pushState({}, "", nextPath);
    }
    /** 用途：负责 setPathname 的界面或数据处理职责。 */
    setPathname(nextPath);
  }, []);

  const value = useMemo(
    () => ({
      location: { pathname },
      navigate
    }),
    [navigate, pathname]
  );

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
  );
}

/** 用途：负责 useLocation 的界面或数据处理职责。 */
export function useLocation() {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useLocation must be used within AppRouter");
  }
  return context.location;
}

/** 用途：负责 useNavigate 的界面或数据处理职责。 */
export function useNavigate() {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useNavigate must be used within AppRouter");
  }
  return context.navigate;
}

/** 用途：负责 Link 的界面或数据处理职责。 */
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

  /** 用途：负责 handleClick 的界面或数据处理职责。 */
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
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
    /** 用途：负责 navigate 的界面或数据处理职责。 */
    navigate(to);
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <a className={className} href={to} onClick={handleClick}>
      {children}
    </a>
  );
}
