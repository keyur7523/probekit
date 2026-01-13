from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput
from app.clients.claude import ClaudeClient


class HallucinationEvaluator(BaseEvaluator):
    """
    Evaluates if model output contains hallucinations (claims not grounded in context).

    Uses an LLM to:
    1. Extract factual claims from the response
    2. Check each claim against the provided context
    3. Flag ungrounded claims as hallucinations
    """

    name = "hallucination"
    description = "Detects claims not grounded in provided context"

    EXTRACTION_PROMPT = """Analyze the following response and extract all factual claims made.
A factual claim is any statement that asserts something as true or false about the world.

Response to analyze:
{response}

List each factual claim on a new line, numbered. Only include explicit claims, not opinions or hedged statements.
If there are no factual claims, respond with "NO CLAIMS".

Claims:"""

    VERIFICATION_PROMPT = """You are a fact-checker. Determine if each claim is supported by the provided context.

Context (source of truth):
{context}

Claims to verify:
{claims}

For each claim, respond with:
- SUPPORTED: if the claim is directly supported by the context
- NOT SUPPORTED: if the claim contradicts or is not mentioned in the context
- PARTIALLY SUPPORTED: if only part of the claim is supported

Format your response as:
1. [SUPPORTED/NOT SUPPORTED/PARTIALLY SUPPORTED] - Brief explanation
2. [SUPPORTED/NOT SUPPORTED/PARTIALLY SUPPORTED] - Brief explanation
...

Verification:"""

    def __init__(self, model_id: str = "claude-sonnet-4-20250514"):
        self.client = ClaudeClient(model_id=model_id)

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        # If no context provided, we can't check for hallucinations
        if not context.context:
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=True,
                score=1.0,
                details={"skipped": True, "reason": "No context provided for verification"},
                reasoning="Hallucination check skipped - no source context provided",
            )

        # Step 1: Extract claims from the response
        extraction_response = await self.client.generate(
            prompt=self.EXTRACTION_PROMPT.format(response=context.output),
            temperature=0.0,
            max_tokens=1000,
        )

        claims_text = extraction_response.content.strip()

        if "NO CLAIMS" in claims_text.upper():
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=True,
                score=1.0,
                details={"claims_found": 0, "hallucinations": []},
                reasoning="No factual claims found in response",
            )

        # Step 2: Verify claims against context
        verification_response = await self.client.generate(
            prompt=self.VERIFICATION_PROMPT.format(
                context=context.context,
                claims=claims_text,
            ),
            temperature=0.0,
            max_tokens=2000,
        )

        # Step 3: Parse verification results
        verification_text = verification_response.content
        lines = verification_text.strip().split("\n")

        supported = 0
        not_supported = 0
        partially_supported = 0
        hallucinations = []

        for line in lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue

            if "NOT SUPPORTED" in line.upper():
                not_supported += 1
                hallucinations.append(line)
            elif "PARTIALLY SUPPORTED" in line.upper():
                partially_supported += 1
            elif "SUPPORTED" in line.upper():
                supported += 1

        total_claims = supported + not_supported + partially_supported

        if total_claims == 0:
            score = 1.0
        else:
            # Score: 1.0 if all supported, 0.0 if all hallucinated
            score = (supported + 0.5 * partially_supported) / total_claims

        passed = not_supported == 0

        return EvaluatorOutput(
            evaluator_name=self.name,
            passed=passed,
            score=round(score, 3),
            details={
                "claims_found": total_claims,
                "supported": supported,
                "partially_supported": partially_supported,
                "not_supported": not_supported,
                "hallucinations": hallucinations,
                "claims_text": claims_text,
            },
            reasoning=f"{not_supported} hallucinated claims found" if not_supported > 0 else "All claims grounded in context",
        )
