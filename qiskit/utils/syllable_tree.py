# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utilities for building a simple syllable tree.

The :class:`~qiskit.utils.syllable_tree.SyllableTree` class builds a light-weight
hierarchical representation of the syllables that make up a word.  It follows a
basic linguistic decomposition into onset, nucleus and coda and offers helpers
to render the structure as ASCII art or JSON data.  The module also exposes a
small command line interface that can be invoked with::

    python -m qiskit.utils.syllable_tree VOORBEELDWOORD

The heuristics in this module are intentionally conservative: they aim to
generate readable trees for Dutch- and English-like words without pretending to
be a complete syllabification engine.  Users can provide manual syllable hints
when the automated guess is insufficient.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import argparse
import json
import re
import sys
from typing import Iterator, List, Sequence

_VOWELS = set("aeiouyáéíóúàèìòùäëïöüâêîôû")
_ONSET_CLUSTERS = {
    "sch",
    "scr",
    "spl",
    "spr",
    "str",
    "thr",
    "chr",
    "phr",
    "shr",
    "squ",
    "br",
    "cr",
    "dr",
    "fr",
    "gr",
    "pr",
    "tr",
    "vr",
    "kr",
    "bl",
    "cl",
    "fl",
    "gl",
    "pl",
    "sl",
    "sk",
    "sm",
    "sn",
    "sp",
    "st",
    "sw",
    "dw",
    "tw",
    "ch",
    "gh",
    "ph",
    "rh",
    "sh",
    "th",
    "wh",
    "gn",
    "kn",
    "qu",
}
_SPLIT_HINT = re.compile(r"[-\s]+")


@dataclass
class TreeNode:
    """A node within a syllable tree."""

    label: str
    children: List["TreeNode"] = field(default_factory=list)

    def add_child(self, node: "TreeNode") -> "TreeNode":
        """Attach *node* as a child and return it."""

        self.children.append(node)
        return node

    def render(self) -> str:
        """Render the tree as ASCII art."""

        lines: List[str] = []

        def _render(current: "TreeNode", prefix: str, is_last: bool) -> None:
            connector = "" if not prefix else ("└── " if is_last else "├── ")
            lines.append(f"{prefix}{connector}{current.label}")
            next_prefix = prefix + ("    " if is_last else "│   ")
            for index, child in enumerate(current.children):
                _render(child, next_prefix, index == len(current.children) - 1)

        _render(self, "", True)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert the node to a JSON-serialisable dictionary."""

        return {
            "label": self.label,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class SyllableTree:
    """Representation of the syllable structure of a word."""

    word: str
    syllables: List[str]
    root: TreeNode

    @classmethod
    def from_word(
        cls, word: str, syllable_hint: Sequence[str] | None = None
    ) -> "SyllableTree":
        """Construct a tree for *word*.

        Args:
            word: Input word that will be analysed.
            syllable_hint: Optional manual syllable split.  When omitted a
                simple heuristic is used to guess the syllables.
        """

        syllables = list(syllable_hint) if syllable_hint else syllabify(word)
        root = TreeNode(f"Word: {word}")
        for index, syllable in enumerate(syllables, start=1):
            branch = TreeNode(f"Syllable {index}: {syllable}")
            onset, nucleus, coda = split_onset_nucleus_coda(syllable)
            if onset:
                onset_node = branch.add_child(TreeNode("Onset"))
                for char in onset:
                    onset_node.add_child(TreeNode(char))
            rime = TreeNode("Rime")
            if nucleus:
                nucleus_node = rime.add_child(TreeNode("Nucleus"))
                nucleus_node.add_child(TreeNode(nucleus))
            if coda:
                coda_node = rime.add_child(TreeNode("Coda"))
                for char in coda:
                    coda_node.add_child(TreeNode(char))
            if rime.children:
                branch.add_child(rime)
            if not branch.children:
                for char in syllable:
                    branch.add_child(TreeNode(char))
            root.add_child(branch)
        return cls(word=word, syllables=syllables, root=root)

    def render(self) -> str:
        """Render the tree as ASCII art."""

        return self.root.render()

    def to_dict(self) -> dict:
        """Convert the tree to a dictionary."""

        return {
            "word": self.word,
            "syllables": list(self.syllables),
            "tree": self.root.to_dict(),
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Return a JSON dump of the tree."""

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def __str__(self) -> str:
        return self.render()


def syllabify(word: str) -> List[str]:
    """Split *word* into syllables using a light-weight heuristic."""

    word = word.strip()
    if not word:
        return []
    parts = [part for part in _SPLIT_HINT.split(word) if part]
    if not parts:
        return [word]
    syllables: List[str] = []
    for part in parts:
        syllables.extend(_syllabify_segment(part))
    return syllables or [word]


def build_syllable_tree(
    word: str, syllable_hint: Sequence[str] | None = None
) -> SyllableTree:
    """Convenience wrapper around :meth:`SyllableTree.from_word`."""

    return SyllableTree.from_word(word, syllable_hint=syllable_hint)


def parse_syllable_hint(hint: str) -> List[str]:
    """Parse a manually provided syllable hint string."""

    return [part for part in _SPLIT_HINT.split(hint) if part]


def split_onset_nucleus_coda(syllable: str) -> tuple[str, str, str]:
    """Split *syllable* into onset, nucleus and coda components."""

    if not syllable:
        return "", "", ""
    lower = syllable.lower()
    try:
        first_vowel = next(index for index, char in enumerate(lower) if char in _VOWELS)
    except StopIteration:
        return syllable, "", ""
    onset = syllable[:first_vowel]
    nucleus_end = first_vowel
    while nucleus_end < len(syllable) and lower[nucleus_end] in _VOWELS:
        nucleus_end += 1
    nucleus = syllable[first_vowel:nucleus_end]
    coda = syllable[nucleus_end:]
    return onset, nucleus, coda


def run_syllable_tree_app(argv: Sequence[str] | None = None) -> int:
    """Entry point for the small syllable-tree command line utility."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("word", nargs="?", help="Woord of zin om te analyseren.")
    parser.add_argument(
        "-s",
        "--syllables",
        help="Handmatige lettergreep verdeling, gescheiden door '-' of spaties.",
    )
    parser.add_argument("--json", action="store_true", help="Geef de boom als JSON terug.")
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start een interactieve modus die meerdere woorden accepteert.",
    )
    args = parser.parse_args(argv)

    def _build(word: str, override: Sequence[str] | None) -> SyllableTree:
        return build_syllable_tree(word, syllable_hint=override)

    try:
        if args.interactive:
            default_hint = parse_syllable_hint(args.syllables) if args.syllables else None
            pending: list[str] = [args.word] if args.word else []
            while True:
                word = pending.pop(0) if pending else input("Woord (leeg om te stoppen): ").strip()
                if not word:
                    break
                tree = _build(word, default_hint)
                _print_tree(tree, args.json)
        else:
            if not args.word:
                parser.error("geef een woord op of gebruik --interactive")
            hint = parse_syllable_hint(args.syllables) if args.syllables else None
            _print_tree(_build(args.word, hint), args.json)
    except (EOFError, KeyboardInterrupt):
        return 1
    return 0


def _print_tree(tree: SyllableTree, as_json: bool) -> None:
    if as_json:
        print(tree.to_json())
    else:
        print(tree.render())


def _syllabify_segment(word: str) -> List[str]:
    lower = word.lower()
    nuclei = list(_find_vowel_clusters(lower))
    if not nuclei:
        return [word]
    syllables: List[str] = []
    previous_boundary = 0
    for index, (start, end) in enumerate(nuclei):
        if index == len(nuclei) - 1:
            syllables.append(word[previous_boundary:])
        else:
            next_start, _ = nuclei[index + 1]
            consonant_cluster = word[end:next_start]
            coda_length = _split_consonant_cluster(consonant_cluster)
            boundary = end + coda_length
            syllables.append(word[previous_boundary:boundary])
            previous_boundary = boundary
    return [segment for segment in syllables if segment]


def _find_vowel_clusters(word: str) -> Iterator[tuple[int, int]]:
    index = 0
    while index < len(word):
        if word[index] in _VOWELS:
            start = index
            while index < len(word) and word[index] in _VOWELS:
                index += 1
            yield start, index
        else:
            index += 1


def _split_consonant_cluster(cluster: str) -> int:
    if not cluster:
        return 0
    lower = cluster.lower()
    length = len(cluster)
    max_onset = min(3, length)
    for onset_size in range(max_onset, 0, -1):
        if lower[-onset_size:] in _ONSET_CLUSTERS:
            return length - onset_size
    return max(length - 1, 0)


if __name__ == "__main__":  # pragma: no cover - CLI helper
    sys.exit(run_syllable_tree_app())
