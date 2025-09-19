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

"""Tests for the syllable tree helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "qiskit" / "utils" / "syllable_tree.py"
SPEC = importlib.util.spec_from_file_location("qiskit.utils.syllable_tree", MODULE_PATH)
syllable_tree = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader  # for type checkers
sys.modules.setdefault("qiskit.utils.syllable_tree", syllable_tree)
SPEC.loader.exec_module(syllable_tree)

SyllableTree = syllable_tree.SyllableTree
build_syllable_tree = syllable_tree.build_syllable_tree
parse_syllable_hint = syllable_tree.parse_syllable_hint
run_syllable_tree_app = syllable_tree.run_syllable_tree_app
split_onset_nucleus_coda = syllable_tree.split_onset_nucleus_coda
syllabify = syllable_tree.syllabify


@pytest.mark.parametrize(
    "word,expected",
    [
        ("lettergreep", ["let", "ter", "greep"]),
        ("programma", ["pro", "gram", "ma"]),
        ("boom", ["boom"]),
        ("variaties", ["va", "ria", "ties"]),
    ],
)
def test_syllabify_examples(word, expected):
    assert syllabify(word) == expected


def test_parse_syllable_hint():
    assert parse_syllable_hint("let-ter greep") == ["let", "ter", "greep"]


def test_split_onset_nucleus_coda():
    assert split_onset_nucleus_coda("greep") == ("gr", "ee", "p")
    assert split_onset_nucleus_coda("boom") == ("b", "oo", "m")
    assert split_onset_nucleus_coda("ssh") == ("ssh", "", "")


def test_build_tree_structure():
    tree = build_syllable_tree("lettergreep")
    assert tree.word == "lettergreep"
    syllable_labels = [node.label for node in tree.root.children]
    assert syllable_labels == ["Syllable 1: let", "Syllable 2: ter", "Syllable 3: greep"]
    onset = tree.root.children[0].children[0]
    assert onset.label == "Onset"
    assert [child.label for child in onset.children] == ["l"]
    rime = tree.root.children[0].children[1]
    assert rime.label == "Rime"
    nucleus, coda = rime.children
    assert nucleus.label == "Nucleus"
    assert [child.label for child in nucleus.children] == ["e"]
    assert coda.label == "Coda"
    assert [child.label for child in coda.children] == ["t"]


def test_tree_render_and_json():
    tree = SyllableTree.from_word("programma")
    rendered = tree.render()
    assert "Syllable 1: pro" in rendered
    payload = json.loads(tree.to_json())
    assert payload["word"] == "programma"
    assert payload["syllables"] == ["pro", "gram", "ma"]


def test_cli_returns_error_on_interrupt(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError()))
    exit_code = run_syllable_tree_app(["--interactive"])
    assert exit_code == 1
