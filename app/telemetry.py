from phoenix.otel import register

tracer_provider = register(
    project_name="sourcerer",
    auto_instrument=True,
)
