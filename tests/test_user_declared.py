import os, sys, tempfile
d = tempfile.mkdtemp(); os.environ["OPENKB_LIBRARY_DB"] = d + "/l.db"
sys.path.insert(0, "/Volumes/MACMINI-HD/ETMW/etmw_openkb/app")
import library as L, random
def ok(c, m): print(("PASS " if c else "FAIL ") + m); assert c, m
random.seed(9); W = ["river","fox","stone","lantern","harvest","orbit","copper","meadow","signal","winter"]
def body(): return " ".join(random.choice(W) + "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(4)) for _ in range(400))
fake = lambda v: [1.0, 0.5, 0.2]
def sub(**k):
    a = dict(text=body(), title="T", origin="user-crawler", licence="", source_url="https://example.org/p", contributor="acct1", declarations={"own_or_licensed": True, "ok_with_cc_by_sa": True, "may_be_edited": True}, embed=fake, text_url="https://example.org/p.txt", recipe="plain"); a.update(k); return L.submit(**a)
r = sub(detected_licence="CC BY 4.0", default_licence="CC0"); ok(r["ok"], "page licence wins over default")
ok(L.licences_for([r["doc_id"]])[0] == "CC BY", "shown as the page licence")
r2 = sub(default_licence="CC BY-SA"); ok(r2["ok"], "no page licence: crawler default applies")
ok(L.licences_for([r2["doc_id"]])[0] == "CC BY-SA (user-declared)", "tagged user-declared")
c = L.connect(); ok("user-declared" in c.execute("SELECT detail FROM audit_log WHERE doc_id=? AND event='published'", (r2["doc_id"],)).fetchone()[0], "audit log records the declared default with the account")
ok(not sub(detected_licence="CC BY-NC 4.0", default_licence="CC0")["ok"], "page says NC: refused even with a default")
ok(not sub()["ok"], "no page licence and no default: refused")
ok(not sub(default_licence="All rights reserved")["ok"], "default must be an accepted open licence")
print("user-declared tests done")
