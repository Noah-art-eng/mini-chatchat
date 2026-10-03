import html
import http.client
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .types import ToolResult, ToolSpec


DEFAULT_MAX_CHARS = 4000
MIN_MAX_CHARS = 500
MAX_MAX_CHARS = 8000
MAX_BODY_BYTES = 1_000_000
MAX_REDIRECTS = 5
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 10
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_CONTENT_TYPES = {"text/html", "text/plain"}
INTERNAL_HOST_MARKERS = (
    ".internal",
    ".local",
    ".localhost",
    ".lan",
    ".home",
    ".corp",
    ".intranet",
)
TEXT_TAG_BREAKS = {
    "article",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "p",
    "section",
    "td",
    "th",
    "tr",
}
SKIP_TAGS = {
    "footer",
    "nav",
    "noscript",
    "script",
    "style",
    "svg",
}
SENSITIVE_MARKERS = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
)


class ReadableHTMLParser(HTMLParser):
    """从 HTML 中提取标题和用户可见正文，忽略脚本、导航等非正文内容。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.skip_depth = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        """进入标签时记录正文分隔，并开始跳过隐藏或无关区域。"""
        tag = tag.lower()
        attr_map = {
            name.lower(): value or ""
            for name, value in attrs
        }

        if tag == "title":
            self.in_title = True

        if self.skip_depth or tag in SKIP_TAGS or is_hidden(attr_map):
            self.skip_depth += 1
            return

        if tag in TEXT_TAG_BREAKS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        """离开标签时结束跳过状态，并保留块级内容之间的换行。"""
        tag = tag.lower()

        if tag == "title":
            self.in_title = False

        if self.skip_depth:
            self.skip_depth -= 1
            return

        if tag in TEXT_TAG_BREAKS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        """只收集当前可见区域的文本，标题另存供工具结果展示。"""
        if self.in_title:
            self.title_parts.append(data)

        if not self.skip_depth:
            self.text_parts.append(data)

    def title(self):
        return normalize_text(" ".join(self.title_parts))

    def text(self):
        return normalize_text(" ".join(self.text_parts))


def is_hidden(attrs: dict) -> bool:
    """识别页面明确标为隐藏的节点，避免把不可见文字交给模型。"""
    if "hidden" in attrs or attrs.get("aria-hidden", "").lower() == "true":
        return True

    style = attrs.get("style", "").replace(" ", "").lower()
    return "display:none" in style or "visibility:hidden" in style


def normalize_max_chars(value) -> int:
    """把页面正文长度限制在 500～8000 字符之间。"""
    try:
        max_chars = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CHARS

    return min(max(max_chars, MIN_MAX_CHARS), MAX_MAX_CHARS)


def normalize_text(value: str) -> str:
    """合并 HTML 提取产生的多余空白，同时保留段落换行。"""
    text = html.unescape(value or "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_blocked_hostname(hostname: str) -> bool:
    """拒绝本机、局域网风格和没有公网域名结构的主机名。"""
    lowered = hostname.rstrip(".").lower()

    if lowered in {"localhost", "localhost.localdomain"}:
        return True

    if any(lowered.endswith(marker) for marker in INTERNAL_HOST_MARKERS):
        return True

    if "." not in lowered and ":" not in lowered:
        return True

    return False


def is_public_ip(address: str) -> bool:
    """确认地址不是私网、回环、链路本地或其他非公网 IP。"""
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def resolve_public_ips(hostname: str) -> tuple[list[str], str | None]:
    """解析域名的全部地址；任一地址非公网都拒绝本次访问。

    不能只检查其中一个地址，否则攻击者可以让同一域名同时解析到公网和内网，
    借重试或地址选择绕过 SSRF 边界。
    """
    try:
        addr_info = socket.getaddrinfo(
            hostname,
            None,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        return [], f"DNS resolution failed: {exc}"

    addresses = sorted({
        item[4][0]
        for item in addr_info
    })

    if not addresses:
        return [], "DNS resolution returned no addresses"

    for address in addresses:
        try:
            if not is_public_ip(address):
                return addresses, f"resolved address is not public: {address}"
        except ValueError:
            return addresses, f"resolved address is invalid: {address}"

    return addresses, None


def validate_url(raw_url: str) -> tuple[str | None, str | None]:
    """在发起请求前检查协议、凭据、主机名和最终解析到的 IP。

    这是 Browser Read 的 SSRF 边界：工具只能访问公开 HTTP(S) 页面，不能读取
    本机服务、云元数据地址或内网资源。
    """
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None, "url is required"

    parsed = urlparse(raw_url.strip())

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return None, "only http and https URLs are allowed"

    if not parsed.hostname:
        return None, "url hostname is required"

    if parsed.username or parsed.password:
        return None, "URLs with username or password are not allowed"

    hostname = parsed.hostname.rstrip(".")
    if is_blocked_hostname(hostname):
        return None, "internal hostnames are not allowed"

    try:
        if not is_public_ip(hostname):
            return None, f"target address is not public: {hostname}"
    except ValueError:
        _, error = resolve_public_ips(hostname)
        if error:
            return None, error

    return parsed.geturl(), None


def read_response_body(response) -> bytes:
    """分块读取响应，并在超过 1 MB 时立即停止，避免大页面耗尽内存。"""
    chunks = []
    total = 0

    while True:
        chunk = response.read(65536)
        if not chunk:
            break

        total += len(chunk)
        if total > MAX_BODY_BYTES:
            raise ValueError("response body is too large")

        chunks.append(chunk)

    return b"".join(chunks)


def request_once(url: str) -> tuple[int, dict, bytes]:
    """对已经验证的 URL 发起一次请求，并分别限制连接和读取时间。"""
    parsed = urlparse(url)
    port = parsed.port
    path = parsed.path or "/"
    if parsed.params:
        path = f"{path};{parsed.params}"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    connection_cls = (
        http.client.HTTPSConnection
        if parsed.scheme.lower() == "https"
        else http.client.HTTPConnection
    )
    connection = connection_cls(
        parsed.hostname,
        port=port,
        timeout=CONNECT_TIMEOUT_SECONDS,
    )
    connection.sock = None

    try:
        connection.request(
            "GET",
            path,
            headers={
                "Accept": "text/html,text/plain;q=0.9",
                "User-Agent": "MiniChatChat-browser-read/0.1",
            },
        )
        connection.sock.settimeout(READ_TIMEOUT_SECONDS)
        response = connection.getresponse()
        headers = {
            key.lower(): value
            for key, value in response.getheaders()
        }
        body = read_response_body(response)
        return response.status, headers, body
    finally:
        connection.close()


def fetch_url(url: str) -> tuple[str | None, dict | None, bytes | None, str | None]:
    """读取页面并手动跟随有限次跳转。

    每次跳转都会重新执行 validate_url()。这样公开网址不能通过 302 把工具带到
    内网地址，失败则返回稳定错误而不是抛出底层网络异常。
    """
    current_url = url

    for redirect_count in range(MAX_REDIRECTS + 1):
        checked_url, validation_error = validate_url(current_url)
        if validation_error:
            return None, None, None, validation_error

        try:
            status, headers, body = request_once(checked_url)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            return None, None, None, str(exc)

        if status in {301, 302, 303, 307, 308}:
            location = headers.get("location")
            if not location:
                return None, None, None, "redirect response missing Location"

            if redirect_count >= MAX_REDIRECTS:
                return None, None, None, "too many redirects"

            current_url = urljoin(checked_url, location)
            continue

        if status >= 400:
            return None, None, None, f"HTTP status {status}"

        return checked_url, headers, body, None

    return None, None, None, "too many redirects"


def parse_content_type(value: str) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def extract_text(body: bytes, content_type: str) -> tuple[str, str]:
    """把纯文本或 HTML 响应转换成标题和可读正文。"""
    decoded = body.decode("utf-8", errors="replace")

    if content_type == "text/plain":
        return "", normalize_text(decoded)

    parser = ReadableHTMLParser()
    parser.feed(decoded)
    return parser.title(), parser.text()


def redact_sensitive_markers(text: str) -> str:
    """遮盖页面中与项目密钥或认证错误相关的高风险标记。"""
    safe_text = text
    for marker in SENSITIVE_MARKERS:
        safe_text = re.sub(
            marker,
            "[REDACTED]",
            safe_text,
            flags=re.IGNORECASE,
        )
    return safe_text


def execute_browser_read(arguments: dict) -> ToolResult:
    """安全读取一个公开网页，并返回截断后的可见文本。

    流程依次经过 URL/解析地址校验、受限下载、内容类型检查和正文提取。每个阶段
    都在进入下一步前拒绝不安全输入，最终结果才会成为 Agent observation。
    """
    # 第一次校验尽早拒绝明显危险地址；fetch_url() 还会对每次跳转重复校验。
    url = arguments.get("url")
    max_chars = normalize_max_chars(arguments.get("max_chars", DEFAULT_MAX_CHARS))

    checked_url, validation_error = validate_url(url)
    if validation_error:
        return ToolResult(
            ok=False,
            error=validation_error,
            metadata={
                "readonly": True,
            },
        )

    final_url, headers, body, fetch_error = fetch_url(checked_url)
    if fetch_error:
        return ToolResult(
            ok=False,
            error=fetch_error,
            metadata={
                "readonly": True,
            },
        )

    # 只解析文本和 HTML，不让工具把二进制下载内容送入模型上下文。
    content_type = parse_content_type(headers.get("content-type", ""))
    if content_type not in ALLOWED_CONTENT_TYPES:
        return ToolResult(
            ok=False,
            error=f"unsupported content type: {content_type or '(missing)'}",
            metadata={
                "readonly": True,
            },
        )

    title, text = extract_text(body, content_type)
    text = redact_sensitive_markers(text)
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars].rstrip()

    return ToolResult(
        ok=True,
        result={
            "title": title,
            "url": final_url,
            "text": text,
            "char_count": len(text),
            "truncated": truncated,
            "content_type": content_type,
        },
        metadata={
            "readonly": True,
            "max_chars": max_chars,
            "max_body_bytes": MAX_BODY_BYTES,
        },
    )


def get_browser_read_tool() -> ToolSpec:
    """声明 Browser Read 的只读能力和参数上限，供 Agent 工具注册表使用。"""
    return ToolSpec(
        name="browser_read",
        description=(
            "Read the visible text from one public http or https URL that the "
            "user already provided. Use this when the user gives a direct URL "
            "and asks to read, summarize, inspect, or answer from that page. "
            "This tool validates redirects and DNS targets, rejects private or "
            "internal addresses, accepts only text/html or text/plain, does "
            "not execute JavaScript, does not click links, does not download "
            "files, and never writes local files."
        ),
        args_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Public http or https URL supplied by the user.",
                },
                "max_chars": {
                    "type": "integer",
                    "default": DEFAULT_MAX_CHARS,
                    "minimum": MIN_MAX_CHARS,
                    "maximum": MAX_MAX_CHARS,
                    "description": "Maximum page text characters to return.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        executor=execute_browser_read,
    )
