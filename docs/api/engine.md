# Game Engine API

The `GameEngine` class orchestrates the entire game flow.

## GameEngine

```python
from src.game.engine import GameEngine

engine = GameEngine()
result = await engine.run_game(scenario, config)
```

### Methods

#### `run_game(scenario, config) -> GameResult`

Runs a complete adversarial game.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `scenario` | `Scenario` | The scenario to run |
| `config` | `GameConfig` | Game configuration |

**Returns:** `GameResult` with all outputs and metrics.

---

## GameConfig

Configuration for a game.

```python
from src.game.engine import GameConfig

config = GameConfig(
    red_model="claude-3-5-sonnet",
    blue_model="claude-3-5-sonnet",
    difficulty="medium",
    language="terraform",
    cloud_provider="aws",
    red_team_mode="single",
    blue_team_mode="single",
    verification_mode="standard",
    region="us-west-2",
)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `red_model` | str | required | Red Team model ID |
| `blue_model` | str | required | Blue Team model ID |
| `difficulty` | str | `"medium"` | `easy`, `medium`, `hard` |
| `language` | str | `"terraform"` | IaC language |
| `cloud_provider` | str | `"aws"` | Cloud provider |
| `red_team_mode` | str | `"single"` | `single`, `pipeline` |
| `blue_team_mode` | str | `"single"` | `single`, `ensemble` |
| `consensus_method` | str | `"debate"` | Ensemble consensus method |
| `verification_mode` | str | `"standard"` | `standard`, `debate` |
| `region` | str | `"us-west-2"` | AWS region |

---

## GameResult

Result from a completed game.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | str | Unique game identifier |
| `scenario` | Scenario | The scenario that was run |
| `config` | GameConfig | Configuration used |
| `red_output` | RedTeamOutput | Red Team code and manifest |
| `blue_output` | BlueTeamOutput | Blue Team findings |
| `scoring` | ScoringResult | Match results and metrics |
| `red_time_seconds` | float | Red Team execution time |
| `blue_time_seconds` | float | Blue Team execution time |
| `total_time_seconds` | float | Total game time |

### Accessing Metrics

```python
result = await engine.run_game(scenario, config)

print(f"Precision: {result.scoring.precision:.0%}")
print(f"Recall: {result.scoring.recall:.0%}")
print(f"F1 Score: {result.scoring.f1_score:.0%}")
print(f"Evasion Rate: {result.scoring.evasion_rate:.0%}")
```
