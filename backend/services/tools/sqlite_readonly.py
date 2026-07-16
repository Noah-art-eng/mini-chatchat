import re
import sqlite3

from db import DB_PATH

from .types import ToolResult, ToolSpec


MAX_ROWS = 50
FORBIDDEN_SQL = re.compile(
    r"\b("
    r"alter|attach|create|delete|detach|drop|insert|pragma|reindex|replace|"
    r"truncate|update|vacuum"
    r")\b",
    flags=re.IGNORECASE,
)


def normalize_limit(value) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return MAX_ROWS

    return min(max(limit, 1), MAX_ROWS)


def validate_select_sql(sql: str) -> str | None:
    stripped = sql.strip()

    if not stripped:
        return "sql is required"

    if ";" in stripped.rstrip(";"):
        return "only one SQL statement is allowed"

    stripped = stripped.rstrip(";").strip()

    if not re.match(r"^select\b", stripped, flags=re.IGNORECASE):
        return "only SELECT statements are allowed"

    if FORBIDDEN_SQL.search(stripped):
        return "write or schema-changing SQL is not allowed"

    return None


def execute_sqlite_readonly_query(arguments: dict) -> ToolResult:
    sql = arguments.get("sql")
    limit = normalize_limit(arguments.get("limit", MAX_ROWS))

    if not isinstance(sql, str):
        return ToolResult(
            ok=False,
            error="sql must be a string",
        )

    validation_error = validate_select_sql(sql)
    if validation_error:
        return ToolResult(
            ok=False,
            error=validation_error,
        )

    try:
        conn = sqlite3.connect(
            f"file:{DB_PATH}?mode=ro",
            uri=True,
        )
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql.rstrip(";"))
        fetched_rows = cursor.fetchmany(limit + 1)
        columns = [
            column[0]
            for column in cursor.description or []
        ]
        rows = [
            {
                column: row[column]
                for column in columns
            }
            for row in fetched_rows[:limit]
        ]
        conn.close()

        return ToolResult(
            ok=True,
            result={
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": len(fetched_rows) > limit,
            },
            metadata={
                "limit": limit,
                "readonly": True,
            },
        )
    except sqlite3.Error as exc:
        return ToolResult(
            ok=False,
            error=str(exc),
            metadata={
                "readonly": True,
            },
        )


def get_sqlite_readonly_query_tool() -> ToolSpec:
    return ToolSpec(
        name="sqlite_readonly_query",
        description=(
            "Run a read-only SELECT query against the Mini ChatChat SQLite "
            "database. Use for inspecting counts or rows from tables such as "
            "conversation, message, knowledge_base, knowledge_file, and "
            "file_doc. Never use this for writes or schema changes."
        ),
        args_schema={
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "Single SELECT statement. Example: SELECT COUNT(*) AS count FROM conversation",
                },
                "limit": {
                    "type": "integer",
                    "default": MAX_ROWS,
                    "minimum": 1,
                    "maximum": MAX_ROWS,
                },
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
        executor=execute_sqlite_readonly_query,
    )
