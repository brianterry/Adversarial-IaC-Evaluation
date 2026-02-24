# Adding Models

## AWS Bedrock Models

Add new model IDs to the supported list in `src/llm.py`.

## Custom Providers

Implement a new LLM client following the `BaseChatModel` interface.

```python
class MyCustomLLM(BaseChatModel):
    def invoke(self, messages):
        # Your implementation
        pass
```
