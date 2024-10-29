from huggingface_hub import InferenceClient

client = InferenceClient(api_key="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")

for message in client.chat_completion(
	model="Bllossom/llama-3.2-Korean-Bllossom-3B",
	messages=[{"role": "user", "content": "너 한국말 잘해?"}],
	max_tokens=500,
	stream=True,
):
    print(message.choices[0].delta.content, end="")