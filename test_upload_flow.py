import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_upload_and_call():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    print(f"Uploading {file_path}...")
    with open(file_path, "rb") as f:
        file_obj = await client.files.create(file=f, purpose="vision")
    
    print(f"File uploaded. ID: {file_obj.id}")
    
    try:
        print("Calling Chat Completions...")
        response = await client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this document about? Reply in JSON."},
                        {
                            "type": "file",
                            "file": {
                                "file_id": file_obj.id
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        print("Response:")
        print(response.choices[0].message.content)
    finally:
        print(f"Deleting file {file_obj.id}...")
        await client.files.delete(file_obj.id)

if __name__ == "__main__":
    asyncio.run(test_upload_and_call())
