"""Local-only API fixture for browser tests. Never use this module in deployment."""
import os
import time
from backend.store import Store
from backend.main import create_app
from tests.fixtures.research import fake_model, fake_search
import agent.nodes.company as company
import agent.nodes.domain as domain
import agent.services.evidence as evidence
import agent.services.search as search
import backend.supabase_client as storage

if os.getenv("APP_ENV") == "production":
    raise RuntimeError("The fixture server cannot run in production")

def delayed_model(prompt, schema=None):
    time.sleep(0.35)
    return fake_model(prompt, schema)

company.invoke_gemini = domain.invoke_gemini = evidence.invoke_gemini = delayed_model
search.search_web = search.search_exa = fake_search
storage.is_supabase_configured = lambda: False
os.environ["IP_DAILY_RUN_LIMIT"] = "1000"
os.environ["GLOBAL_DAILY_RUN_LIMIT"] = "1000"
os.environ["RESEARCH_CACHE_ENABLED"] = "false"
os.environ["SEARCH_CACHE_ENABLED"] = "false"
app = create_app(Store("outputs/browser-tests.sqlite3"))
