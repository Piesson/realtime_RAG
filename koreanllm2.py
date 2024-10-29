from huggingface_hub import InferenceClient

client = InferenceClient(api_key="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")

for message in client.chat_completion(
	model="MLP-KTLim/llama-3-Korean-Bllossom-8B",
	messages=[{"role": "user", "content": "안녕"}],
	max_tokens=500,
	stream=True,
):
    print(message.choices[0].delta.content, end="")