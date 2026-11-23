"""Publish the next solar tip to Instagram (Instagram API with Instagram Login).

Run by GitHub Actions. Environment variables:
  IG_TOKEN      long-lived Instagram user access token (secret)
  IG_USER_ID    Instagram professional account ID (optional; looked up if empty)
  IMAGE_BASE    public base URL where cards/ is served, e.g.
                https://raw.githubusercontent.com/<user>/circa100-web/main/solar-tips/
  MODE          "render" = only create the next card and write next.json
                "publish" = publish the card described in next.json
  DRY_RUN       "1" = print what would be posted, don't call Instagram
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse
import make_card

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://graph.instagram.com/v21.0"
STATE = os.path.join(HERE, "posted.json")
NEXT = os.path.join(HERE, "next.json")


def load(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except FileNotFoundError:
        return default


def save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def call(method, path, params):
    params = dict(params, access_token=os.environ["IG_TOKEN"])
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Instagram API error {e.code}: {e.read().decode()}")


def pick_next(tips, state):
    """Alternate everyday / technical, never repeat until the library is exhausted."""
    done = {p["id"] for p in state["posts"]}
    last = state["posts"][-1]["audience"] if state["posts"] else "technical"
    want = "everyday" if last == "technical" else "technical"
    pool = [t for t in tips if t["id"] not in done]
    if not pool:  # library exhausted: start a new round
        state["round"] = state.get("round", 1) + 1
        done = {p["id"] for p in state["posts"] if p.get("round", 1) == state["round"]}
        pool = [t for t in tips if t["id"] not in done]
    pref = [t for t in pool if t["audience"] == want]
    return (pref or pool)[0]


def caption(tip, data, number):
    tags = data["hashtags_technical"] if tip["audience"] == "technical" else data["hashtags_everyday"]
    who = "For the technical crowd" if tip["audience"] == "technical" else "For every home"
    return (f"☀️ Solar tip #{number:03d} · {who}\n\n"
            f"{tip['title']}\n\n{tip['body']}\n\n{tip['more']}\n\n"
            "Questions about your own system? DM @circa.100 or try the free solar assessment at circa100.com (link in bio).\n\n" + tags)


def render():
    data = load(os.path.join(HERE, "tips.json"), None)
    state = load(STATE, {"posts": [], "round": 1})
    tip = pick_next(data["tips"], state)
    number = len(state["posts"]) + 1
    fname = f"cards/{datetime.date.today():%Y%m%d}-{tip['id']}.jpg"
    os.makedirs(os.path.join(HERE, "cards"), exist_ok=True)
    make_card.render(tip, os.path.join(HERE, fname), number)
    save(NEXT, {"id": tip["id"], "audience": tip["audience"], "number": number,
                "file": fname, "caption": caption(tip, data, number), "round": state.get("round", 1)})
    print("Rendered", fname)


def publish():
    nxt = load(NEXT, None)
    if not nxt:
        sys.exit("next.json missing: run MODE=render first")
    image_url = os.environ["IMAGE_BASE"].rstrip("/") + "/" + nxt["file"]
    if os.environ.get("DRY_RUN") == "1":
        print("DRY RUN\n", image_url, "\n", nxt["caption"])
        return
    ig = os.environ.get("IG_USER_ID") or call("GET", "me", {"fields": "user_id"})["user_id"]
    # Wait until the freshly pushed image is publicly reachable
    for _ in range(12):
        try:
            urllib.request.urlopen(urllib.request.Request(image_url, method="HEAD"), timeout=20)
            break
        except Exception:
            time.sleep(10)
    c = call("POST", f"{ig}/media", {"image_url": image_url, "caption": nxt["caption"],
                                     "alt_text": nxt["caption"].split("\n\n")[1][:1000]})
    for _ in range(20):
        st = call("GET", c["id"], {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"Container failed: {st}")
        time.sleep(6)
    media = call("POST", f"{ig}/media_publish", {"creation_id": c["id"]})
    link = call("GET", media["id"], {"fields": "permalink"}).get("permalink", "")
    state = load(STATE, {"posts": [], "round": 1})
    state["round"] = nxt.get("round", 1)
    state["posts"].append({"id": nxt["id"], "audience": nxt["audience"], "number": nxt["number"],
                           "date": f"{datetime.date.today():%Y-%m-%d}", "image": nxt["file"],
                           "permalink": link, "round": state["round"]})
    save(STATE, state)
    os.remove(NEXT)
    print("Published", nxt["id"], link)


def refresh_token():
    """Long-lived tokens last 60 days; refreshing returns a new 60-day token."""
    r = call("GET", "refresh_access_token", {"grant_type": "ig_refresh_token"})
    # print only to a file the workflow reads; never echo tokens into logs
    open(os.environ.get("TOKEN_OUT", "/tmp/new_token"), "w").write(r["access_token"])
    print("Token refreshed, expires in", r.get("expires_in"), "seconds")


if __name__ == "__main__":
    mode = os.environ.get("MODE", "render")
    {"render": render, "publish": publish, "refresh": refresh_token}[mode]()
