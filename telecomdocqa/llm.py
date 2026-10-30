"""A small wrapper around the LLM API.

Groq, Gemini, Ollama and OpenAI all support the same "OpenAI-compatible"
chat API, so we use the `openai` library and just point it at a different
base URL. Switching provider = changing settings, not code.
"""

from openai import OpenAI

from telecomdocqa import config


class LLMClient:
    def __init__(self, model=config.LLM_MODEL, base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY,
                 reasoning_effort=config.LLM_REASONING_EFFORT):
        if not api_key:
            raise ValueError(
                "No API key found. Create a .env file in the project root with:\n"
                "LLM_API_KEY=your-groq-key\n"
                "(see .env.example)"
            )
        self.model = model
        self.reasoning_effort = reasoning_effort
        # max_retries: if we hit the free tier's rate limit, the library
        # waits a bit and tries again instead of crashing.
        self.client = OpenAI(api_key=api_key, base_url=base_url, max_retries=config.LLM_MAX_RETRIES)

    def _request(self, messages, temperature, max_tokens):
        """The settings sent with every request."""
        request = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.reasoning_effort:
            request["reasoning_effort"] = self.reasoning_effort
        return request

    def chat(self, messages, temperature=config.LLM_TEMPERATURE, max_tokens=config.LLM_MAX_TOKENS):
        """Send a list of messages and return the reply text."""
        response = self.client.chat.completions.create(**self._request(messages, temperature, max_tokens))
        text = response.choices[0].message.content or ""
        if not text.strip():
            # Happens if a reasoning model used all its tokens on thinking.
            raise RuntimeError("The model returned an empty answer. Try raising LLM_MAX_TOKENS in config.py.")
        return text.strip()

    def chat_stream(self, messages, temperature=config.LLM_TEMPERATURE, max_tokens=config.LLM_MAX_TOKENS):
        """Like chat(), but yields the reply piece by piece as it's generated.
        We'll use this for the streaming API in step 6."""
        stream = self.client.chat.completions.create(**self._request(messages, temperature, max_tokens), stream=True)
        for event in stream:
            if event.choices and event.choices[0].delta.content:
                yield event.choices[0].delta.content

    def list_models(self):
        """Names of the models your API key can use."""
        return sorted(model.id for model in self.client.models.list())


def main():
    """Check the API key works and show which models it can use:
        python -m telecomdocqa.llm
    """
    client = LLMClient()
    print(f"Provider: {config.LLM_BASE_URL}")
    print(f"Current model setting: {client.model}\n")
    print("Models available to your key:")
    for name in client.list_models():
        print("  ", name)


if __name__ == "__main__":
    main()
