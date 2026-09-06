from dotenv import load_dotenv
load_dotenv()

import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
model="claude-sonnet-4-6",
max_tokens=1000,
messages=[
{"role": "user", "content": "Say hello in one sentence."}
],
)
for block in message.content:
    if block.type == "text":
        print(block.text)