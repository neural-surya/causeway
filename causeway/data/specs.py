"""World definitions (config only, no logic). generate.py turns a Spec into a graph."""
from dataclasses import dataclass, field


@dataclass
class Family:
    key: str            # retry | schema | config | flaky
    tier: str           # easy | medium | hard
    pattern: str        # human description of the recurring failure pattern
    # one (failing_service, culprit_service) pair per occurrence, in order
    occurrences: list[tuple[str, str]]


@dataclass
class Spec:
    tenant: str
    company: str
    services: dict[str, str]                 # name -> tier (tier1/tier2)
    deps: list[tuple[str, str]]              # (a, b): a DEPENDS_ON b
    teams: dict[str, list[str]]              # team -> services it owns
    people: list[str]                        # name pool, split evenly across teams
    noise_commits_per_service: int
    families: list[Family]
    decisions: list[dict] = field(default_factory=list)


ALPHA = Spec(
    tenant="alpha",
    company="Northwind Payments",
    services={
        "api-gateway": "tier1", "auth": "tier1", "orders": "tier1", "payments": "tier1",
        "billing": "tier2", "ledger": "tier1", "fraud": "tier2", "notifications": "tier2",
        "inventory": "tier2", "user-profile": "tier1",
    },
    deps=[
        ("api-gateway", "auth"), ("api-gateway", "orders"), ("api-gateway", "payments"),
        ("api-gateway", "user-profile"),
        ("orders", "payments"), ("orders", "inventory"), ("orders", "notifications"),
        ("payments", "ledger"), ("payments", "fraud"), ("payments", "auth"),
        ("billing", "ledger"), ("billing", "payments"),
        ("fraud", "user-profile"), ("notifications", "user-profile"), ("auth", "user-profile"),
    ],
    teams={
        "platform": ["api-gateway", "auth"],
        "commerce": ["orders", "inventory", "notifications"],
        "money": ["payments", "billing", "ledger"],
        "identity-risk": ["fraud", "user-profile"],
    },
    people=["Asha Rao", "Ben Okafor", "Chloe Martin", "Dev Patel", "Elena Petrova", "Farid Haddad",
            "Grace Liu", "Hugo Silva", "Ines Moreau", "Jon Berg", "Kavya Nair", "Liam Walsh",
            "Mei Tanaka", "Noah Cohen", "Olga Ivanova", "Pavel Novak"],
    noise_commits_per_service=28,
    families=[
        Family("retry", "easy", "retry policy change causes timeouts and duplicate requests",
               [("payments", "payments"), ("orders", "orders"), ("billing", "billing")]),
        Family("schema", "medium", "schema migration upstream breaks a downstream consumer",
               [("api-gateway", "fraud"), ("orders", "ledger"), ("payments", "user-profile")]),
        Family("config", "hard", "config default change upstream shows up as latency in an unrelated service",
               [("orders", "auth"), ("billing", "fraud"), ("api-gateway", "inventory")]),
        Family("flaky", "medium", "a flaky test draws attention while the real regression is one hop upstream",
               [("api-gateway", "notifications"), ("orders", "user-profile"), ("billing", "auth")]),
    ],
    decisions=[
        dict(key="retry1", title="Retry failed gateway calls 3 times immediately", days_ago=330,
             concerns=["payments", "api-gateway"], supersedes=None, status="superseded",
             body="We retry failed calls to payments three times with no delay. Simple, but under load it multiplies traffic."),
        dict(key="retry2", title="Use exponential backoff with jitter, capped at 2s", days_ago=240,
             concerns=["payments", "api-gateway"], supersedes="retry1", status="superseded",
             body="Immediate retries caused a retry storm. Switch to exponential backoff with jitter, cap 2s."),
        dict(key="retry3", title="Retry budget of 10 percent extra load, never retry 4xx", days_ago=120,
             concerns=["payments", "api-gateway", "orders"], supersedes="retry2", status="active",
             body="Backoff alone still amplified outages. Enforce a retry budget (10 percent extra load) and never retry 4xx."),
        dict(key="migr", title="Schema migrations follow expand then contract", days_ago=200,
             concerns=["ledger", "payments"], supersedes=None, status="active",
             body="Add new columns first, migrate readers, then drop old columns in a later release."),
        dict(key="cfg1", title="Config changes ship only through the versioned config service", days_ago=300,
             concerns=["user-profile", "auth", "fraud"], supersedes=None, status="superseded",
             body="All runtime config goes through the versioned config service, no local overrides."),
        dict(key="cfg2", title="Allow reviewed default overrides inside service repos", days_ago=150,
             concerns=["user-profile", "auth", "fraud"], supersedes="cfg1", status="active",
             body="Teams may change defaults in their own repo with one reviewer, to speed up hotfixes."),
        dict(key="flk", title="Quarantine tests with flaky score above 0.3", days_ago=180,
             concerns=["orders", "notifications", "auth"], supersedes=None, status="active",
             body="Tests flaking more than 30 percent of runs are quarantined and must not block releases."),
    ],
)

BETA = Spec(
    tenant="beta",
    company="Globex Logistics",
    services={"routing": "tier1", "tracking": "tier2", "carrier-api": "tier1", "warehouse-sync": "tier2"},
    deps=[("tracking", "carrier-api"), ("routing", "carrier-api"), ("routing", "warehouse-sync")],
    teams={"logistics": ["routing", "tracking"], "integrations": ["carrier-api", "warehouse-sync"]},
    people=["Zara Quinn", "Yusuf Demir", "Xavier Reyes", "Wanda Lee", "Viktor Hahn", "Uma Shah"],
    noise_commits_per_service=8,
    families=[Family("retry", "easy", "retry policy change causes timeouts and duplicate requests",
                     [("routing", "routing"), ("tracking", "tracking")])],
    decisions=[
        dict(key="b1", title="Poll carriers every 30 seconds", days_ago=200, concerns=["carrier-api"],
             supersedes=None, status="superseded", body="Carrier status is polled every 30 seconds."),
        dict(key="b2", title="Subscribe to carrier webhooks instead of polling", days_ago=90,
             concerns=["carrier-api", "tracking"], supersedes="b1", status="active",
             body="Webhooks cut load and latency; polling remains only as a fallback."),
    ],
)
