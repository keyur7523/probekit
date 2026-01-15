"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns service info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Behavioral Eval API"
        assert data["status"] == "healthy"

    async def test_health_endpoint(self, client: AsyncClient):
        """Test health endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestTestCasesAPI:
    """Tests for test cases endpoints."""

    async def test_create_test_case(self, client: AsyncClient, sample_test_case_data):
        """Test creating a test case."""
        response = await client.post("/api/test-cases/", json=sample_test_case_data)
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == sample_test_case_data["prompt"]
        assert data["input"] == sample_test_case_data["input"]
        assert data["category"] == sample_test_case_data["category"]
        assert "id" in data

    async def test_create_test_case_minimal(self, client: AsyncClient):
        """Test creating a test case with minimal fields."""
        minimal_data = {
            "prompt": "Test prompt",
            "input": "Test input",
        }
        response = await client.post("/api/test-cases/", json=minimal_data)
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == minimal_data["prompt"]
        assert data["category"] is None

    async def test_create_test_case_with_expected_structure(self, client: AsyncClient):
        """Test creating a test case with expected JSON structure."""
        test_data = {
            "prompt": "Extract entities from text",
            "input": "John works at Acme Corp.",
            "expected_structure": {
                "type": "object",
                "required": ["entities"],
                "properties": {
                    "entities": {"type": "array"}
                }
            }
        }
        response = await client.post("/api/test-cases/", json=test_data)
        assert response.status_code == 200
        data = response.json()
        assert data["expected_structure"] == test_data["expected_structure"]

    async def test_list_test_cases_empty(self, client: AsyncClient):
        """Test listing test cases when empty."""
        response = await client.get("/api/test-cases/")
        assert response.status_code == 200
        data = response.json()
        assert data["test_cases"] == []
        assert data["total"] == 0

    async def test_list_test_cases(self, client: AsyncClient, sample_test_case_data):
        """Test listing test cases."""
        # Create a few test cases
        await client.post("/api/test-cases/", json=sample_test_case_data)
        await client.post("/api/test-cases/", json={
            "prompt": "Another prompt",
            "input": "Another input",
            "category": "qa"
        })

        response = await client.get("/api/test-cases/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["test_cases"]) == 2
        assert data["total"] == 2

    async def test_list_test_cases_filter_by_category(self, client: AsyncClient):
        """Test filtering test cases by category."""
        # Create test cases with different categories
        await client.post("/api/test-cases/", json={
            "prompt": "P1", "input": "I1", "category": "summarization"
        })
        await client.post("/api/test-cases/", json={
            "prompt": "P2", "input": "I2", "category": "qa"
        })
        await client.post("/api/test-cases/", json={
            "prompt": "P3", "input": "I3", "category": "summarization"
        })

        response = await client.get("/api/test-cases/", params={"category": "summarization"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["test_cases"]) == 2
        assert all(tc["category"] == "summarization" for tc in data["test_cases"])

    async def test_get_test_case(self, client: AsyncClient, sample_test_case_data):
        """Test getting a specific test case."""
        # Create a test case
        create_response = await client.post("/api/test-cases/", json=sample_test_case_data)
        test_case_id = create_response.json()["id"]

        # Get the test case
        response = await client.get(f"/api/test-cases/{test_case_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_case_id
        assert data["prompt"] == sample_test_case_data["prompt"]

    async def test_get_test_case_not_found(self, client: AsyncClient):
        """Test getting a non-existent test case."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/test-cases/{fake_id}")
        assert response.status_code == 404

    async def test_update_test_case(self, client: AsyncClient, sample_test_case_data):
        """Test updating a test case."""
        # Create a test case
        create_response = await client.post("/api/test-cases/", json=sample_test_case_data)
        test_case_id = create_response.json()["id"]

        # Update it
        update_data = {"prompt": "Updated prompt", "category": "updated_category"}
        response = await client.put(f"/api/test-cases/{test_case_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == "Updated prompt"
        assert data["category"] == "updated_category"
        assert data["input"] == sample_test_case_data["input"]  # Unchanged

    async def test_delete_test_case(self, client: AsyncClient, sample_test_case_data):
        """Test deleting a test case."""
        # Create a test case
        create_response = await client.post("/api/test-cases/", json=sample_test_case_data)
        test_case_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(f"/api/test-cases/{test_case_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        get_response = await client.get(f"/api/test-cases/{test_case_id}")
        assert get_response.status_code == 404

    async def test_pagination(self, client: AsyncClient):
        """Test pagination of test cases."""
        # Create 5 test cases
        for i in range(5):
            await client.post("/api/test-cases/", json={
                "prompt": f"Prompt {i}",
                "input": f"Input {i}",
            })

        # Get first page
        response = await client.get("/api/test-cases/", params={"skip": 0, "limit": 2})
        data = response.json()
        assert len(data["test_cases"]) == 2
        assert data["total"] == 5

        # Get second page
        response = await client.get("/api/test-cases/", params={"skip": 2, "limit": 2})
        data = response.json()
        assert len(data["test_cases"]) == 2


class TestEvaluationsAPI:
    """Tests for evaluations endpoints."""

    async def test_list_evaluators(self, client: AsyncClient):
        """Test listing available evaluators."""
        response = await client.get("/api/evaluations/evaluators")
        assert response.status_code == 200
        data = response.json()
        assert "evaluators" in data
        evaluator_names = [e["name"] for e in data["evaluators"]]
        assert "instruction_adherence" in evaluator_names
        assert "hallucination" in evaluator_names
        assert "format_consistency" in evaluator_names
        assert "refusal_behavior" in evaluator_names
        assert "output_stability" in evaluator_names

    async def test_list_evaluation_runs_empty(self, client: AsyncClient):
        """Test listing evaluation runs when empty."""
        response = await client.get("/api/evaluations/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0

    async def test_start_evaluation_no_test_cases(self, client: AsyncClient):
        """Test starting evaluation with non-existent test cases fails."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post("/api/evaluations/run", json={
            "prompt_version": "v1.0",
            "test_case_ids": [fake_id],
            "models": [{"model_id": "gpt-4o", "temperature": 0.0, "max_tokens": 100}]
        })
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    async def test_start_evaluation_invalid_evaluator(self, client: AsyncClient, sample_test_case_data):
        """Test starting evaluation with invalid evaluator fails."""
        # Create a test case first
        tc_response = await client.post("/api/test-cases/", json=sample_test_case_data)
        test_case_id = tc_response.json()["id"]

        response = await client.post("/api/evaluations/run", json={
            "prompt_version": "v1.0",
            "test_case_ids": [test_case_id],
            "models": [{"model_id": "gpt-4o", "temperature": 0.0, "max_tokens": 100}],
            "evaluators": ["nonexistent_evaluator"]
        })
        assert response.status_code == 400
        assert "Unknown evaluators" in response.json()["detail"]

    async def test_get_evaluation_run_not_found(self, client: AsyncClient):
        """Test getting a non-existent evaluation run."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/evaluations/runs/{fake_id}")
        assert response.status_code == 404

    async def test_delete_evaluation_run_not_found(self, client: AsyncClient):
        """Test deleting a non-existent evaluation run."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(f"/api/evaluations/runs/{fake_id}")
        assert response.status_code == 404

    async def test_get_aggregated_results_empty(self, client: AsyncClient):
        """Test getting aggregated results when no runs exist."""
        response = await client.get("/api/evaluations/results")
        assert response.status_code == 200
        data = response.json()
        assert data["statistics"] == {}


class TestAnnotationsAPI:
    """Tests for annotations endpoints."""

    async def test_list_annotations_empty(self, client: AsyncClient):
        """Test listing annotations when empty."""
        response = await client.get("/api/annotations/")
        assert response.status_code == 200
        data = response.json()
        assert data["annotations"] == []


class TestConversationsAPI:
    """Tests for conversation endpoints."""

    async def test_list_conversation_runs_empty(self, client: AsyncClient):
        response = await client.get("/api/conversations/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0

    async def test_list_conversation_metrics_empty(self, client: AsyncClient):
        response = await client.get("/api/conversations/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []

    async def test_start_conversation_no_turns(self, client: AsyncClient):
        response = await client.post("/api/conversations/run", json={
            "condition": "baseline",
            "model": {"model_id": "claude-sonnet-4-20250514", "temperature": 0.0, "max_tokens": 100},
            "turns": [],
        })
        assert response.status_code == 400
        assert "turns" in response.json()["detail"].lower()

    async def test_conversation_requires_exactly_12_turns(self, client: AsyncClient):
        payload = {
            "condition": "baseline",
            "model": {"model_id": "claude-sonnet-4-20250514", "temperature": 0.2, "max_tokens": 256},
            "turns": [f"Turn {i}" for i in range(11)],
        }
        response = await client.post("/api/conversations/run", json=payload)
        assert response.status_code == 400
        assert "exactly 12 turns" in response.json()["detail"]

    async def test_conversation_rejects_disallowed_model(self, client: AsyncClient):
        payload = {
            "condition": "baseline",
            "model": {"model_id": "gpt-4o", "temperature": 0.2, "max_tokens": 256},
            "turns": [f"Turn {i}" for i in range(12)],
        }
        response = await client.post("/api/conversations/run", json=payload)
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    async def test_create_annotation_invalid_output(self, client: AsyncClient):
        """Test creating annotation for non-existent output fails."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post("/api/annotations/", json={
            "output_id": fake_id,
            "annotation_type": "correctness",
            "label": "correct"
        })
        assert response.status_code == 404


class TestDashboardAPI:
    """Tests for dashboard endpoints."""

    async def test_get_metrics(self, client: AsyncClient):
        """Test getting dashboard metrics."""
        response = await client.get("/api/dashboard/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_test_cases" in data
        assert "total_runs" in data
        assert "completed_runs" in data
        assert "total_cost_usd" in data
        assert "avg_latency_ms" in data
        assert "overall_pass_rate" in data

    async def test_get_trends(self, client: AsyncClient):
        """Test getting score trends."""
        response = await client.get("/api/dashboard/trends", params={"days": 30})
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert data["days"] == 30
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_get_model_comparison(self, client: AsyncClient):
        """Test getting model comparison data."""
        response = await client.get("/api/dashboard/model-comparison")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_get_evaluator_breakdown(self, client: AsyncClient):
        """Test getting evaluator breakdown data."""
        response = await client.get("/api/dashboard/evaluator-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_get_recent_activity(self, client: AsyncClient):
        """Test getting recent activity."""
        response = await client.get("/api/dashboard/recent-activity", params={"limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "activity" in data
        assert isinstance(data["activity"], list)
