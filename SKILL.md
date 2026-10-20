---
name: bureaucat
description: Manage tasks in a Bureaucat instance — capture, list, search, update, move between states, and comment. Invoked with /bureaucat or whenever the user asks to add/remember a task or todo, asks what's on their plate or what's pending, or says a task is done/blocked/in progress. Uses ~/.claude/skills/bureaucat/bureaucat.py.
argument-hint: <what to do, in plain language>
allowed-tools: Bash
---

# Bureaucat — task management

Script: `~/.claude/skills/bureaucat/bureaucat.py <command>`

| Command | Purpose |
|---------|---------|
| `projects` | List projects: key, name, description |
| `mine` | Tasks assigned to me across all projects |
| `states <PROJECT>` | State names + `state_type` for a project |
| `labels <PROJECT>` | Label names for a project |
| `list <PROJECT> [--state NAME] [--state-type T] [--priority N] [-q TEXT] [--by-due]` | List/search tasks (`-q` matches title; `--by-due` sorts soonest first) |
| `get <KEY-NUM>` | Full task: description, assignees, comments |
| `add <PROJECT> "<title>" [--desc TEXT] [--priority N] [--state NAME] [--due DATE] [--start DATE] [--label NAME]...` | Create task |
| `update <KEY-NUM> [--title] [--desc] [--priority N] [--state NAME] [--due DATE\|none] [--start DATE\|none]` | Edit or move a task; `none` clears a date |
| `comment <KEY-NUM> "<text>"` | Add a comment |

Tasks are referenced as `KEY-NUM` (project key + task number, e.g. `OPS-12`). States and labels are passed by **name**; the script resolves IDs.

## Choosing the project

There is no default project. Run `projects` and pick the one matching the task's topic from its name/description. Ask only when two projects fit equally or none fits. For "what's pending?" style questions with no project named, run `list` across every project.

## Conventions

- **Before adding**, run `list <PROJECT> -q "<keyword>"` to avoid duplicates; if a matching open task exists, `update` or `comment` on it instead.
- **Title** is a short imperative ("Renew nearmio.com domain"). Context, links and acceptance criteria go in `--desc` (markdown).
- **Done / blocked / started** → `update <ref> --state <name>`. State names are per project; run `states` first rather than guessing. Omitting `--state` on `add` uses the project's default state.
- **Progress notes** go in `comment`, not by rewriting the description.
- **Dates**: `--due` / `--start` take `YYYY-MM-DD` or an ISO datetime in local time. Convert natural language ("Friday", "end of month") to an absolute date yourself using today's date from context. Bureaucat does not alert on due dates; offer the `remind` skill if the user wants an actual notification.
- **Priority**: `0` none (default), `1` low, `2` medium, `3` high, `4` urgent. Set one only when the user signals urgency.
- **State types** are fixed: `backlog`, `unstarted`, `started`, `completed`, `cancelled`. State *names* are per project. For "what's open?", list with `--state-type` for `unstarted` and `started` (and `backlog` if asked).
- The script has no delete; tasks are closed by moving them to a done/cancelled state.

Report the script's output line (`KEY-NUM [State] Pn title`) back to the user after every write.

## Configuration

Both values live in the `env` block of `~/.claude/settings.json`:

- `BUREAUCAT_URL` — the instance origin with no path, e.g. `https://tasks.example.com`. The script appends `/api/v1`.
- `BUREAUCAT_TOKEN` — a Personal Access Token (`bcat_…`, scope `read_write`, created at `<instance>/settings` → Personal Access Tokens). Fallback: macOS Keychain, service `bureaucat`, account `token`.

If the script exits with "BUREAUCAT_URL not set", ask the user for their instance URL and tell them where to put it; never guess a host.

A `401` means the token is expired or revoked, a `403` on writes means it is `read_only` — ask the user to replace the value in `settings.json` and restart the session. Never ask for the token or a password in chat, and never print `$BUREAUCAT_TOKEN`.

## Examples

```
"remember to renew the example.com domain before the end of the month"
→ bureaucat.py projects
→ bureaucat.py list OPS -q "domain"
→ bureaucat.py add OPS "Renew example.com domain" --due 2026-10-31

"OPS-7 is done"
→ bureaucat.py states OPS
→ bureaucat.py update OPS-7 --state Done
```

## API reference

The published swagger (`docs/swagger.json`) lags the code: it omits dates, PATs, subtasks, cycles, modules and `/me/tasks`. Ground truth is the source at github.com/bureaucatorg/bureaucat — request/response structs in `internal/handlers/*.go`, routes in `internal/server/routes.go`.
