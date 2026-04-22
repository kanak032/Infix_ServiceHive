def mock_lead_capture(name: str, email: str, platform: str) -> str:
    """Mock API to capture a qualified lead. Call ONLY when all 3 fields are collected."""
    print(f"Lead captured successfully: {name}, {email}, {platform}")
    return f"Lead captured successfully: {name}, {email}, {platform}"
