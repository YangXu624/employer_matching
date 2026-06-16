CONFIG = {
    "embedding_model": "BAAI/bge-base-en-v1.5",
    "weight_budget": 100,
    "llm_provider": "off",  # Phase 0: only "off" is supported
    "llm_trigger": {"min_peak_similarity": 0.40, "max_margin": 0.05},
    "calibration": {
        "effective_communicator": 0.0,
        "global_citizen": 0.0,
        "creative_innovator": 0.0,
        "critical_thinker": 0.0,
        "reflective_future_focused": 0.0,
        "career_ready": 0.0,
    },
}
