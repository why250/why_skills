#!/usr/bin/env python3
"""Mechanical validator for the why_skills repository.

Errors are deterministic structural violations. Warnings are maintenance
candidates that require human judgement or deliberate migration.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILLS = ROOT / "skills"
README = ROOT / "README.md"


@dataclass
class Skill:
    path: Path
    legacy_layout: bool

    @property
    def skill_md(self) -> Path:
        return self.path / "SKILL.md"

    @property
    def rel_skill_md(self) -> str:
        return self.skill_md.relative_to(ROOT).as_posix()


def discover_skills() -> list[Skill]:
    found: list[Skill] = []
    for first in sorted(SKILLS.iterdir()):
        if not first.is_dir():
            continue
        if (first / "SKILL.md").is_file():
            found.append(Skill(first, legacy_layout=True))
        for second in sorted(first.iterdir()):
            if second.is_dir() and (second / "SKILL.md").is_file():
                found.append(Skill(second, legacy_layout=False))
    return found


def frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    return text[4:end]


def scalar(fm: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*['\"]?([^\n'\"]+)['\"]?\s*$", fm)
    return match.group(1).strip() if match else None


def local_links(skill: Skill, text: str) -> list[str]:
    targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    missing: list[str] = []
    for target in targets:
        target = target.strip().split("#", 1)[0]
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        if target.startswith("#"):
            continue
        candidate = (skill.path / target).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            continue
        if not candidate.exists():
            missing.append(target)
    return missing


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    skills = discover_skills()
    readme = README.read_text(encoding="utf-8") if README.exists() else ""
    names: dict[str, str] = {}

    for skill in skills:
        text = skill.skill_md.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            errors.append(f"{skill.rel_skill_md}: missing YAML frontmatter")
            continue

        name = scalar(fm, "name")
        if not name:
            errors.append(f"{skill.rel_skill_md}: missing frontmatter name")
            continue

        if name != skill.path.name:
            errors.append(
                f"{skill.rel_skill_md}: frontmatter name '{name}' != directory '{skill.path.name}'"
            )

        if name in names:
            errors.append(
                f"duplicate skill name '{name}': {names[name]} and {skill.rel_skill_md}"
            )
        else:
            names[name] = skill.rel_skill_md

        if skill.legacy_layout:
            warnings.append(
                f"{skill.rel_skill_md}: legacy top-level layout; prefer skills/<category>/<skill>/"
            )

        if skill.rel_skill_md not in readme:
            warnings.append(f"{skill.rel_skill_md}: not indexed in README.md")

        user_invoked = bool(
            re.search(r"(?m)^disable-model-invocation:\s*true\s*$", fm)
        )
        openai_yaml = skill.path / "agents" / "openai.yaml"
        if user_invoked:
            if not openai_yaml.exists():
                warnings.append(
                    f"{skill.rel_skill_md}: user-invoked but agents/openai.yaml is missing"
                )
            elif "allow_implicit_invocation: false" not in openai_yaml.read_text(
                encoding="utf-8"
            ):
                warnings.append(
                    f"{skill.rel_skill_md}: user-invoked but Codex implicit invocation is not disabled"
                )

        for target in local_links(skill, text):
            warnings.append(f"{skill.rel_skill_md}: missing local link target {target!r}")

    print(f"skills: {len(skills)}")
    print(f"errors: {len(errors)}")
    print(f"warnings: {len(warnings)}")

    if errors:
        print("\nERRORS")
        for item in errors:
            print(f"- {item}")

    if warnings:
        print("\nWARNINGS")
        for item in warnings:
            print(f"- {item}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
