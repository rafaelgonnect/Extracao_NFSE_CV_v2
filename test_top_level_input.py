import os
import asyncio
import base64
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_top_level_input_file():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    print("Calling OpenAI with top-level input_file...")
    try:
        # We use extra_body to send non-standard parameters
        response = await client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is in this document?"}
            ],
            extra_body={
                "input_file": {
                    "data": pdf_base64,
                    "format": "pdf"
                }
            }
        )
        print("Response:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_top_level_input_file())
