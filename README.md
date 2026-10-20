# Bureaucat skill for Claude Code

A [Claude Code](https://claude.com/claude-code) skill that lets Claude manage tasks in a self-hosted
[Bureaucat](https://github.com/bureaucatorg/bureaucat) instance. Say "remember to renew the domain",
"what's on my plate?" or "OPS-7 is done" and Claude captures, lists, updates and comments on tasks
through Bureaucat's REST API.

It ships as two files:

- `SKILL.md` — instructions Claude follows: when to trigger, which project to pick, conventions for
  titles, states, dates and priorities.
- `bureaucat.py` — a dependency-free Python CLI (stdlib only, Python 3.8+) that wraps the API.
  Claude calls it, but you can use it directly too.

## Install

Clone into your Claude Code skills directory:

```sh
git clone https://github.com/tellship/bureaucat-tasks ~/.claude/skills/bureaucat
```

Claude Code picks up skills on the next session start. The directory name `bureaucat` becomes the
`/bureaucat` slash command.

## Configure

1. In your Bureaucat instance, go to **Settings → Personal Access Tokens** and create a token with
   the `read_write` scope. It starts with `bcat_`.
2. Add the instance URL and the token to the `env` block of `~/.claude/settings.json`:

   ```json
   {
     "env": {
       "BUREAUCAT_URL": "https://tasks.example.com",
       "BUREAUCAT_TOKEN": "bcat_..."
     }
   }
   ```

   `BUREAUCAT_URL` is the origin only, no `/api/v1` path.
3. Restart Claude Code. Check it works with:

   ```sh
   ~/.claude/skills/bureaucat/bureaucat.py projects
   ```

On macOS the token can instead live in the Keychain, service `bureaucat`, account `token`:

```sh
security add-generic-password -s bureaucat -a token -w 'bcat_...'
```

The environment variable wins when both are set.

## Use

In Claude Code, just talk about tasks:

- "remember to follow up with the printer vendor next Friday"
- "what's pending in the OPS project?"
- "mark OPS-12 as blocked and note that we're waiting on the invoice"
- `/bureaucat list everything due this week`

Claude resolves the project from your project names, checks for duplicates before adding, converts
relative dates to absolute ones, and moves tasks between states by name.

### CLI

Tasks are referenced as `KEY-NUM`, e.g. `OPS-12`. States and labels are passed by name.

| Command | Purpose |
|---------|---------|
| `projects` | List projects: key, name, description |
| `mine` | Tasks assigned to you across all projects |
| `states <PROJECT>` | State names and types for a project |
| `labels <PROJECT>` | Label names for a project |
| `list <PROJECT> [--state NAME] [--state-type T] [--priority N] [-q TEXT] [--by-due]` | List or search tasks |
| `get <KEY-NUM>` | Full task with description, assignees and comments |
| `add <PROJECT> "<title>" [--desc TEXT] [--priority N] [--state NAME] [--due DATE] [--start DATE] [--label NAME]...` | Create a task |
| `update <KEY-NUM> [--title] [--desc] [--priority N] [--state NAME] [--due DATE\|none] [--start DATE\|none]` | Edit or move a task |
| `comment <KEY-NUM> "<text>"` | Add a comment |

Dates take `YYYY-MM-DD` or an ISO datetime in local time. Priority is `0` none, `1` low, `2` medium,
`3` high, `4` urgent. State types are fixed (`backlog`, `unstarted`, `started`, `completed`,
`cancelled`); state names are whatever your project defines.

## Notes

- There is no delete. Tasks are closed by moving them to a completed or cancelled state.
- Bureaucat does not send due-date alerts. Pair with a reminder tool if you need notifications.
- The script sends a custom `User-Agent` because some reverse proxies block Python's default one.
- Bureaucat's published swagger lags its code. The API calls here follow the handlers in the
  upstream source, not the swagger.

## License

MIT
