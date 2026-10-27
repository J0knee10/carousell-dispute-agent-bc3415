import os

# Tests never call a real API.
os.environ["LLM_PROVIDER"] = "mock"

import pytest  # noqa: E402

from dispute_agent.data.cases import load_seed_cases  # noqa: E402
from dispute_agent.llm import get_llm  # noqa: E402
from dispute_agent.rag.store import get_store  # noqa: E402


@pytest.fixture(scope="session")
def seeds():
    return {c.case_id: c for c in load_seed_cases()}


@pytest.fixture(scope="session")
def store():
    return get_store()


@pytest.fixture
def mock_llm():
    return get_llm(provider="mock")
