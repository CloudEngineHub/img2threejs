"""Profile, record, tokenizer, and source-ingestion boundary. # noqa: SIZE_OK"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import tempfile
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, NoReturn, TypeAlias, TypedDict

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
SourceKind: TypeAlias = Literal["markdown", "json", "jsonl"]
CacheStatus: TypeAlias = Literal["hit", "rebuilt"]
CacheReason: TypeAlias = Literal["current", "missing", "stale", "corrupt", "forced"]
_SOURCE_KINDS: Final[dict[str, SourceKind]] = {
    ".md": "markdown",
    ".json": "json",
    ".jsonl": "jsonl",
}


class TokenizerSettings(TypedDict):
    version: str
    unicode_normalization: str
    casefold: bool
    accent_fold: str
    preserve_identifiers: bool
    preserve_numbers: bool
    stemming: bool


class AliasSettings(TypedDict):
    mode: str
    enabled: bool
    max_expansions: int


class Bm25Settings(TypedDict):
    k1: float
    b: float


class CollectionProfile(TypedDict):
    source_roots: list[str]
    distilled_records: list[str]
    cache: str
    documentation: str
    encoding: str
    languages: list[str]
    source_extensions: list[str]
    tokenizer: TokenizerSettings
    aliases: AliasSettings
    bm25: Bm25Settings
    term_aliases: dict[str, list[str]]


class MeasurementRequired(TypedDict):
    name: str
    value: str


class Measurement(MeasurementRequired, total=False):
    unit: str
    context: str


class SourceRefRequired(TypedDict):
    path: str


class SourceRef(SourceRefRequired, total=False):
    heading: str
    key_path: str


class EvidenceRefRequired(TypedDict):
    kind: str
    ref: str


class EvidenceRef(EvidenceRefRequired, total=False):
    note: str


class SpecRecord(TypedDict):
    record_id: str
    collection: str
    domain: str
    kind: str
    entity: str
    title: str
    aliases: list[str]
    content: str
    constraints: list[str]
    measurements: list[Measurement]
    source_refs: list[SourceRef]
    evidence_refs: list[EvidenceRef]
    observation_status: str
    confidence: float
    assumptions: list[str]


class CachedSourceReference(TypedDict):
    path: str
    heading: str | None
    key_path: str | None


class CachedRecord(TypedDict):
    record_id: str
    collection: str
    title: str
    content: str
    file_path: str
    heading: str | None
    key_path: str | None
    aliases: list[str]
    source_refs: list[CachedSourceReference]


class CachedPosting(TypedDict):
    record_id: str
    term_frequency: int


class CachePayload(TypedDict):
    schema_version: int
    schema_fingerprint: str
    tokenizer_fingerprint: str
    config_fingerprint: str
    source_fingerprint: str
    fingerprint: str
    collection: str
    k1: float
    b: float
    document_lengths: dict[str, int]
    avgdl: float
    document_frequencies: dict[str, int]
    postings: dict[str, list[CachedPosting]]
    records: dict[str, CachedRecord]
    term_aliases: dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class SourceReference:
    path: str
    heading: str | None = None
    key_path: str | None = None


@dataclass(frozen=True, slots=True)
class SourceDocument:
    record_id: str
    collection: str
    title: str
    content: str
    file_path: str
    heading: str | None = None
    key_path: str | None = None
    aliases: tuple[str, ...] = ()
    source_refs: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class Bm25Config:
    collection: str
    k1: float = 1.5
    b: float = 0.75
    term_aliases: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True, slots=True)
class IndexFingerprints:
    schema: str = ""
    tokenizer: str = ""
    config: str = ""
    source: str = ""

    @property
    def combined(self) -> str:
        return _fingerprint(
            {
                "schema": self.schema,
                "tokenizer": self.tokenizer,
                "config": self.config,
                "source": self.source,
            }
        )


@dataclass(frozen=True, slots=True)
class Posting:
    record_id: str
    term_frequency: int


@dataclass(frozen=True, slots=True)
class Bm25Index:
    collection: str
    k1: float
    b: float
    fingerprints: IndexFingerprints
    document_lengths: Mapping[str, int]
    avgdl: float
    document_frequencies: Mapping[str, int]
    postings: Mapping[str, tuple[Posting, ...]]
    records: Mapping[str, SourceDocument]
    term_aliases: Mapping[str, tuple[str, ...]]

    @property
    def fingerprint(self) -> str:
        return self.fingerprints.combined


@dataclass(frozen=True, slots=True)
class SearchMatch:
    record: SourceDocument
    score: float


@dataclass(frozen=True, slots=True)
class IndexRequest:
    project_root: Path
    collection: str
    profile: CollectionProfile
    force_reindex: bool = False


@dataclass(frozen=True, slots=True)
class IndexLoadResult:
    index: Bm25Index
    status: CacheStatus
    reason: CacheReason
    cache_path: Path

    @property
    def fingerprint(self) -> str:
        return self.index.fingerprint


@dataclass(frozen=True, slots=True)
class ConfiguredSource:
    path: Path
    source_path: str
    kind: SourceKind


@dataclass(frozen=True, slots=True)
class ProfileValidationError(ValueError):
    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class UnknownCollectionError(KeyError):
    collection: str

    def __str__(self) -> str:
        return f"unknown spec-search collection: {self.collection}"


@dataclass(frozen=True, slots=True)
class SourceIngestionError(Exception):
    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class SpecRecordValidationError(ValueError):
    path: Path
    line_number: int
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line_number}: {self.reason}"


@dataclass(frozen=True, slots=True)
class IndexBuildError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class CacheValidationError(ValueError):
    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class CacheReadError(Exception):
    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class CacheWriteError(Exception):
    path: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


_DEFAULT_PROFILES_PATH: Final = Path(__file__).with_name("spec_search_profiles.json")
_CACHE_SCHEMA_VERSION: Final = 1
_TOKENIZER_SCHEMA_VERSION: Final = "1"
_TOKEN_PATTERN: Final = re.compile(r"[^\W_]+(?:[_.\-\u2010-\u2015][^\W_]+)*", re.UNICODE)
_DASH_TRANSLATION: Final = str.maketrans({character: "-" for character in "‐‑‒–—―"})
_VIETNAMESE_MARKED: Final = frozenset(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữựỳýỷỹỵđ"
)


def _profile_error(path: Path, reason: str) -> ProfileValidationError:
    return ProfileValidationError(path=path, reason=reason)


def _mapping(value: JsonValue, path: Path, label: str) -> dict[str, JsonValue]:
    if type(value) is not dict:
        raise _profile_error(path, f"{label} must be an object")
    return value


def _profile_string(mapping: dict[str, JsonValue], field: str, path: Path) -> str:
    value = mapping.get(field)
    if type(value) is not str or not value:
        raise _profile_error(path, f"{field} must be a non-empty string")
    return value


def _profile_string_list(mapping: dict[str, JsonValue], field: str, path: Path) -> list[str]:
    value = mapping.get(field)
    if type(value) is not list:
        raise _profile_error(path, f"{field} must be an array of non-empty strings")
    parsed: list[str] = []
    for item in value:
        if type(item) is not str or not item:
            raise _profile_error(path, f"{field} must be an array of non-empty strings")
        parsed.append(item)
    return parsed


def _profile_bool(mapping: dict[str, JsonValue], field: str, path: Path) -> bool:
    value = mapping.get(field)
    if type(value) is not bool:
        raise _profile_error(path, f"{field} must be a boolean")
    return value


def _profile_number(mapping: dict[str, JsonValue], field: str, path: Path) -> float:
    value = mapping.get(field)
    if type(value) is bool or not isinstance(value, (int, float)):
        raise _profile_error(path, f"{field} must be a number")
    return float(value)


def load_profiles(path: Path | None = None) -> dict[str, CollectionProfile]:
    profile_path = _DEFAULT_PROFILES_PATH if path is None else path
    try:
        raw: JsonValue = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise _profile_error(profile_path, "invalid JSON profile") from error
    except (OSError, UnicodeError) as error:
        raise _profile_error(profile_path, "unable to read UTF-8 profile") from error
    root = _mapping(raw, profile_path, "profile")
    version = root.get("profile_schema_version")
    if type(version) is not int or version < 1:
        raise _profile_error(profile_path, "profile_schema_version must be a positive integer")
    defaults = _mapping(root.get("defaults"), profile_path, "defaults")
    tokenizer_raw = _mapping(defaults.get("tokenizer"), profile_path, "defaults.tokenizer")
    alias_raw = _mapping(defaults.get("aliases"), profile_path, "defaults.aliases")
    bm25_raw = _mapping(defaults.get("bm25"), profile_path, "defaults.bm25")
    max_expansions = alias_raw.get("max_expansions")
    if type(max_expansions) is not int or max_expansions < 0:
        raise _profile_error(profile_path, "defaults.aliases.max_expansions must be a non-negative integer")
    tokenizer: TokenizerSettings = {
        "version": _profile_string(tokenizer_raw, "version", profile_path),
        "unicode_normalization": _profile_string(tokenizer_raw, "unicode_normalization", profile_path),
        "casefold": _profile_bool(tokenizer_raw, "casefold", profile_path),
        "accent_fold": _profile_string(tokenizer_raw, "accent_fold", profile_path),
        "preserve_identifiers": _profile_bool(tokenizer_raw, "preserve_identifiers", profile_path),
        "preserve_numbers": _profile_bool(tokenizer_raw, "preserve_numbers", profile_path),
        "stemming": _profile_bool(tokenizer_raw, "stemming", profile_path),
    }
    alias_settings: AliasSettings = {
        "mode": _profile_string(alias_raw, "mode", profile_path),
        "enabled": _profile_bool(alias_raw, "enabled", profile_path),
        "max_expansions": max_expansions,
    }
    bm25: Bm25Settings = {
        "k1": _profile_number(bm25_raw, "k1", profile_path),
        "b": _profile_number(bm25_raw, "b", profile_path),
    }
    collections = _mapping(root.get("collections"), profile_path, "collections")
    parsed: dict[str, CollectionProfile] = {}
    for name in sorted(collections):
        collection = _mapping(collections[name], profile_path, f"collections.{name}")
        term_aliases_raw = collection.get("term_aliases", {})
        term_aliases_mapping = _mapping(term_aliases_raw, profile_path, f"collections.{name}.term_aliases")
        term_aliases = {
            term: _profile_string_list(term_aliases_mapping, term, profile_path)
            for term in sorted(term_aliases_mapping)
        }
        parsed[name] = {
            "source_roots": _profile_string_list(collection, "source_roots", profile_path),
            "distilled_records": _profile_string_list(collection, "distilled_records", profile_path),
            "documentation": _profile_string(collection, "documentation", profile_path),
            "cache": _profile_string(collection, "cache", profile_path),
            "encoding": _profile_string(defaults, "encoding", profile_path),
            "languages": _profile_string_list(defaults, "languages", profile_path),
            "source_extensions": _profile_string_list(defaults, "source_extensions", profile_path),
            "tokenizer": tokenizer,
            "aliases": alias_settings,
            "bm25": bm25,
            "term_aliases": term_aliases,
        }
    return parsed


def load_profile(collection: str, path: Path | None = None) -> CollectionProfile:
    profiles = load_profiles(path)
    if collection not in profiles:
        raise UnknownCollectionError(collection=collection)
    return profiles[collection]


def _record_error(path: Path, line_number: int, reason: str) -> SpecRecordValidationError:
    return SpecRecordValidationError(path=path, line_number=line_number, reason=reason)


def _record_mapping(value: JsonValue, path: Path, line_number: int) -> dict[str, JsonValue]:
    if type(value) is not dict:
        raise _record_error(path, line_number, "record must be a JSON object")
    return value


def _record_string(
    record: dict[str, JsonValue],
    field: str,
    location: tuple[Path, int],
    *,
    allow_empty: bool = False,
) -> str:
    value = record.get(field)
    if type(value) is not str or (not allow_empty and not value):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise _record_error(location[0], location[1], f"{field} must be {qualifier}")
    return value


def _record_string_list(
    record: dict[str, JsonValue],
    field: str,
    location: tuple[Path, int],
) -> list[str]:
    value = record.get(field)
    if type(value) is not list:
        raise _record_error(location[0], location[1], f"{field} must be an array of strings")
    parsed: list[str] = []
    for item in value:
        if type(item) is not str:
            raise _record_error(location[0], location[1], f"{field} must be an array of strings")
        parsed.append(item)
    return parsed


def _measurements(record: dict[str, JsonValue], location: tuple[Path, int]) -> list[Measurement]:
    raw = record.get("measurements")
    if type(raw) is not list:
        raise _record_error(location[0], location[1], "measurements must be an array")
    parsed: list[Measurement] = []
    for value in raw:
        item = _record_mapping(value, *location)
        measurement: Measurement = {
            "name": _record_string(item, "name", location),
            "value": _record_string(item, "value", location),
        }
        for field in ("unit", "context"):
            if field in item:
                measurement[field] = _record_string(item, field, location, allow_empty=True)
        parsed.append(measurement)
    return parsed


def _source_refs(record: dict[str, JsonValue], location: tuple[Path, int]) -> list[SourceRef]:
    raw = record.get("source_refs")
    if type(raw) is not list or not raw:
        raise _record_error(location[0], location[1], "source_refs must be a non-empty array")
    parsed: list[SourceRef] = []
    for value in raw:
        item = _record_mapping(value, *location)
        source_ref: SourceRef = {"path": _record_string(item, "path", location)}
        for field in ("heading", "key_path"):
            if field in item:
                source_ref[field] = _record_string(item, field, location)
        parsed.append(source_ref)
    return parsed


def _evidence_refs(record: dict[str, JsonValue], location: tuple[Path, int]) -> list[EvidenceRef]:
    raw = record.get("evidence_refs")
    if type(raw) is not list:
        raise _record_error(location[0], location[1], "evidence_refs must be an array")
    parsed: list[EvidenceRef] = []
    for value in raw:
        item = _record_mapping(value, *location)
        evidence_ref: EvidenceRef = {
            "kind": _record_string(item, "kind", location),
            "ref": _record_string(item, "ref", location),
        }
        if "note" in item:
            evidence_ref["note"] = _record_string(item, "note", location, allow_empty=True)
        parsed.append(evidence_ref)
    return parsed


def _parse_record(value: JsonValue, path: Path, line_number: int) -> SpecRecord:
    raw = _record_mapping(value, path, line_number)
    location = (path, line_number)
    status = _record_string(raw, "observation_status", location)
    if status not in {"observed", "inferred", "unverified"}:
        raise _record_error(path, line_number, "observation_status is invalid")
    confidence = raw.get("confidence")
    if type(confidence) is bool or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise _record_error(path, line_number, "confidence must be a number from 0 through 1")
    return {
        "record_id": _record_string(raw, "record_id", location),
        "collection": _record_string(raw, "collection", location),
        "domain": _record_string(raw, "domain", location),
        "kind": _record_string(raw, "kind", location),
        "entity": _record_string(raw, "entity", location),
        "title": _record_string(raw, "title", location),
        "aliases": _record_string_list(raw, "aliases", location),
        "content": _record_string(raw, "content", location, allow_empty=True),
        "constraints": _record_string_list(raw, "constraints", location),
        "measurements": _measurements(raw, location),
        "source_refs": _source_refs(raw, location),
        "evidence_refs": _evidence_refs(raw, location),
        "observation_status": status,
        "confidence": float(confidence),
        "assumptions": _record_string_list(raw, "assumptions", location),
    }


def load_jsonl_records(path: Path) -> list[SpecRecord]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise _record_error(path, 0, "unable to read UTF-8 JSONL") from error
    records: list[SpecRecord] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value: JsonValue = json.loads(line)
        except json.JSONDecodeError as error:
            raise _record_error(path, line_number, "invalid JSON object") from error
        records.append(_parse_record(value, path, line_number))
    return records


def _primary_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return [match.group(0).translate(_DASH_TRANSLATION) for match in _TOKEN_PATTERN.finditer(normalized)]


def _accent_companion(token: str) -> str | None:
    if not any(character in _VIETNAMESE_MARKED for character in token):
        return None
    decomposed = unicodedata.normalize("NFD", token)
    folded = "".join(character for character in decomposed if unicodedata.category(character) != "Mn")
    folded = folded.replace("đ", "d")
    return folded if folded != token else None


def _with_accent_companions(tokens: Sequence[str]) -> list[str]:
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        companion = _accent_companion(token)
        if companion is not None:
            expanded.append(companion)
    return expanded


def tokenize(text: str, aliases: Mapping[str, Sequence[str]] | None = None) -> list[str]:
    primary = _primary_tokens(text)
    tokens = _with_accent_companions(primary)
    if aliases is None:
        return tokens
    normalized_aliases = sorted(
        ((_primary_tokens(term), tuple(values)) for term, values in aliases.items()),
        key=lambda item: item[0],
    )
    for alias_tokens, expansions in normalized_aliases:
        width = len(alias_tokens)
        if width == 0 or not any(primary[index : index + width] == alias_tokens for index in range(len(primary) - width + 1)):
            continue
        for expansion in sorted(expansions, key=lambda value: unicodedata.normalize("NFKC", value).casefold()):
            tokens.extend(_with_accent_companions(_primary_tokens(expansion)))
    return tokens


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SourceIngestionError(path=path, reason="unable to read UTF-8 source") from error


def _source_reference(file_path: str, heading: str | None, key_path: str | None) -> tuple[SourceReference, ...]:
    return (SourceReference(path=file_path, heading=heading, key_path=key_path),)


def ingest_markdown(path: Path, source_path: str, collection: str) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    heading: str | None = None
    body: list[str] = []
    section_number = 0

    def append_section() -> None:
        nonlocal section_number
        content = "\n".join(body).strip()
        if heading is None and not content:
            return
        section_number += 1
        title = heading if heading is not None else path.stem
        documents.append(
            SourceDocument(
                record_id=f"{collection}.markdown.{source_path}#{section_number}",
                collection=collection,
                title=title,
                content=content,
                file_path=source_path,
                heading=heading,
                source_refs=_source_reference(source_path, heading, None),
            )
        )

    for line in _read_source(path).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            body.append(line)
            continue
        append_section()
        heading = match.group(1)
        body = []
    append_section()
    return documents


def _json_content(value: JsonScalar) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def assert_never(value: NoReturn) -> NoReturn:
    raise AssertionError(f"unhandled JSON value: {value!r}")


def ingest_json(path: Path, source_path: str, collection: str) -> list[SourceDocument]:
    try:
        root: JsonValue = json.loads(_read_source(path))
    except json.JSONDecodeError as error:
        raise SourceIngestionError(path=path, reason="invalid JSON source") from error
    documents: list[SourceDocument] = []

    def visit(value: JsonValue, key_path: str) -> None:
        match value:
            case dict() as mapping:
                for key in sorted(mapping):
                    child_path = key if not key_path else f"{key_path}.{key}"
                    visit(mapping[key], child_path)
            case list() as values:
                for index, item in enumerate(values):
                    visit(item, f"{key_path}[{index}]" if key_path else f"[{index}]")
            case str() | int() | float() | bool() | None as scalar:
                location = key_path or "$"
                documents.append(
                    SourceDocument(
                        record_id=f"{collection}.json.{source_path}#{location}",
                        collection=collection,
                        title=location.rsplit(".", maxsplit=1)[-1],
                        content=_json_content(scalar),
                        file_path=source_path,
                        key_path=location,
                        source_refs=_source_reference(source_path, None, location),
                    )
                )
            case unreachable:
                assert_never(unreachable)

    visit(root, "")
    return documents


def _ingest_jsonl(path: Path, source_path: str) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for record in load_jsonl_records(path):
        references = tuple(
            SourceReference(
                path=source_ref["path"],
                heading=source_ref.get("heading"),
                key_path=source_ref.get("key_path"),
            )
            for source_ref in record["source_refs"]
        )
        documents.append(
            SourceDocument(
                record_id=record["record_id"],
                collection=record["collection"],
                title=record["title"],
                content=record["content"],
                file_path=source_path,
                aliases=tuple(record["aliases"]),
                source_refs=references,
            )
        )
    return documents


def _source_kind(path: Path) -> SourceKind:
    kind = _SOURCE_KINDS.get(path.suffix.casefold())
    if kind is None:
        raise SourceIngestionError(path=path, reason="unsupported configured source extension")
    return kind


def ingest_source_tree(
    root: Path,
    collection: str,
    extensions: Sequence[str],
) -> list[SourceDocument]:
    if not root.is_dir():
        raise SourceIngestionError(path=root, reason="configured source root is not a directory")
    allowed = frozenset(extension.casefold() for extension in extensions)
    documents: list[SourceDocument] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if not path.is_file() or path.suffix.casefold() not in allowed:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        source_path = relative.as_posix()
        match _source_kind(path):
            case "markdown":
                documents.extend(ingest_markdown(path, source_path, collection))
            case "json":
                documents.extend(ingest_json(path, source_path, collection))
            case "jsonl":
                documents.extend(_ingest_jsonl(path, source_path))
            case unreachable:
                assert_never(unreachable)
    return documents


def _fingerprint(value: JsonValue | CollectionProfile) -> str:
    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _alias_mapping(config: Bm25Config) -> dict[str, tuple[str, ...]]:
    return {term: expansions for term, expansions in config.term_aliases}


def _searchable_text(document: SourceDocument) -> str:
    parts = [document.title]
    if document.heading is not None and document.heading != document.title:
        parts.append(document.heading)
    parts.extend(document.aliases)
    parts.append(document.content)
    return "\n".join(parts)


def build_index(
    documents: Sequence[SourceDocument],
    config: Bm25Config,
    fingerprints: IndexFingerprints = IndexFingerprints(),
) -> Bm25Index:
    if config.k1 <= 0:
        raise IndexBuildError(reason="BM25 k1 must be greater than zero")
    if not 0 <= config.b <= 1:
        raise IndexBuildError(reason="BM25 b must be from zero through one")

    aliases = _alias_mapping(config)
    records: dict[str, SourceDocument] = {}
    document_lengths: dict[str, int] = {}
    posting_lists: dict[str, list[Posting]] = {}
    for document in sorted(documents, key=lambda item: item.record_id):
        if document.record_id in records:
            raise IndexBuildError(reason=f"duplicate record_id: {document.record_id}")
        records[document.record_id] = document
        term_frequencies = Counter(tokenize(_searchable_text(document), aliases))
        document_lengths[document.record_id] = sum(term_frequencies.values())
        for term in sorted(term_frequencies):
            posting_lists.setdefault(term, []).append(
                Posting(record_id=document.record_id, term_frequency=term_frequencies[term])
            )

    document_count = len(records)
    avgdl = sum(document_lengths.values()) / document_count if document_count else 0.0
    postings = {term: tuple(values) for term, values in sorted(posting_lists.items())}
    document_frequencies = {term: len(values) for term, values in postings.items()}
    return Bm25Index(
        collection=config.collection,
        k1=config.k1,
        b=config.b,
        fingerprints=fingerprints,
        document_lengths=document_lengths,
        avgdl=avgdl,
        document_frequencies=document_frequencies,
        postings=postings,
        records=records,
        term_aliases=aliases,
    )


def search_index(index: Bm25Index, query: str) -> list[SearchMatch]:
    if not index.records or index.avgdl == 0:
        return []
    query_terms = sorted(set(tokenize(query, index.term_aliases)))
    scores: dict[str, float] = {}
    document_count = len(index.records)
    for term in query_terms:
        term_postings = index.postings.get(term, ())
        if not term_postings:
            continue
        document_frequency = index.document_frequencies[term]
        inverse_document_frequency = math.log(
            1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        for posting in term_postings:
            document_length = index.document_lengths[posting.record_id]
            length_normalization = 1 - index.b + index.b * document_length / index.avgdl
            numerator = posting.term_frequency * (index.k1 + 1)
            denominator = posting.term_frequency + index.k1 * length_normalization
            scores[posting.record_id] = scores.get(posting.record_id, 0.0) + (
                inverse_document_frequency * numerator / denominator
            )
    matches = [
        SearchMatch(record=index.records[record_id], score=score)
        for record_id, score in scores.items()
        if score > 0
    ]
    return sorted(matches, key=lambda match: (-match.score, match.record.record_id))


def _hidden_source(relative: Path) -> bool:
    return any(part.startswith(".") or part == "__pycache__" for part in relative.parts)


def _configured_sources(request: IndexRequest) -> list[ConfiguredSource]:
    allowed = frozenset(extension.casefold() for extension in request.profile["source_extensions"])
    sources: dict[str, ConfiguredSource] = {}
    for configured_root in request.profile["source_roots"]:
        root = request.project_root / configured_root
        if not root.is_dir():
            raise SourceIngestionError(path=root, reason="configured source root is not a directory")
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in allowed:
                continue
            source_path = path.relative_to(request.project_root)
            if _hidden_source(source_path):
                continue
            source_key = source_path.as_posix()
            sources[source_key] = ConfiguredSource(
                path=path,
                source_path=source_key,
                kind=_source_kind(path),
            )
    for configured_record in request.profile["distilled_records"]:
        path = request.project_root / configured_record
        if not path.is_file():
            raise SourceIngestionError(path=path, reason="configured distilled record source is not a file")
        source_path = path.relative_to(request.project_root)
        if _hidden_source(source_path):
            continue
        source_key = source_path.as_posix()
        sources[source_key] = ConfiguredSource(
            path=path,
            source_path=source_key,
            kind=_source_kind(path),
        )
    return [sources[source_key] for source_key in sorted(sources)]


def _source_fingerprint(sources: Sequence[ConfiguredSource]) -> str:
    digest = hashlib.sha256()
    for source in sources:
        digest.update(source.source_path.encode("utf-8"))
        digest.update(b"\0")
        try:
            with source.path.open("rb") as source_file:
                for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise SourceIngestionError(
                path=source.path,
                reason="unable to read source for freshness check",
            ) from error
        digest.update(b"\0")
    return digest.hexdigest()


def _index_fingerprints(request: IndexRequest, sources: Sequence[ConfiguredSource]) -> IndexFingerprints:
    schema_fingerprint = _fingerprint(
        {
            "cache_schema_version": _CACHE_SCHEMA_VERSION,
            "record_metadata_version": 1,
        }
    )
    tokenizer = request.profile["tokenizer"]
    tokenizer_value: JsonValue = {
        "implementation_version": _TOKENIZER_SCHEMA_VERSION,
        "settings": {
            "version": tokenizer["version"],
            "unicode_normalization": tokenizer["unicode_normalization"],
            "casefold": tokenizer["casefold"],
            "accent_fold": tokenizer["accent_fold"],
            "preserve_identifiers": tokenizer["preserve_identifiers"],
            "preserve_numbers": tokenizer["preserve_numbers"],
            "stemming": tokenizer["stemming"],
        },
    }
    tokenizer_fingerprint = _fingerprint(tokenizer_value)
    config_fingerprint = _fingerprint(request.profile)
    return IndexFingerprints(
        schema=schema_fingerprint,
        tokenizer=tokenizer_fingerprint,
        config=config_fingerprint,
        source=_source_fingerprint(sources),
    )


def _ingest_configured_sources(
    request: IndexRequest,
    sources: Sequence[ConfiguredSource],
) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for source in sources:
        match source.kind:
            case "markdown":
                documents.extend(ingest_markdown(source.path, source.source_path, request.collection))
            case "json":
                documents.extend(ingest_json(source.path, source.source_path, request.collection))
            case "jsonl":
                documents.extend(_ingest_jsonl(source.path, source.source_path))
            case unreachable:
                assert_never(unreachable)
    return documents


def _cached_source_reference(reference: SourceReference) -> CachedSourceReference:
    return {
        "path": reference.path,
        "heading": reference.heading,
        "key_path": reference.key_path,
    }


def _cached_record(document: SourceDocument) -> CachedRecord:
    return {
        "record_id": document.record_id,
        "collection": document.collection,
        "title": document.title,
        "content": document.content,
        "file_path": document.file_path,
        "heading": document.heading,
        "key_path": document.key_path,
        "aliases": list(document.aliases),
        "source_refs": [_cached_source_reference(reference) for reference in document.source_refs],
    }


def _cache_payload(index: Bm25Index) -> CachePayload:
    return {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "schema_fingerprint": index.fingerprints.schema,
        "tokenizer_fingerprint": index.fingerprints.tokenizer,
        "config_fingerprint": index.fingerprints.config,
        "source_fingerprint": index.fingerprints.source,
        "fingerprint": index.fingerprint,
        "collection": index.collection,
        "k1": index.k1,
        "b": index.b,
        "document_lengths": dict(index.document_lengths),
        "avgdl": index.avgdl,
        "document_frequencies": dict(index.document_frequencies),
        "postings": {
            term: [
                {"record_id": posting.record_id, "term_frequency": posting.term_frequency}
                for posting in postings
            ]
            for term, postings in index.postings.items()
        },
        "records": {
            record_id: _cached_record(document)
            for record_id, document in index.records.items()
        },
        "term_aliases": {
            term: list(expansions)
            for term, expansions in index.term_aliases.items()
        },
    }


def _cache_validation_error(path: Path, reason: str) -> CacheValidationError:
    return CacheValidationError(path=path, reason=reason)


def _cache_mapping(value: JsonValue, path: Path, label: str) -> dict[str, JsonValue]:
    if type(value) is not dict:
        raise _cache_validation_error(path, f"{label} must be an object")
    return value


def _cache_string(mapping: dict[str, JsonValue], field: str, path: Path) -> str:
    value = mapping.get(field)
    if type(value) is not str:
        raise _cache_validation_error(path, f"{field} must be a string")
    return value


def _cache_optional_string(mapping: dict[str, JsonValue], field: str, path: Path) -> str | None:
    value = mapping.get(field)
    if value is not None and type(value) is not str:
        raise _cache_validation_error(path, f"{field} must be a string or null")
    return value


def _cache_float(mapping: dict[str, JsonValue], field: str, path: Path) -> float:
    value = mapping.get(field)
    if type(value) is bool or not isinstance(value, (int, float)):
        raise _cache_validation_error(path, f"{field} must be a number")
    return float(value)


def _cache_integer(mapping: dict[str, JsonValue], field: str, path: Path) -> int:
    value = mapping.get(field)
    if type(value) is not int:
        raise _cache_validation_error(path, f"{field} must be an integer")
    return value


def _cache_string_list(value: JsonValue, path: Path, label: str) -> list[str]:
    if type(value) is not list or not all(type(item) is str for item in value):
        raise _cache_validation_error(path, f"{label} must be an array of strings")
    parsed: list[str] = []
    for item in value:
        if type(item) is str:
            parsed.append(item)
    return parsed


def _parse_cached_reference(value: JsonValue, path: Path) -> SourceReference:
    raw = _cache_mapping(value, path, "source reference")
    return SourceReference(
        path=_cache_string(raw, "path", path),
        heading=_cache_optional_string(raw, "heading", path),
        key_path=_cache_optional_string(raw, "key_path", path),
    )


def _parse_cached_record(record_id: str, value: JsonValue, path: Path) -> SourceDocument:
    raw = _cache_mapping(value, path, f"records.{record_id}")
    cached_record_id = _cache_string(raw, "record_id", path)
    if cached_record_id != record_id:
        raise _cache_validation_error(path, f"records.{record_id}.record_id does not match its key")
    references_raw = raw.get("source_refs")
    if type(references_raw) is not list:
        raise _cache_validation_error(path, f"records.{record_id}.source_refs must be an array")
    return SourceDocument(
        record_id=record_id,
        collection=_cache_string(raw, "collection", path),
        title=_cache_string(raw, "title", path),
        content=_cache_string(raw, "content", path),
        file_path=_cache_string(raw, "file_path", path),
        heading=_cache_optional_string(raw, "heading", path),
        key_path=_cache_optional_string(raw, "key_path", path),
        aliases=tuple(_cache_string_list(raw.get("aliases"), path, f"records.{record_id}.aliases")),
        source_refs=tuple(_parse_cached_reference(reference, path) for reference in references_raw),
    )


def _parse_integer_mapping(value: JsonValue, path: Path, label: str) -> dict[str, int]:
    raw = _cache_mapping(value, path, label)
    parsed: dict[str, int] = {}
    for key, item in raw.items():
        if type(item) is not int or item < 0:
            raise _cache_validation_error(path, f"{label}.{key} must be a non-negative integer")
        parsed[key] = item
    return parsed


def _parse_postings(
    value: JsonValue,
    path: Path,
    records: Mapping[str, SourceDocument],
) -> dict[str, tuple[Posting, ...]]:
    raw = _cache_mapping(value, path, "postings")
    parsed: dict[str, tuple[Posting, ...]] = {}
    for term, values in raw.items():
        if type(values) is not list:
            raise _cache_validation_error(path, f"postings.{term} must be an array")
        postings: list[Posting] = []
        previous_record_id: str | None = None
        for value_item in values:
            item = _cache_mapping(value_item, path, f"postings.{term} entry")
            record_id = _cache_string(item, "record_id", path)
            term_frequency = _cache_integer(item, "term_frequency", path)
            if record_id not in records or term_frequency <= 0:
                raise _cache_validation_error(path, f"postings.{term} contains an invalid entry")
            if previous_record_id is not None and record_id <= previous_record_id:
                raise _cache_validation_error(path, f"postings.{term} is not record_id sorted")
            previous_record_id = record_id
            postings.append(Posting(record_id=record_id, term_frequency=term_frequency))
        parsed[term] = tuple(postings)
    return parsed


def _parse_term_aliases(value: JsonValue, path: Path) -> dict[str, tuple[str, ...]]:
    raw = _cache_mapping(value, path, "term_aliases")
    return {
        term: tuple(_cache_string_list(expansions, path, f"term_aliases.{term}"))
        for term, expansions in raw.items()
    }


def _parse_cache(value: JsonValue, path: Path) -> Bm25Index:
    raw = _cache_mapping(value, path, "cache")
    records_raw = _cache_mapping(raw.get("records"), path, "records")
    records = {
        record_id: _parse_cached_record(record_id, record, path)
        for record_id, record in sorted(records_raw.items())
    }
    document_lengths = _parse_integer_mapping(raw.get("document_lengths"), path, "document_lengths")
    document_frequencies = _parse_integer_mapping(
        raw.get("document_frequencies"),
        path,
        "document_frequencies",
    )
    postings = _parse_postings(raw.get("postings"), path, records)
    if set(document_lengths) != set(records):
        raise _cache_validation_error(path, "document_lengths keys must match records")
    if {
        term: len(term_postings)
        for term, term_postings in postings.items()
    } != document_frequencies:
        raise _cache_validation_error(path, "document_frequencies must match postings")
    avgdl = _cache_float(raw, "avgdl", path)
    expected_avgdl = sum(document_lengths.values()) / len(records) if records else 0.0
    if not math.isclose(avgdl, expected_avgdl, rel_tol=0.0, abs_tol=1e-12):
        raise _cache_validation_error(path, "avgdl must match document_lengths")
    schema_version = _cache_integer(raw, "schema_version", path)
    if schema_version < 1:
        raise _cache_validation_error(path, "schema_version must be positive")
    fingerprints = IndexFingerprints(
        schema=_cache_string(raw, "schema_fingerprint", path),
        tokenizer=_cache_string(raw, "tokenizer_fingerprint", path),
        config=_cache_string(raw, "config_fingerprint", path),
        source=_cache_string(raw, "source_fingerprint", path),
    )
    if _cache_string(raw, "fingerprint", path) != fingerprints.combined:
        raise _cache_validation_error(path, "fingerprint does not match component fingerprints")
    return Bm25Index(
        collection=_cache_string(raw, "collection", path),
        k1=_cache_float(raw, "k1", path),
        b=_cache_float(raw, "b", path),
        fingerprints=fingerprints,
        document_lengths=document_lengths,
        avgdl=avgdl,
        document_frequencies=document_frequencies,
        postings=postings,
        records=records,
        term_aliases=_parse_term_aliases(raw.get("term_aliases"), path),
    )


def _read_cache(path: Path) -> Bm25Index:
    try:
        value: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise _cache_validation_error(path, "invalid JSON cache") from error
    except UnicodeError as error:
        raise _cache_validation_error(path, "cache is not valid UTF-8") from error
    except OSError as error:
        raise CacheReadError(path=path, reason="unable to read cache") from error
    return _parse_cache(value, path)


def _write_cache(path: Path, index: Bm25Index) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CacheWriteError(path=path, reason="unable to create cache directory") from error
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                _cache_payload(index),
                temporary_file,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                raise CacheWriteError(
                    path=path,
                    reason=f"atomic cache replacement failed; temporary cleanup failed: {cleanup_error}",
                ) from error
        raise CacheWriteError(path=path, reason="atomic cache replacement failed") from error


def _index_config(request: IndexRequest) -> Bm25Config:
    return Bm25Config(
        collection=request.collection,
        k1=request.profile["bm25"]["k1"],
        b=request.profile["bm25"]["b"],
        term_aliases=tuple(
            (term, tuple(expansions))
            for term, expansions in sorted(request.profile["term_aliases"].items())
        ),
    )


def load_or_build_index(request: IndexRequest) -> IndexLoadResult:
    sources = _configured_sources(request)
    fingerprints = _index_fingerprints(request, sources)
    configured_cache = Path(request.profile["cache"])
    cache_path = configured_cache if configured_cache.is_absolute() else request.project_root / configured_cache
    reason: CacheReason
    if request.force_reindex:
        reason = "forced"
    elif not cache_path.is_file():
        reason = "missing"
    else:
        try:
            cached = _read_cache(cache_path)
        except CacheValidationError:
            reason = "corrupt"
        else:
            if (
                cached.collection == request.collection
                and cached.fingerprints == fingerprints
                and cached.k1 == request.profile["bm25"]["k1"]
                and cached.b == request.profile["bm25"]["b"]
            ):
                return IndexLoadResult(
                    index=cached,
                    status="hit",
                    reason="current",
                    cache_path=cache_path,
                )
            reason = "stale"

    documents = _ingest_configured_sources(request, sources)
    index = build_index(documents, _index_config(request), fingerprints)
    _write_cache(cache_path, index)
    return IndexLoadResult(
        index=index,
        status="rebuilt",
        reason=reason,
        cache_path=cache_path,
    )
