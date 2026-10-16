from app.evaluators.base import BaseEvaluator, EvaluationContext, EvaluatorOutput
from app.clients.claude import ClaudeClient


class HallucinationEvaluator(BaseEvaluator):
    """
    Evaluates if model output contains hallucinations (claims not grounded in context).

    Uses an LLM to:
    1. Extract claims from the response (given the question), including inferred conclusions,
       evaluations, motives and statements about what the document does or doesn't say
    2. Check each claim against the provided context, with the question for reference
    3. Flag unsupported or partly supported claims as hallucinations
    """

    name = "hallucination"
    description = "LLM-judged: two-step claim extraction and verification against the provided context"

    EXTRACTION_PROMPT = """You are listing the claims a response makes so that each one can be checked against a source document.

Question the response answers:
{question}

Response:
{response}

List every claim the response makes, one per line, numbered. A claim is anything a reader could take as information, including:
- facts such as names, numbers, dates and events;
- statements about what the source does or does not say (for example "The document does not state the build cost");
- inferred conclusions, evaluations and characterisations (for example "this shows strong investor confidence" or "it was a successful season");
- causes, motives and purposes (for example "the closure is needed to ensure safety");
- hedged statements that still assert specific content (for example "it was likely made by an indie studio").

Do not list generic advice about where to find information (for example "check the official website"), or speculation that is explicitly marked as such and adds no specific content.

Write each claim as a self-contained sentence. If the response makes no claims, respond with "NO CLAIMS".

Claims:"""

    VERIFICATION_PROMPT = """You are a fact-checker. Decide whether each claim is supported by the source document. The document is the only source of truth: ignore general knowledge, even when a claim is true in the real world.

Question that was asked:
{question}

Document:
{context}

Claims to verify:
{claims}

For each claim, decide:
- SUPPORTED: the document states it, or it follows directly and unavoidably from what the document states. A claim that the document does not contain some information is SUPPORTED when the document indeed does not contain it.
- NOT SUPPORTED: the document doesn't state it or contradicts it, including inferences, evaluations, causes and motives that the document doesn't itself give. A claim that the document lacks information it actually contains is NOT SUPPORTED.
- PARTIALLY SUPPORTED: part of the claim is stated in the document and part is not.

Format your response as:
1. [SUPPORTED/NOT SUPPORTED/PARTIALLY SUPPORTED] - Brief explanation
2. [SUPPORTED/NOT SUPPORTED/PARTIALLY SUPPORTED] - Brief explanation
...

Verification:"""

    # Judge model; classification/extraction work, so low effort keeps thinking short
    JUDGE_MODEL = "claude-sonnet-5-5"
    JUDGE_EFFORT = "low"

    def __init__(self, model_id: str = JUDGE_MODEL):
        self.client = ClaudeClient(model_id=model_id)

    async def evaluate(self, context: EvaluationContext) -> EvaluatorOutput:
        # If no context provided, we can't check for hallucinations
        if not context.context:
            # Not applicable: record no verdict so it is excluded from pass rates
            return EvaluatorOutput(
                evaluator_name=self.name,
                passed=None,
                score=None,
                details={"skipped": True, "reason": "No context provided for verification"},
                reasoning="Not applicable - no source context to check claims against",
            )

        # Step 1: Extract claims from the response
        extraction_response = await self.client.generate(
            prompt=self.EXTRACTION_PROMPT.format(question=context.input_text, response=context.output),
            temperature=0.0,
            max_tokens=4000,
            effort=self.JUDGE_EFFORT,
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
                question=context.input_text,
                context=context.context,
                claims=claims_text,
            ),
            temperature=0.0,
            max_tokens=8000,
            effort=self.JUDGE_EFFORT,
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

        # Any unsupported content counts as a hallucination, including partly supported claims
        passed = not_supported == 0 and partially_supported == 0

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
            reasoning=(
                f"{not_supported} unsupported and {partially_supported} partly supported claims found"
                if not passed else "All claims grounded in context"
            ),
        )
