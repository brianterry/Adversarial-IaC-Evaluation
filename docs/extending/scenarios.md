# Custom Scenarios

## Adding Domain Templates

Edit `src/prompts.py` to add new scenario templates:

```python
SCENARIO_TEMPLATES = {
    "my_domain": [
        "Create a {resource} for {purpose}",
    ]
}
```
