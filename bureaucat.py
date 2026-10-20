#!/usr/bin/env python3
"""Bureaucat task CLI.

Instance: $BUREAUCAT_URL is the instance origin, e.g. https://tasks.example.com
(env block of ~/.claude/settings.json); the script appends /api/v1.
Auth: bearer token from $BUREAUCAT_TOKEN (same env block),
else macOS Keychain (service "bureaucat", account "token").

Tasks are referenced as KEY-NUM (e.g. OPS-12): project key + task number.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

def base_url():
    origin = os.environ.get("BUREAUCAT_URL")
    if not origin:
        sys.exit("BUREAUCAT_URL not set. Set it to your instance origin (e.g. https://tasks.example.com) "
                 "in the env block of ~/.claude/settings.json")
    return origin.rstrip("/") + "/api/v1"


def token():
    if os.environ.get("BUREAUCAT_TOKEN"):
        return os.environ["BUREAUCAT_TOKEN"]
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "bureaucat", "-a", "token", "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit("No token. Set BUREAUCAT_TOKEN in the env block of ~/.claude/settings.json")
    return r.stdout.strip()


def api(method, path, body=None, query=None):
    url = base_url() + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        # Some reverse proxies (e.g. Cloudflare) block urllib's default User-Agent
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
                 "User-Agent": "bureaucat-cli"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:500]}")


def split_ref(ref):
    key, _, num = ref.rpartition("-")
    if not key or not num.isdigit():
        sys.exit(f"Bad task ref {ref!r}, expected KEY-NUM")
    return key, num


def task_path(ref):
    key, num = split_ref(ref)
    return f"/projects/{key}/tasks/{num}"


def state_id(project, name):
    states = api("GET", f"/projects/{project}/states")
    for s in states:
        if s["name"].lower() == name.lower():
            return s["id"]
    sys.exit(f"No state {name!r} in {project}. States: {', '.join(s['name'] for s in states)}")


def label_ids(project, names):
    labels = {l["name"].lower(): l["id"] for l in api("GET", f"/projects/{project}/labels")}
    missing = [n for n in names if n.lower() not in labels]
    if missing:
        sys.exit(f"No label(s) {missing} in {project}. Labels: {', '.join(labels)}")
    return [labels[n.lower()] for n in names]


def when(value):
    """YYYY-MM-DD or ISO datetime (local time) -> RFC3339; "none" -> null (clears the date)."""
    if value.lower() == "none":
        return None
    return datetime.datetime.fromisoformat(value).astimezone().isoformat()


def task_line(t):
    labels = " ".join("#" + l["name"] for l in t.get("labels") or [])
    due = f"due {t['due_date'][:10]}" if t.get("due_date") else ""
    return f"{t['project_key']}-{t['task_number']}\t[{t['state_name']}]\tP{t['priority']}\t{t['title']}\t{due}\t{labels}".rstrip()


def print_tasks(path, query):
    page = 1
    while True:
        r = api("GET", path, query={**query, "page": page, "per_page": 100})
        for t in r["tasks"]:
            print(task_line(t))
        if page >= r["total_pages"]:
            break
        page += 1


def cmd_projects(a):
    page = 1
    while True:
        r = api("GET", "/projects", query={"page": page, "per_page": 100})
        for p in r["projects"]:
            print(f"{p['project_key']}\t{p['name']}\t{p.get('description') or ''}")
        if page >= r["total_pages"]:
            break
        page += 1


def cmd_states(a):
    for s in api("GET", f"/projects/{a.project}/states"):
        default = " (default)" if s.get("is_default") else ""
        print(f"{s['name']}\t{s['state_type']}{default}")


def cmd_labels(a):
    for l in api("GET", f"/projects/{a.project}/labels"):
        print(l["name"])


def cmd_list(a):
    query = {"state_type": a.state_type, "priority": a.priority, "q": a.q}
    if a.state:
        query["state_id"] = state_id(a.project, a.state)
    if a.by_due:
        query.update(sort_by="due_date", sort_dir="asc")
    print_tasks(f"/projects/{a.project}/tasks", query)


def cmd_mine(a):
    print_tasks("/me/tasks", {})


def cmd_get(a):
    t = api("GET", task_path(a.ref))
    print(task_line(t))
    print(f"created {t['created_at']} by {t['creator_username']}, updated {t['updated_at']}")
    if t.get("assignees"):
        print("assignees: " + ", ".join(x["username"] for x in t["assignees"]))
    if t.get("description"):
        print("\n" + t["description"])
    comments = api("GET", task_path(a.ref) + "/comments")
    for c in comments:
        print(f"\n--- {c['username']} {c['created_at']}\n{c['content']}")


def cmd_add(a):
    body = {"title": a.title}
    if a.desc:
        body["description"] = a.desc
    if a.priority is not None:
        body["priority"] = a.priority
    if a.state:
        body["state_id"] = state_id(a.project, a.state)
    for field, value in (("due_date", a.due), ("start_date", a.start)):
        if value:
            body[field] = when(value)
    if a.label:
        body["labels"] = label_ids(a.project, a.label)
    print(task_line(api("POST", f"/projects/{a.project}/tasks", body)))


def cmd_update(a):
    key, _ = split_ref(a.ref)
    body = {}
    if a.title:
        body["title"] = a.title
    if a.desc is not None:
        body["description"] = a.desc
    if a.priority is not None:
        body["priority"] = a.priority
    if a.state:
        body["state_id"] = state_id(key, a.state)
    for field, value in (("due_date", a.due), ("start_date", a.start)):
        if value:
            body[field] = when(value)
    if not body:
        sys.exit("Nothing to update")
    print(task_line(api("PATCH", task_path(a.ref), body)))


def cmd_comment(a):
    c = api("POST", task_path(a.ref) + "/comments", {"content": a.text})
    print(f"commented on {a.ref} ({c['id']})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("projects").set_defaults(f=cmd_projects)
    sub.add_parser("mine", help="tasks assigned to me, all projects").set_defaults(f=cmd_mine)

    for name, f in (("states", cmd_states), ("labels", cmd_labels)):
        s = sub.add_parser(name)
        s.add_argument("project")
        s.set_defaults(f=f)

    s = sub.add_parser("list")
    s.add_argument("project")
    s.add_argument("--state", help="state name")
    s.add_argument("--state-type")
    s.add_argument("--priority", type=int, help="0 none, 1 low, 2 medium, 3 high, 4 urgent")
    s.add_argument("-q", help="search title")
    s.add_argument("--by-due", action="store_true", help="sort by due date, soonest first")
    s.set_defaults(f=cmd_list)

    s = sub.add_parser("get")
    s.add_argument("ref")
    s.set_defaults(f=cmd_get)

    s = sub.add_parser("add")
    s.add_argument("project")
    s.add_argument("title")
    s.add_argument("--desc")
    s.add_argument("--priority", type=int, help="0 none, 1 low, 2 medium, 3 high, 4 urgent")
    s.add_argument("--state", help="state name (default: project's default state)")
    s.add_argument("--due", help="YYYY-MM-DD or ISO datetime")
    s.add_argument("--start", help="YYYY-MM-DD or ISO datetime")
    s.add_argument("--label", action="append", help="label name, repeatable")
    s.set_defaults(f=cmd_add)

    s = sub.add_parser("update")
    s.add_argument("ref")
    s.add_argument("--title")
    s.add_argument("--desc")
    s.add_argument("--priority", type=int, help="0 none, 1 low, 2 medium, 3 high, 4 urgent")
    s.add_argument("--state", help="state name, e.g. Done")
    s.add_argument("--due", help='YYYY-MM-DD, ISO datetime, or "none" to clear')
    s.add_argument("--start", help='YYYY-MM-DD, ISO datetime, or "none" to clear')
    s.set_defaults(f=cmd_update)

    s = sub.add_parser("comment")
    s.add_argument("ref")
    s.add_argument("text")
    s.set_defaults(f=cmd_comment)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
