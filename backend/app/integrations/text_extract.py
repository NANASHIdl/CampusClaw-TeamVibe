"""正文提取：把落盘文件读成纯文本。

第 3 课范围只接受 `.txt` 与 `.md`，因此这里不做 PDF / Word 解析——那需要新增
pypdf / python-docx 依赖，属于第 5 课之后的扩展。放开新类型时在这里加一个分支，
并在 `Settings.UPLOAD_ALLOWED_EXT` 里登记，两处必须同时改。

编码处理：先按 UTF-8 读，失败再按 GB18030（Windows 上另存的讲义常见）。
两次都失败按「无可提取文本」处理，由 services/ 落成 `failed`，不是 500。
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = {"md", "txt"}
# 单篇正文上限：超过 200 万字符的讲义基本是误传，直接判失败比慢慢切片更省事
MAX_TEXT_CHARS = 2_000_000


class EmptyTextError(Exception):
    """文件里没有可提取文本。"""


class UnsupportedFormatError(Exception):
    """扩展名不在提取器支持范围内。"""


def read_text_file(path: Path, ext: str) -> str:
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(ext)

    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError as exc:  # 换下一种编码再试
            last_error = exc
    else:
        raise UnsupportedFormatError(ext) from last_error

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise EmptyTextError("文件无可提取文本")
    return normalized[:MAX_TEXT_CHARS]
