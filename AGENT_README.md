# Sourcerer — Verified AI Tutor

An AI tutor that verifies its own answers using multi-agent debate and web evidence grounding.

## What it does

Send any factual question and Sourcerer will:

1. Draft an answer using Claude (Sonnet)
2. Decompose it into atomic claims and red-team each with specialist critics
3. Fetch web evidence for disputed claims via Browserbase
4. Synthesize a final answer that drops or hedges unsupported claims
5. Score confidence based on multi-sample semantic disagreement

## How to use

Send a plain-text question as a ChatMessage. You'll receive an acknowledgement immediately, then a verified answer within 15–60 seconds depending on question complexity.

## Powered by

Claude (Anthropic) for reasoning, Stagehand/Browserbase for web grounding, Arize Phoenix for observability.
