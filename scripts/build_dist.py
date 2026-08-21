#!/usr/bin/env python3
"""Validate the canonical TSV and build import files for major Japanese IMEs."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "racehorses.tsv"
DIST = ROOT / "dist"
FIELDS = ["reading", "word", "pos", "japanese_form"]
BV_TOKEN_RE = re.compile(
    r"ヴャ|ヴュ|ヴョ|ヴァ|ヴィ|ヴェ|ヴォ|ヴ|ビャ|ビュ|ビョ|バ|ビ|ブ|ベ|ボ"
)
NON_BV_SOURCE_FORMS = {
    ("Baryshnikov", "バリシニコフ"),
    ("Eldar Eldarov", "エルダーエルダロフ"),
    ("Fasliyev", "ファスリエフ"),
    ("Jan Vermeer", "ヤンフェルメール"),
    ("Johannes Vermeer", "ヨハネスフェルメール"),
    ("Kristov", "クリストフ"),
    ("Makarova", "マカロワ"),
    ("Volkstok'n'barrell", "フォルクストクンバレル"),
    ("Volkstok'n'barrell", "フォルクストックンバレル"),
}


def katakana_to_hiragana(value: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if 0x30A1 <= ord(char) <= 0x30F6 else char
        for char in value
    )


def bv_targets(word: str) -> list[str]:
    word = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", word)
    targets: list[str] = []
    for part in re.findall(r"[a-z]+", word.casefold()):
        previous = ""
        for char in part:
            if char in "bv" and char != previous:
                targets.append(char)
            elif part == "of" and char == "f":
                targets.append("b")
            elif part == "stephen" and char == "p":
                targets.append("b")
            previous = char
    return targets


def validate_bv(rows: list[dict[str, str]]) -> None:
    by_word: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_word[row["word"]].append(row)

    for word, word_rows in by_word.items():
        targets = bv_targets(word)
        if "v" not in targets and "b" not in targets:
            continue
        v_coverage: dict[int, set[str]] = {
            index: set() for index, target in enumerate(targets) if target == "v"
        }
        aligned = 0
        for row in word_rows:
            form = row["japanese_form"]
            tokens = BV_TOKEN_RE.findall(form)
            if len(tokens) != len(targets):
                if "v" not in targets and not any(
                    token.startswith("ヴ") for token in tokens
                ):
                    continue
                if (word, form) not in NON_BV_SOURCE_FORMS:
                    raise ValueError(
                        f"unreviewed v/b alignment: {word!r} / {form!r}"
                    )
                for index in v_coverage:
                    v_coverage[index].add("b")
                continue
            aligned += 1
            for index, (target, token) in enumerate(zip(targets, tokens)):
                is_v_form = token.startswith("ヴ")
                if target == "b" and is_v_form:
                    raise ValueError(
                        f"English b must not generate a v-form: {word!r} / {form!r}"
                    )
                if target == "v":
                    v_coverage[index].add("v" if is_v_form else "b")

        if v_coverage and not aligned:
            raise ValueError(f"no aligned v-form available: {word!r}")
        for index, forms in v_coverage.items():
            if forms != {"b", "v"}:
                raise ValueError(
                    f"English v needs both b- and v-forms: {word!r} at target {index}"
                )


def load_rows() -> list[dict[str, str]]:
    with CANONICAL.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected columns: {reader.fieldnames!r}")
        rows = list(reader)

    seen: set[tuple[str, str]] = set()
    previous: tuple[str, str, str] | None = None
    for line_number, row in enumerate(rows, start=2):
        if any(not row[field] for field in FIELDS):
            raise ValueError(f"line {line_number}: empty required field")
        if row["pos"] != "noun":
            raise ValueError(f"line {line_number}: unsupported pos {row['pos']!r}")
        if "・" in row["japanese_form"]:
            raise ValueError(f"line {line_number}: middle dot is not allowed")
        if katakana_to_hiragana(row["japanese_form"]) != row["reading"]:
            raise ValueError(f"line {line_number}: reading and Japanese form differ")
        key = (row["reading"], row["word"])
        if key in seen:
            raise ValueError(f"line {line_number}: duplicate conversion {key!r}")
        seen.add(key)
        sort_key = (row["reading"], row["word"].casefold(), row["word"])
        if previous is not None and sort_key < previous:
            raise ValueError(f"line {line_number}: rows are not sorted")
        previous = sort_key

    if not rows:
        raise ValueError("canonical dictionary is empty")
    validate_bv(rows)
    return rows


def write_utf16(path: Path, text: str, byte_order: str) -> None:
    if byte_order == "be":
        path.write_bytes(b"\xfe\xff" + text.encode("utf-16-be"))
    elif byte_order == "le":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    else:
        raise ValueError(f"unsupported byte order: {byte_order}")


def apple_csv_field(value: str) -> str:
    """Quote fields containing characters called out by Apple's CSV format."""
    if any(char in value for char in ', \"\r\n'):
        return f'"{value.replace(chr(34), chr(34) * 2)}"'
    return value


def build(rows: list[dict[str, str]]) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    entries = [f"{row['reading']}\t{row['word']}\t名詞" for row in rows]

    atok_text = "\r\n".join(["!!ATOK_TANGO_TEXT_HEADER_1", *entries, ""])
    write_utf16(DIST / "atok.txt", atok_text, "be")

    google_text = "\n".join([*entries, ""])
    (DIST / "google-ime.txt").write_bytes(google_text.encode("utf-8"))

    microsoft_header = [
        "!Microsoft IME Dictionary Tool",
        "!Version:",
        "!Format:WORDLIST",
        "!Output File Name:microsoft-ime.txt",
        "!DateTime:",
        "!User Dictionary Name:Overseas Racehorse IME Dictionary",
    ]
    microsoft_text = "\r\n".join([*microsoft_header, *entries, ""])
    write_utf16(DIST / "microsoft-ime.txt", microsoft_text, "le")

    apple_entries = [
        ",".join(
            [
                apple_csv_field(row["reading"]),
                apple_csv_field(row["word"]),
                "普通名詞",
            ]
        )
        for row in rows
    ]
    apple_text = "\n".join([*apple_entries, ""])
    (DIST / "apple-japanese-input.txt").write_bytes(apple_text.encode("utf-8"))


def verify_outputs(expected_entries: int) -> None:
    atok = (DIST / "atok.txt").read_text(encoding="utf-16")
    google = (DIST / "google-ime.txt").read_text(encoding="utf-8")
    microsoft = (DIST / "microsoft-ime.txt").read_text(encoding="utf-16")
    apple = (DIST / "apple-japanese-input.txt").read_text(encoding="utf-8")

    if not atok.startswith("!!ATOK_TANGO_TEXT_HEADER_1\n"):
        raise ValueError("invalid ATOK header")
    if google.count("\n") != expected_entries:
        raise ValueError("unexpected Google Japanese Input entry count")
    if not microsoft.startswith("!Microsoft IME Dictionary Tool\n"):
        raise ValueError("invalid Microsoft IME header")
    if microsoft.count("\n") != expected_entries + 6:
        raise ValueError("unexpected Microsoft IME entry count")
    apple_rows = list(csv.reader(apple.splitlines()))
    if len(apple_rows) != expected_entries:
        raise ValueError("unexpected Apple Japanese Input entry count")
    if any(len(row) != 3 or row[2] != "普通名詞" for row in apple_rows):
        raise ValueError("invalid Apple Japanese Input row")


def main() -> None:
    rows = load_rows()
    build(rows)
    verify_outputs(len(rows))
    unique_horses = len({row["word"].casefold() for row in rows})
    print(f"built {len(rows):,} conversions for {unique_horses:,} horses")


if __name__ == "__main__":
    main()
