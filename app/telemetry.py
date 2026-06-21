from phoenix.otel import register

# When PHOENIX_API_KEY + PHOENIX_COLLECTOR_ENDPOINT are set, register() routes
# to Arize cloud automatically. Falls back to localhost if neither is set.
tracer_provider = register(
    project_name="sourcerer",
    auto_instrument=True,
)
