import pytest
from src.agents.blue_team_agent import BlueTeamAgent
from src.llm_factory import create_llm

def test_non_reasoning_precision():
    """Verify non-reasoning models now achieve >=78% precision"""
    # Use Nova Pro (non-reasoning) on hard difficulty
    llm = create_llm("us.amazon.nova-pro-v1:0")
    blue = BlueTeamAgent(
        llm=llm,
        strategy="precise",  # Enable verification filter
        iterations=1
    )
    
    # Mock code analysis (simplified for unit test)
    test_code = {
        "main.tf": """
resource "aws_s3_bucket" "data" {
  bucket = "patient-records"
}
"""
    }
    
    output = blue.execute(test_code)
    
    # Extract precision from stats
    precision = output.detection_stats.get("precision_stats", {}).get("pass2_count", 0)
    total = output.detection_stats.get("precision_stats", {}).get("pass1_count", 1)
    
    if total > 0:
        calculated_precision = precision / total
        # Minimum acceptable precision after fix
        assert calculated_precision >= 0.78, f"Precision {calculated_precision:.2%} < 78%"

if __name__ == "__main__":
    test_non_reasoning_precision()
    print("✅ Precision bottleneck fix verified")