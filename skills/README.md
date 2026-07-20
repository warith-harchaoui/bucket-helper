# bucket-helper as an agent skill

`skills/bucket-helper/` packages `bucket-helper` as a **Claude Skill** *and* an
**OpenCode skill** — both ecosystems read the same `SKILL.md` (YAML frontmatter
+ Markdown body + progressive-disclosure `references/`). Installing it lets an
agent discover bucket-helper and run object-storage operations (upload /
download / list / exists / delete / make-bucket / tempfile / strip-path) on the
user's behalf without the user opening a terminal.

## Layout

```
skills/bucket-helper/
├── SKILL.md                 # name + trigger-rich description + instructions
└── references/
    ├── cli-reference.md      # full subcommand + flag matrix, output contract
    ├── surfaces.md           # library, CLIs, API, MCP, credentials schema (no GUI)
    └── triggers.md           # exhaustive, auditable trigger catalogue
```

Progressive disclosure: `SKILL.md` stays short and discoverable; the depth lives
in `references/*.md`, loaded only when a task needs it.

## Install for Claude Code / Claude Desktop

Skills live under `~/.claude/skills/` (user) or `.claude/skills/` (project). To
track this repo's copy rather than duplicate it, symlink it:

```bash
ln -sfn "$PWD/skills/bucket-helper" ~/.claude/skills/bucket-helper
# per-project instead:
mkdir -p /path/to/project/.claude/skills
ln -sfn "$PWD/skills/bucket-helper" /path/to/project/.claude/skills/bucket-helper
```

## Install for OpenCode

OpenCode reads skills from `~/.opencode/skills/` (or `~/.config/opencode/skills/`):

```bash
mkdir -p ~/.opencode/skills
ln -sfn "$PWD/skills/bucket-helper" ~/.opencode/skills/bucket-helper
```

## Keeping triggers enforced

The host model only sees `SKILL.md`'s `description` before deciding to load the
skill, so every real trigger must appear there. `references/triggers.md` is the
human-reviewable superset — keep the two in sync, and mirror the repo-root
`TRIGGERS.md` (the user-facing catalogue).

## Notes

- **No secrets live in this skill.** Credentials are loaded at runtime by the
  user's own `s3_config.json` / `s3_config.yaml` / `.env` / environment — never
  committed here (the repo `.gitignore` blocks real `*config.json` files).
- **Remote by design, no GUI.** bucket-helper moves data to a *remote* bucket;
  there is no local-first mode and no browser GUI. The skill does not offer one.
